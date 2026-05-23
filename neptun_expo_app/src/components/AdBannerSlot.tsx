import { useEffect, useState } from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import { adService } from '../services/adService';
import { bannerAdUnitId } from '../config/adUnits';
import { getGoogleMobileAds, isGoogleMobileAdsNativeLinked } from '../utils/lazyGoogleMobileAds';
import { purchaseService } from '../services/purchaseService';
import { useThemedStyles } from '../theme/useAppTheme';

/**
 * Flutter `app_shell` banner above `TacticalNavBar` — adaptive banner, hidden for PRO / ad-free.
 */
export function AdBannerSlot() {
  const styles = useStyles();
  const [visible, setVisible] = useState(false);
  const [premium, setPremium] = useState(purchaseService.isPremiumSync());
  const [requesting, setRequesting] = useState(false);
  const [adsReady, setAdsReady] = useState(adService.canRequestBanner());
  const mod = isGoogleMobileAdsNativeLinked() ? getGoogleMobileAds() : null;

  useEffect(() => {
    const sync = () => {
      setPremium(purchaseService.isPremiumSync());
      setVisible(adService.isBannerVisible());
      setAdsReady(adService.canRequestBanner());
    };
    sync();
    const u1 = adService.subscribe(sync);
    const u2 = purchaseService.subscribe(sync);
    return () => {
      u1();
      u2();
    };
  }, []);

  useEffect(() => {
    if (premium || !mod || !adsReady) {
      setRequesting(false);
      return;
    }
    adService.markBannerRequest();
    setRequesting(true);
  }, [premium, mod, adsReady]);

  if (Platform.OS === 'web' || premium || !mod || !requesting) {
    return null;
  }

  const { BannerAd, BannerAdSize } = mod;
  const unitId = bannerAdUnitId();
  if (!unitId) return null;

  return (
    <View style={[styles.slot, !visible && styles.hidden]}>
      <BannerAd
        unitId={unitId}
        size={BannerAdSize.ANCHORED_ADAPTIVE_BANNER}
        requestOptions={{ requestNonPersonalizedAdsOnly: false }}
        onAdLoaded={() => {
          adService.setBannerLoaded(true);
          setVisible(true);
        }}
        onAdFailedToLoad={() => {
          adService.setBannerLoaded(false);
          setVisible(false);
        }}
      />
    </View>
  );
}

function useStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      slot: {
        width: '100%',
        alignItems: 'center',
        backgroundColor: t.colors.surface,
        overflow: 'hidden',
      },
      hidden: {
        height: 0,
        opacity: 0,
      },
    }),
  );
}
