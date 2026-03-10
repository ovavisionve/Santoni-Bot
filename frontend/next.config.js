/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://backend:8000"}/api/:path*`,
      },
    ];
  },
};

// Only wrap with Sentry if DSN is configured and package is available
let finalConfig = nextConfig;
if (process.env.NEXT_PUBLIC_SENTRY_DSN) {
  try {
    const { withSentryConfig } = require("@sentry/nextjs");
    finalConfig = withSentryConfig(nextConfig, {
      // Suppress source map upload logs during build
      silent: true,
      disableLogger: true,

      // Upload source maps for better stack traces in Sentry
      // Requires SENTRY_AUTH_TOKEN, SENTRY_ORG, and SENTRY_PROJECT env vars
      widenClientFileUpload: true,

      // Automatically tree-shake Sentry logger statements to reduce bundle size
      disableServerWebpackPlugin: false,
      disableClientWebpackPlugin: false,

      // Hide source maps from users while still uploading them to Sentry
      hideSourceMaps: true,

      // Tunnel Sentry events through the Next.js app to avoid ad-blockers
      // Uncomment if needed:
      // tunnelRoute: "/monitoring",

      // Automatically instrument Next.js data fetching and API routes
      autoInstrumentServerFunctions: true,
      autoInstrumentMiddleware: true,
    });
  } catch {
    // @sentry/nextjs not installed, skip
  }
}
module.exports = finalConfig;
