import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Google redirects to this Next.js route after OAuth consent.
 * We forward the code+state to the FastAPI backend which validates,
 * sets the httpOnly cookie, and returns the final redirect destination.
 */
export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl;
  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const error = searchParams.get("error");

  if (error) {
    return NextResponse.redirect(new URL(`/login?error=oauth_failed`, req.url));
  }

  if (!code || !state) {
    return NextResponse.redirect(new URL("/login?error=oauth_failed", req.url));
  }

  // Forward the oauth_state cookie so backend can validate CSRF
  const oauthStateCookie = req.cookies.get("oauth_state")?.value ?? "";

  // Derive the public origin so the backend builds the matching redirect_uri
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host") ?? req.nextUrl.host;
  const proto = req.headers.get("x-forwarded-proto") ?? req.nextUrl.protocol.replace(":", "");
  const publicOrigin = `${proto}://${host}`;

  const backendUrl = `${API_BASE}/api/v1/auth/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`;

  const backendResp = await fetch(backendUrl, {
    method: "GET",
    redirect: "manual",
    headers: {
      Cookie: `oauth_state=${oauthStateCookie}`,
      "X-Forwarded-Proto": proto,
      "X-Forwarded-Host": host,
    },
  });

  const setCookies = backendResp.headers.getSetCookie();
  const location = backendResp.headers.get("location") ?? "/";

  // Extract the JWT value from the backend's ecc_token Set-Cookie header
  // e.g. "ecc_token=eyJ...; Path=/; HttpOnly; SameSite=lax; Max-Age=28800"
  const eccTokenEntry = setCookies.find((c) => c.startsWith("ecc_token="));
  const eccTokenValue = eccTokenEntry?.split(";")[0].split("=").slice(1).join("=");

  if (!eccTokenValue) {
    console.error("[auth/callback] no ecc_token in backend response", setCookies);
    return NextResponse.redirect(new URL("/login?error=oauth_failed", req.url));
  }

  // Use the absolute location from backend (it already has the correct public origin)
  // Fall back to the public origin root if location is relative
  const finalDest = location.startsWith("http") ? location : `${publicOrigin}${location}`;
  const response = NextResponse.redirect(new URL(finalDest));

  // Set the cookie via Next.js native API — this is reliable and sets it
  // for the Next.js origin (localhost:3000) so the browser always sends it
  // back on subsequent requests to this origin.
  response.cookies.set("ecc_token", eccTokenValue, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 8 * 60 * 60, // 8 hours
  });
  response.cookies.delete("oauth_state");

  return response;
}
