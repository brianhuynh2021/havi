import { NextResponse, type NextRequest } from "next/server";

const LEGACY_ALIASES: Record<string, string> = {
  "/gioi-thieu": "/about",
  "/bao-mat": "/privacy",
  "/dieu-khoan": "/terms",
  "/huong-dan-xoa-du-lieu": "/data-deletion",
  "/dang-nhap": "/login",
  "/dang-ky": "/signup",
  "/quen-mat-khau": "/forgot-password",
  "/noi-dung": "/app/content",
  "/lich-dang": "/app/calendar",
  "/khach-tiem-nang": "/app/leads",
  "/bao-cao": "/app/reports",
  "/cai-dat": "/app/settings",
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
  const sessionCookie = request.cookies.get("havi_session")?.value;
  const hasSession = Boolean(sessionCookie);

  // 1. Alias Rewrites for legacy Vietnamese URLs
  if (pathname in LEGACY_ALIASES) {
    return NextResponse.rewrite(new URL(LEGACY_ALIASES[pathname], request.url));
  }

  // 2. Root route '/' Gateway Logic
  if (pathname === "/") {
    if (hasSession) {
      return NextResponse.redirect(new URL("/app", request.url));
    }
    return NextResponse.rewrite(new URL("/about", request.url));
  }

  // 3. Protected App Realm (/app/*)
  if (pathname.startsWith("/app") && !hasSession) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // 4. Guest Auth Routes (/login, /signup)
  if ((pathname === "/login" || pathname === "/signup") && hasSession) {
    return NextResponse.redirect(new URL("/app", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|icon.svg|images|ai-samples).*)",
  ],
};
