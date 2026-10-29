import type { NextRequest } from "next/server";

/**
 * Public origin of the app as seen by the browser (e.g. http://localhost:3000).
 *
 * In Docker the Next.js server listens on 0.0.0.0, so request.nextUrl.origin can be
 * "http://0.0.0.0:3000", which browsers cannot open. The Host / X-Forwarded-* headers
 * carry the address the user actually typed, so we build redirects from them.
 */
export function publicOrigin(request: NextRequest): string {
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  if (!host) return request.nextUrl.origin;
  const proto =
    request.headers.get("x-forwarded-proto")?.split(",")[0].trim() ??
    request.nextUrl.protocol.replace(":", "");
  return `${proto}://${host}`;
}
