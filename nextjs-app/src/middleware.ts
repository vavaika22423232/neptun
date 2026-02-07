import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const SESSION_COOKIE_NAME = 'neptun_admin_session';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Only protect /admin routes (not /admin/login and not /api/admin/auth/*)
  if (pathname.startsWith('/admin') && pathname !== '/admin/login') {
    const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
    if (!token) {
      return NextResponse.redirect(new URL('/admin/login', request.url));
    }
    // Note: full token validation happens server-side in layout.tsx
    // This middleware provides a fast redirect for missing cookies
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/admin/:path*'],
};
