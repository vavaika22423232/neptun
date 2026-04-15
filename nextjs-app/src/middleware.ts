import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { handleCors, handlePreflight } from '@/lib/cors';

const SESSION_COOKIE_NAME = 'neptun_admin_session';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname.startsWith('/api/')) {
    const preflightResponse = handlePreflight(request);
    if (preflightResponse) return preflightResponse;

    const response = NextResponse.next();
    return handleCors(request, response);
  }

  if (pathname.startsWith('/admin') && pathname !== '/admin/login') {
    const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
    if (!token) {
      return NextResponse.redirect(new URL('/admin/login', request.url));
    }
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-neptun-pathname', pathname);

  return NextResponse.next({ request: { headers: requestHeaders } });
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|icons/|manifest\\.json|robots\\.txt|sitemap\\.xml).*)',
  ],
};
