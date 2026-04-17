Invoke the e2e-runner agent to generate and execute end-to-end tests using Playwright.

Handles:
- Test generation for critical user journeys using Page Object Model
- Execution across Chromium, Firefox, and WebKit
- Artifact capture on failure (screenshots, video, traces)
- Flaky test identification and quarantine

**Critical safety rule: Tests involving real money, payments, or destructive actions MUST target staging/testnet only. Never run against production.**

Run:
```bash
npx playwright test
npx playwright show-report
```

Scope / flow to test: $ARGUMENTS
