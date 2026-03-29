import { NextResponse } from 'next/server';
import { androidpublisher } from '@googleapis/androidpublisher';
import { GoogleAuth } from 'google-auth-library';
import { X509Certificate, createVerify } from 'crypto';

const PACKAGE_NAME =
  process.env.GOOGLE_PLAY_PACKAGE_NAME || 'com.neptunalarm.neptun_alarm_app';
const APPLE_SHARED_SECRET = process.env.APPLE_SHARED_SECRET;
const APPLE_BUNDLE_ID = 'com.neptunalarm.neptunAlarmApp';

const APPLE_PRODUCTION_URL = 'https://buy.itunes.apple.com/verifyReceipt';
const APPLE_SANDBOX_URL = 'https://sandbox.itunes.apple.com/verifyReceipt';

const APPLE_ROOT_CA_G3_FINGERPRINT =
  '63:34:3A:BF:B8:9A:6A:03:EB:B5:7E:9B:3F:5F:A7:BE:7C:4F:5C:75:6F:30:17:B3:A8:C4:88:C3:65:3E:91:79';

/** POST /api/verify-purchase
 * Verify in-app purchase via Google Play or App Store API.
 * Google: GOOGLE_APPLICATION_CREDENTIALS required.
 * iOS: APPLE_SHARED_SECRET required (from App Store Connect).
 *
 * Legacy: Accepts old product IDs (premium, premium_100_uah etc.) for users
 * who bought before current product (premium_150_uah) was introduced.
 */
const KNOWN_PREMIUM_PRODUCT_IDS = [
  'premium_150_uah',
  'premium_100_uah',
  'premium',
  'com.neptunalarm.premium',
];
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { productId, purchaseToken, source } = body;

    if (!productId || !purchaseToken) {
      return NextResponse.json(
        { error: 'Missing productId or purchaseToken' },
        { status: 400 }
      );
    }

    console.log(`[PURCHASE] Verify: ${productId} from ${source || 'unknown'}`);

    // iOS App Store
    if (source === 'app_store') {
      return await verifyApplePurchase(productId, purchaseToken);
    }

    // Google Play (default)

    const credsPath = process.env.GOOGLE_APPLICATION_CREDENTIALS;
    if (!credsPath) {
      if (process.env.NODE_ENV === 'production') {
        console.error('[PURCHASE] GOOGLE_APPLICATION_CREDENTIALS missing in production — rejecting verify');
        return NextResponse.json(
          { valid: false, error: 'server_misconfigured' },
          { status: 503 },
        );
      }
      console.warn('[PURCHASE] GOOGLE_APPLICATION_CREDENTIALS not set (dev) — cannot verify Play purchase');
      return NextResponse.json({ valid: false, error: 'google_not_configured' }, { status: 503 });
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

    const purchase = await pub.purchases.products.get({
      packageName: PACKAGE_NAME,
      productId,
      token: purchaseToken,
    });

    const data = purchase.data;

    // purchaseState: 0 = Purchased, 1 = Canceled, 2 = Pending
    const purchaseState = data.purchaseState ?? -1;
    // acknowledgementState: 0 = Not acknowledged, 1 = Acknowledged (both valid for one-time)
    const acknowledgementState = data.acknowledgementState ?? 0;

    const valid = purchaseState === 0;

    if (!valid) {
      console.log(
        `[PURCHASE] Invalid: purchaseState=${purchaseState} acknowledgementState=${acknowledgementState}`
      );
    }

    return NextResponse.json({ valid });
  } catch (err) {
    console.error('[PURCHASE] Verify error:', err);
    return NextResponse.json({ valid: false }, { status: 200 });
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

/**
 * Verify a StoreKit 2 JWS (signed transaction) from the `in_app_purchase` Flutter plugin.
 * Decodes the JWS, verifies the Apple certificate chain + ES256 signature,
 * and checks the productId against known premium IDs.
 */
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

    // Verify certificate chain from x5c header
    const x5cCerts: string[] = header.x5c;
    if (!x5cCerts || x5cCerts.length < 2) {
      return { valid: false, error: 'missing_x5c_certs' };
    }

    const certs = x5cCerts.map((b64: string) => {
      const pem = `-----BEGIN CERTIFICATE-----\n${b64}\n-----END CERTIFICATE-----`;
      return new X509Certificate(pem);
    });

    // Verify chain: each cert should be issued by the next one
    for (let i = 0; i < certs.length - 1; i++) {
      if (!certs[i].checkIssued(certs[i + 1])) {
        return { valid: false, error: 'broken_cert_chain' };
      }
    }

    // Verify root cert fingerprint matches Apple Root CA G3
    const rootCert = certs[certs.length - 1];
    const rootFingerprint = rootCert.fingerprint256;
    if (rootFingerprint !== APPLE_ROOT_CA_G3_FINGERPRINT) {
      console.error(
        `[PURCHASE] iOS JWS: root cert fingerprint mismatch: ${rootFingerprint}`
      );
      return { valid: false, error: 'untrusted_root_cert' };
    }

    // Verify ES256 signature using the leaf certificate's public key
    const signatureInput = `${parts[0]}.${parts[1]}`;
    const signatureBytes = Buffer.from(parts[2], 'base64url');
    const leafKey = certs[0].publicKey;
    const verifier = createVerify('SHA256');
    verifier.update(signatureInput);
    if (!verifier.verify({ key: leafKey, dsaEncoding: 'ieee-p1363' }, signatureBytes)) {
      return { valid: false, error: 'invalid_signature' };
    }

    // Check bundleId
    if (payload.bundleId && payload.bundleId !== APPLE_BUNDLE_ID) {
      console.error(
        `[PURCHASE] iOS JWS: bundleId mismatch: ${payload.bundleId} !== ${APPLE_BUNDLE_ID}`
      );
      return { valid: false, error: 'bundle_mismatch' };
    }

    const txProductId: string = payload.productId;
    const hasProduct =
      txProductId === expectedProductId ||
      KNOWN_PREMIUM_PRODUCT_IDS.includes(txProductId);

    return { valid: hasProduct, productId: txProductId };
  } catch (e) {
    console.error('[PURCHASE] iOS JWS decode error:', e);
    return { valid: false, error: 'jws_decode_error' };
  }
}

async function verifyApplePurchase(
  productId: string,
  receiptData: string
): Promise<NextResponse> {
  try {
    const sanitized = receiptData.replace(/\s/g, '');
    const isJWS = sanitized.startsWith('eyJ') && sanitized.includes('.');

    console.log(
      `[PURCHASE] iOS receipt: length=${sanitized.length}, format=${isJWS ? 'JWS/StoreKit2' : 'receipt/StoreKit1'}`
    );

    // StoreKit 2 — JWS signed transaction
    if (isJWS) {
      const result = verifyStoreKit2JWS(sanitized, productId);
      console.log(
        `[PURCHASE] iOS JWS result: valid=${result.valid}, productId=${result.productId ?? 'n/a'}${result.error ? `, error=${result.error}` : ''}`
      );
      return NextResponse.json({ valid: result.valid });
    }

    // StoreKit 1 — traditional base64 receipt → verifyReceipt API
    if (!APPLE_SHARED_SECRET) {
      console.error('[PURCHASE] APPLE_SHARED_SECRET missing — cannot verify StoreKit 1 receipt');
      return NextResponse.json(
        { valid: false, error: 'server_misconfigured' },
        { status: 503 },
      );
    }

    let appleResponse = await callAppleVerifyReceipt(sanitized, APPLE_PRODUCTION_URL);

    // Status 21007 = sandbox receipt sent to production → retry with sandbox
    if (appleResponse.status === 21007) {
      console.log('[PURCHASE] iOS: sandbox receipt, retrying with sandbox URL');
      appleResponse = await callAppleVerifyReceipt(sanitized, APPLE_SANDBOX_URL);
    }

    if (appleResponse.status !== 0) {
      console.error(`[PURCHASE] iOS: Apple rejected receipt, status=${appleResponse.status}`);
      return NextResponse.json({ valid: false, error: `apple_status_${appleResponse.status}` });
    }

    const inAppProducts = appleResponse.receipt?.in_app ?? [];
    const latestProducts = appleResponse.latest_receipt_info ?? [];
    const allProductIds = [
      ...inAppProducts.map(p => p.product_id),
      ...latestProducts.map(p => p.product_id),
    ];

    console.log(`[PURCHASE] iOS receipt valid, products: [${allProductIds.join(', ')}]`);

    const hasProduct =
      allProductIds.includes(productId) ||
      allProductIds.some(id => KNOWN_PREMIUM_PRODUCT_IDS.includes(id));

    return NextResponse.json({ valid: hasProduct });
  } catch (err) {
    console.error('[PURCHASE] iOS verify error:', err);
    return NextResponse.json({ valid: false }, { status: 200 });
  }
}
