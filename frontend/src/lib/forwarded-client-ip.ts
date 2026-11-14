import { NextRequest } from "next/server";

/**
 * Forward the ingress proxy's client chain to the API. The API accepts it only
 * when the direct peer belongs to TRUSTED_PROXY_IPS. Configure the public
 * reverse proxy to overwrite, not append to, X-Forwarded-For.
 */
export function forwardedClientIpHeader(request: NextRequest): Record<string, string> {
  const forwarded = request.headers.get("x-forwarded-for");
  if (!forwarded || forwarded.length > 256) return {};
  return { "x-forwarded-for": forwarded };
}
