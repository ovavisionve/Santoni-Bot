import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: process.env.NODE_ENV,
    release: `santonibot-frontend@${process.env.NEXT_PUBLIC_APP_VERSION || "1.1.0"}`,
    tracesSampleRate: 0.2,

    // Session Replay: record 0% of all sessions, but 100% of sessions with errors
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 1.0,

    // Do not send cookies, auth headers, or other PII
    sendDefaultPii: false,

    // Integrations
    integrations: [
      Sentry.replayIntegration({
        // Mask all text and block all media in replays for privacy
        maskAllText: true,
        blockAllMedia: true,
      }),
      Sentry.browserTracingIntegration(),
    ],

    // Ignore common non-actionable errors
    ignoreErrors: [
      // Browser extensions and network errors
      "ResizeObserver loop",
      "Network request failed",
      "Load failed",
      "Failed to fetch",
      // Next.js hydration (usually harmless)
      "Hydration failed",
      "Text content does not match",
    ],
  });
}
