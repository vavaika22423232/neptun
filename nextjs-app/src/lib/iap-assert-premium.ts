/**
 * Shared Google Play + Apple premium purchase verification.
 * Used by /api/verify-purchase and /api/premium/entitlement.
 */

import { androidpublisher } from '@googleapis/androidpublisher';
import { GoogleAuth } from 'google-auth-library';
import { X509Certificate, createVerify } from 'crypto';

export const PACKAGE_NAME =
  process.env.GOOGLE_PLAY_PACKAGE_NAME || 'com.neptunalarm.neptun_alarm_app';

const APPLE_SHARED_SECRET = process.env.APPLE_SHARED_SECRET;
const APPLE_BUNDLE_ID = 'com.neptunalarm.neptunAlarmApp';
const APPLE_PRODUCTION_URL = 'https://buy.itunes.apple.com/verifyReceipt';
const APPLE_SANDBOX_URL = 'https://sandbox.itunes.apple.com/verifyReceipt';

const APPLE_ROOT_CA_G3_FINGERPRINT =
  '63:34:3A:BF:B8:9A:6A:03:EB:B5:7E:9B:3F:5F:A7:BE:7C:4F:5C:75:6F:30:17:B3:A8:C4:88:C3:65:3E:91:79';

export const KNOWN_PREMIUM_PRODUCT_IDS = [
  'neptun_pro_monthly_69',
  'neptun_pro_plus_monthly_129',
  'neptun_max_monthly_199',
  'pro_monthly',
  'premium_150_uah',
  'premium_100_uah',
  'premium',
  'com.neptunalarm.premium',
];

/** Monthly subscription SKUs — verified via subscriptions API, not products.get */
export const SUBSCRIPTION_PRODUCT_IDS = [
  'neptun_pro_monthly_69',
  'neptun_pro_plus_monthly_129',
  'neptun_max_monthly_199',
  'pro_monthly',
];

export function isSubscriptionProductId(productId: string): boolean {
  return SUBSCRIPTION_PRODUCT_IDS.includes(productId);
}

export type PremiumAssertResult =
  | { kind: 'valid'; expiresAt?: string | null }
  | { kind: 'invalid' }
  | { kind: 'pending' }
  | { kind: 'transient' }
  | { kind: 'misconfigured' };

function isGooglePurchaseNotFound(err: unknown): boolean {
  const e = err as { code?: number; response?: { status?: number } };
  return e?.code === 400 ||
    e?.code === 404 ||
    e?.response?.status === 400 ||
    e?.response?.status === 404;
}

async function assertGooglePremium(
  productId: string,
  purchaseToken: string
): Promise<PremiumAssertResult> {
  const credsPath = process.env.GOOGLE_APPLICATION_CREDENTIALS;
  if (!credsPath) {
    if (process.env.NODE_ENV === 'production') {
      console.error('[IAP] GOOGLE_APPLICATION_CREDENTIALS missing in production');
      return { kind: 'misconfigured' };
    }
    console.warn('[IAP] GOOGLE_APPLICATION_CREDENTIALS not set (dev)');
    return { kind: 'misconfigured' };
  }

  const auth = new GoogleAuth({
    scopes: ['https://www.googleapis.com/auth/androidpublisher'],
  });
  const authClient = await auth.getClient();
  const pub = androidpublisher({
    version: 'v3',
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    auth: authClient as any,
  });

  let data;
  try {
    const purchase = await pub.purchases.products.get({
      packageName: PACKAGE_NAME,
      productId,
      token: purchaseToken,
    });
    data = purchase.data;
  } catch (err) {
    const status = (err as { response?: { status?: number } })?.response?.status;
    if (status === 403) {
      console.error(
        '[IAP] Google Play API 403 — enable "Google Play Android Developer API" in Google Cloud for the service account project and link Play Console API access (see VERIFY_PURCHASE_SETUP.md).',
        err
      );
    } else {
      console.error('[IAP] Google Play API error:', err);
    }
    if (isGooglePurchaseNotFound(err)) return { kind: 'invalid' };
    return { kind: 'transient' };
  }

  const purchaseState = data.purchaseState ?? -1;
  if (purchaseState === 2) return { kind: 'pending' };
  if (purchaseState === 0) return { kind: 'valid' };
  console.log(`[IAP] Google invalid purchaseState=${purchaseState}`);
  return { kind: 'invalid' };
}

function parseGoogleExpiryMillis(data: {
  expiryTimeMillis?: string | null;
  lineItems?: Array<{ expiryTime?: string | null }>;
}): string | null {
  if (data.expiryTimeMillis) {
    const n = Number(data.expiryTimeMillis);
    if (Number.isFinite(n) && n > 0) return new Date(n).toISOString();
  }
  const line = data.lineItems?.[0]?.expiryTime;
  if (line) {
    const d = new Date(line);
    if (!Number.isNaN(d.getTime())) return d.toISOString();
  }
  return null;
}

async function assertGoogleSubscription(
  productId: string,
  purchaseToken: string,
): Promise<PremiumAssertResult> {
  const credsPath = process.env.GOOGLE_APPLICATION_CREDENTIALS;
  if (!credsPath) {
    if (process.env.NODE_ENV === 'production') {
      console.error('[IAP] GOOGLE_APPLICATION_CREDENTIALS missing in production');
      return { kind: 'misconfigured' };
    }
    return { kind: 'misconfigured' };
  }

  const auth = new GoogleAuth({
    scopes: ['https://www.googleapis.com/auth/androidpublisher'],
  });
  const authClient = await auth.getClient();
  const pub = androidpublisher({
    version: 'v3',
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    auth: authClient as any,
  });

  try {
    const sub = await pub.purchases.subscriptionsv2.get({
      packageName: PACKAGE_NAME,
      token: purchaseToken,
    });
    const data = sub.data;
    const state = data.subscriptionState;
    const expiresAt = parseGoogleExpiryMillis(data);

    if (state === 'SUBSCRIPTION_STATE_ACTIVE' || state === 'SUBSCRIPTION_STATE_IN_GRACE_PERIOD') {
      return { kind: 'valid', expiresAt };
    }
    if (state === 'SUBSCRIPTION_STATE_PENDING') {
      return { kind: 'pending' };
    }
    console.log(`[IAP] Google subscription state=${state}`);
    return { kind: 'invalid' };
  } catch (err) {
    if (isGooglePurchaseNotFound(err)) {
      try {
        const legacy = await pub.purchases.subscriptions.get({
          packageName: PACKAGE_NAME,
          subscriptionId: productId,
          token: purchaseToken,
        });
        const d = legacy.data;
        const paymentState = d.paymentState ?? -1;
        if (paymentState === 0 || paymentState === 1) {
          const exp = d.expiryTimeMillis ? new Date(Number(d.expiryTimeMillis)).toISOString() : null;
          return { kind: 'valid', expiresAt: exp };
        }
        if (paymentState === 2) return { kind: 'pending' };
        return { kind: 'invalid' };
      } catch (legacyErr) {
        if (isGooglePurchaseNotFound(legacyErr)) return { kind: 'invalid' };
      }
    }
    console.error('[IAP] Google subscription API error:', err);
    return { kind: 'transient' };
  }
}

async function callAppleVerifyReceipt(
  receiptData: string,
  url: string
): Promise<{ status: number; receipt?: { in_app?: Array<{ product_id: string }> }; latest_receipt_info?: Array<{ product_id: string }> }> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      'receipt-data': receiptData,
      'password': APPLE_SHARED_SECRET,
      'exclude-old-transactions': true,
    }),
  });
  return res.json();
}

function verifyStoreKit2JWS(
  jwsToken: string,
  expectedProductId: string
): { valid: boolean; productId?: string; error?: string } {
  const parts = jwsToken.split('.');
  if (parts.length !== 3) {
    return { valid: false, error: 'invalid_jws_format' };
  }

  try {
    const headerJson = Buffer.from(parts[0], 'base64url').toString();
    const payloadJson = Buffer.from(parts[1], 'base64url').toString();
    const header = JSON.parse(headerJson);
    const payload = JSON.parse(payloadJson);

    const x5cCerts: string[] = header.x5c;
    if (!x5cCerts || x5cCerts.length < 2) {
      return { valid: false, error: 'missing_x5c_certs' };
    }

    const certs = x5cCerts.map((b64: string) => {
      const pem = `-----BEGIN CERTIFICATE-----\n${b64}\n-----END CERTIFICATE-----`;
      return new X509Certificate(pem);
    });

    for (let i = 0; i < certs.length - 1; i++) {
      if (!certs[i].checkIssued(certs[i + 1])) {
        return { valid: false, error: 'broken_cert_chain' };
      }
    }

    const rootCert = certs[certs.length - 1];
    if (rootCert.fingerprint256 !== APPLE_ROOT_CA_G3_FINGERPRINT) {
      return { valid: false, error: 'untrusted_root_cert' };
    }

    const signatureInput = `${parts[0]}.${parts[1]}`;
    const signatureBytes = Buffer.from(parts[2], 'base64url');
    const leafKey = certs[0].publicKey;
    const verifier = createVerify('SHA256');
    verifier.update(signatureInput);
    if (!verifier.verify({ key: leafKey, dsaEncoding: 'ieee-p1363' }, signatureBytes)) {
      return { valid: false, error: 'invalid_signature' };
    }

    if (payload.bundleId && payload.bundleId !== APPLE_BUNDLE_ID) {
      return { valid: false, error: 'bundle_mismatch' };
    }

    const txProductId: string = payload.productId;
    const hasProduct =
      txProductId === expectedProductId ||
      KNOWN_PREMIUM_PRODUCT_IDS.includes(txProductId);

    return { valid: hasProduct, productId: txProductId };
  } catch (e) {
    console.error('[IAP] iOS JWS decode error:', e);
    return { valid: false, error: 'jws_decode_error' };
  }
}

async function assertApplePremium(
  productId: string,
  receiptData: string
): Promise<PremiumAssertResult> {
  try {
    const sanitized = receiptData.replace(/\s/g, '');
    const isJWS = sanitized.startsWith('eyJ') && sanitized.includes('.');

    if (isJWS) {
      const result = verifyStoreKit2JWS(sanitized, productId);
      return result.valid ? { kind: 'valid' } : { kind: 'invalid' };
    }

    if (!APPLE_SHARED_SECRET) {
      console.error('[IAP] APPLE_SHARED_SECRET missing');
      return { kind: 'misconfigured' };
    }

    let appleResponse = await callAppleVerifyReceipt(sanitized, APPLE_PRODUCTION_URL);
    if (appleResponse.status === 21007) {
      appleResponse = await callAppleVerifyReceipt(sanitized, APPLE_SANDBOX_URL);
    }

    if (appleResponse.status !== 0) {
      return { kind: 'invalid' };
    }

    const inAppProducts = appleResponse.receipt?.in_app ?? [];
    const latestProducts = appleResponse.latest_receipt_info ?? [];
    const allProductIds = [
      ...inAppProducts.map(p => p.product_id),
      ...latestProducts.map(p => p.product_id),
    ];

    const hasProduct =
      allProductIds.includes(productId) ||
      allProductIds.some(id => KNOWN_PREMIUM_PRODUCT_IDS.includes(id));

    return hasProduct ? { kind: 'valid' } : { kind: 'invalid' };
  } catch (err) {
    console.error('[IAP] iOS verify error:', err);
    return { kind: 'transient' };
  }
}

/**
 * Verify a one-time premium purchase (Google Play or App Store).
 */
export async function assertPremiumPurchase(
  productId: string,
  purchaseToken: string,
  source?: string
): Promise<PremiumAssertResult> {
  if (!productId || !purchaseToken) return { kind: 'invalid' };

  if (source === 'app_store') {
    return assertApplePremium(productId, purchaseToken);
  }

  if (isSubscriptionProductId(productId)) {
    return assertGoogleSubscription(productId, purchaseToken);
  }

  return assertGooglePremium(productId, purchaseToken);
}
