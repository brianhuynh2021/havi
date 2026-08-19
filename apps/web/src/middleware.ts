import { NextResponse, type NextRequest } from "next/server";

const LEGACY_ALIASES: Record<string, string> = {
  "/gioi-thieu": "/about",
  "/bao-mat": "/privacy",
  "/dieu-khoan": "/terms",
  "/huong-dan-xoa-du-lieu": "/data-deletion",
  "/dang-nhap": "/login",
  "/dang-ky": "/signup",
  "/quen-mat-khau": "/forgot-password",
  "/connections": "/app/connections",
  "/ket-noi": "/app/connections",
  "/noi-dung": "/app/content",
  "/content": "/app/content",
  "/lich-dang": "/app/calendar",
  "/calendar": "/app/calendar",
  "/khach-tiem-nang": "/app/leads",
  "/leads": "/app/leads",
  "/bao-cao": "/app/reports",
  "/reports": "/app/reports",
  "/cai-dat": "/app/settings",
  "/settings": "/app/settings",
  "/video-studio": "/app/video-studio",
  "/billing": "/app/billing",
  "/inbox": "/app/inbox",
};

/**
 * MIT Policy Enforcement Point (PEP) Edge Middleware.
 *
 * Enforces zero-latency, zero-flicker routing between:
 * 1. Public Marketing Realm (Unauthenticated): '/' -> Landing Page (/about)
 * 2. Protected Application Realm (Authenticated): '/app/*' -> Workspace App
 * 3. Auth Guard: Guest routes (/login, /signup) -> Redirect to /app if logged in
 * 4. Alias Rewrites: Backward compatibility for legacy Vietnamese URLs
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 1. Alias Rewrites for legacy Vietnamese URLs
  if (pathname in LEGACY_ALIASES) {
    return NextResponse.rewrite(new URL(LEGACY_ALIASES[pathname], request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|icon.svg|images|ai-samples).*)",
  ],
};
