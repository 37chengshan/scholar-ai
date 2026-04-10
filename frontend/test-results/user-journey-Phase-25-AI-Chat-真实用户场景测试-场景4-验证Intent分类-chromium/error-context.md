# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: user-journey.spec.ts >> Phase 25: AI Chat 真实用户场景测试 >> 场景4: 验证Intent分类
- Location: e2e/user-journey.spec.ts:125:3

# Error details

```
Error: Channel closed
```

```
Error: page.waitForTimeout: Target page, context or browser has been closed
```

```
Error: browserContext.close: Test ended.
Browser logs:

<launching> /Users/cc/Library/Caches/ms-playwright/chromium-1217/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing --disable-field-trial-config --disable-background-networking --disable-background-timer-throttling --disable-backgrounding-occluded-windows --disable-back-forward-cache --disable-breakpad --disable-client-side-phishing-detection --disable-component-extensions-with-background-pages --disable-component-update --no-default-browser-check --disable-default-apps --disable-dev-shm-usage --disable-extensions --disable-features=AvoidUnnecessaryBeforeUnloadCheckSync,BoundaryEventDispatchTracksNodeRemoval,DestroyProfileOnBrowserClose,DialMediaRouteProvider,GlobalMediaControls,HttpsUpgrades,LensOverlay,MediaRouter,PaintHolding,ThirdPartyStoragePartitioning,Translate,AutoDeElevate,RenderDocument,OptimizationHints --enable-features=CDPScreenshotNewSurface --allow-pre-commit-input --disable-hang-monitor --disable-ipc-flooding-protection --disable-popup-blocking --disable-prompt-on-repost --disable-renderer-backgrounding --force-color-profile=srgb --metrics-recording-only --no-first-run --password-store=basic --use-mock-keychain --no-service-autorun --export-tagged-pdf --disable-search-engine-choice-screen --unsafely-disable-devtools-self-xss-warnings --edge-skip-compat-layer-relaunch --enable-automation --disable-infobars --disable-search-engine-choice-screen --disable-sync --enable-unsafe-swiftshader --no-sandbox --user-data-dir=/var/folders/q8/c82vj8fs04n4bt80pynrqsvc0000gn/T/playwright_chromiumdev_profile-4046wf --remote-debugging-pipe --no-startup-window
<launched> pid=60531
[pid=60531] <gracefully close start>
[pid=60531][err] [60531:17444057:0409/084059.870106:ERROR:base/process/process_mac.cc:98] task_policy_set TASK_SUPPRESSION_POLICY: (os/kern) invalid argument (4)
```