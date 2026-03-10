/**
 * Sentry helper utilities for SantoniBot frontend.
 *
 * All functions are safe to call even when Sentry is not configured.
 * They check for the DSN at runtime and become no-ops when disabled.
 */

const isSentryEnabled = (): boolean => {
  return !!process.env.NEXT_PUBLIC_SENTRY_DSN;
};

/**
 * Lazily import Sentry to avoid errors when the package is not installed.
 */
async function getSentry() {
  if (!isSentryEnabled()) return null;
  try {
    return await import("@sentry/nextjs");
  } catch {
    return null;
  }
}

/**
 * Set the authenticated user context in Sentry.
 * Call this after a successful login.
 */
export async function setSentryUser(user: {
  id: number | string;
  username: string;
  department?: string;
  role?: string;
}): Promise<void> {
  const Sentry = await getSentry();
  if (!Sentry) return;

  Sentry.setUser({
    id: String(user.id),
    username: user.username,
  });
  if (user.department) {
    Sentry.setTag("user.department", user.department);
  }
  if (user.role) {
    Sentry.setTag("user.role", user.role);
  }
}

/**
 * Clear the Sentry user context.
 * Call this on logout.
 */
export async function clearSentryUser(): Promise<void> {
  const Sentry = await getSentry();
  if (!Sentry) return;

  Sentry.setUser(null);
}

/**
 * Capture a chat-related error with additional context.
 */
export async function captureChatError(
  error: Error | unknown,
  context: {
    message?: string;
    agent?: string;
    conversationId?: number;
  } = {}
): Promise<void> {
  const Sentry = await getSentry();
  if (!Sentry) return;

  Sentry.withScope((scope) => {
    scope.setTag("feature", "chat");
    if (context.agent) {
      scope.setTag("agent", context.agent);
    }
    scope.setContext("chat_context", {
      message: context.message,
      agent: context.agent,
      conversationId: context.conversationId,
    });
    if (error instanceof Error) {
      Sentry.captureException(error);
    } else {
      Sentry.captureMessage(String(error), "error");
    }
  });
}

/**
 * Track a page navigation as a Sentry breadcrumb.
 */
export async function trackNavigation(
  from: string,
  to: string
): Promise<void> {
  const Sentry = await getSentry();
  if (!Sentry) return;

  Sentry.addBreadcrumb({
    category: "navigation",
    message: `${from} -> ${to}`,
    level: "info",
  });
}

/**
 * Add a custom breadcrumb for debugging context.
 */
export async function addBreadcrumb(
  category: string,
  message: string,
  data?: Record<string, unknown>
): Promise<void> {
  const Sentry = await getSentry();
  if (!Sentry) return;

  Sentry.addBreadcrumb({
    category,
    message,
    level: "info",
    data,
  });
}
