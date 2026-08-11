const { withAndroidManifest, withDangerousMod, AndroidConfig } = require('@expo/config-plugins');
const { generateImageAsync } = require('@expo/image-utils');
const fs = require('fs');
const path = require('path');

// Launcher icon sizes per density bucket
const MIPMAP_SIZES = {
  'mipmap-mdpi':    48,
  'mipmap-hdpi':    72,
  'mipmap-xhdpi':   96,
  'mipmap-xxhdpi':  144,
  'mipmap-xxxhdpi': 192,
};

async function generateResizedIcons(projectRoot, srcPath, outName) {
  for (const [density, size] of Object.entries(MIPMAP_SIZES)) {
    const dir = path.join(projectRoot, 'android/app/src/main/res', density);
    fs.mkdirSync(dir, { recursive: true });
    const { source } = await generateImageAsync(
      { projectRoot, cacheType: `dynamic-icon-${outName}-${density}` },
      { src: srcPath, width: size, height: size, resizeMode: 'cover' }
    );
    fs.writeFileSync(path.join(dir, `${outName}.png`), source);
  }
}

// Modify AndroidManifest to add activity-alias entries for icon switching
function withDynamicIconManifest(config) {
  return withAndroidManifest(config, (mod) => {
    const manifest = mod.modResults;
    const app = AndroidConfig.Manifest.getMainApplicationOrThrow(manifest);

    // Remove LAUNCHER intent-filter from .MainActivity so only aliases are launchable
    if (app.activity) {
      for (const activity of app.activity) {
        if (
          activity.$['android:name'] === '.MainActivity' &&
          activity['intent-filter']
        ) {
          activity['intent-filter'] = activity['intent-filter'].filter((filter) => {
            const cats = filter.category ?? [];
            return !cats.some(
              (c) => c.$?.['android:name'] === 'android.intent.category.LAUNCHER'
            );
          });
        }
      }
    }

    if (!app['activity-alias']) app['activity-alias'] = [];
    const existingNames = app['activity-alias'].map((a) => a.$['android:name']);

    const launcherIntentFilter = [{
      action:   [{ $: { 'android:name': 'android.intent.action.MAIN' } }],
      category: [{ $: { 'android:name': 'android.intent.category.LAUNCHER' } }],
    }];

    // Default alias (enabled) — same icon as the original app
    if (!existingNames.includes('.MainActivityDefault')) {
      app['activity-alias'].push({
        $: {
          'android:name':           '.MainActivityDefault',
          'android:enabled':        'true',
          'android:exported':       'true',
          'android:icon':           '@mipmap/ic_launcher',
          'android:roundIcon':      '@mipmap/ic_launcher_round',
          'android:targetActivity': '.MainActivity',
        },
        'intent-filter': launcherIntentFilter,
      });
    }

    // Alert alias (disabled by default) — red alert icon
    if (!existingNames.includes('.MainActivityAlert')) {
      app['activity-alias'].push({
        $: {
          'android:name':           '.MainActivityAlert',
          'android:enabled':        'false',
          'android:exported':       'true',
          'android:icon':           '@mipmap/ic_launcher_alert',
          'android:roundIcon':      '@mipmap/ic_launcher_alert',
          'android:targetActivity': '.MainActivity',
        },
        'intent-filter': launcherIntentFilter,
      });
    }

    mod.modResults = manifest;
    return mod;
  });
}

// Generate resized alert icon images into Android mipmap directories
function withDynamicIconFiles(config) {
  return withDangerousMod(config, [
    'android',
    async (mod) => {
      const { projectRoot } = mod.modRequest;

      const alertIconSrc    = path.join(projectRoot, 'assets/icon-alert.png');
      const adaptiveAlertSrc = path.join(projectRoot, 'assets/adaptive-icon-alert.png');

      // Flat launcher icon for all densities (non-adaptive fallback)
      await generateResizedIcons(projectRoot, alertIconSrc, 'ic_launcher_alert');

      // Foreground layer for adaptive icon (API 26+)
      await generateResizedIcons(projectRoot, adaptiveAlertSrc, 'ic_launcher_alert_foreground');

      // Background solid-color drawable (AAPT rejects inline hex in adaptive icon XML)
      const drawableDir = path.join(projectRoot, 'android/app/src/main/res/drawable');
      fs.mkdirSync(drawableDir, { recursive: true });
      fs.writeFileSync(
        path.join(drawableDir, 'ic_launcher_alert_bg.xml'),
`<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android">
    <solid android:color="#CC2222"/>
</shape>`
      );

      // Adaptive icon XML descriptor (references drawable, not raw hex)
      const anydpiDir = path.join(
        projectRoot,
        'android/app/src/main/res/mipmap-anydpi-v26'
      );
      fs.mkdirSync(anydpiDir, { recursive: true });
      fs.writeFileSync(
        path.join(anydpiDir, 'ic_launcher_alert.xml'),
`<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_alert_bg"/>
    <foreground android:drawable="@mipmap/ic_launcher_alert_foreground"/>
</adaptive-icon>`
      );

      return mod;
    },
  ]);
}

module.exports = function withDynamicIcon(config) {
  config = withDynamicIconManifest(config);
  config = withDynamicIconFiles(config);
  return config;
};
