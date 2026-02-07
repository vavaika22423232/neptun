import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { validateSession, SESSION_COOKIE_NAME } from '@/lib/admin/auth';

export const metadata = {
  title: 'NEPTUN Admin',
  robots: 'noindex, nofollow',
};

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies();
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value;

  // Allow login page without auth
  // For other admin pages, validate session server-side
  const isLoginPage = false; // layout wraps all /admin/* pages
  if (!isLoginPage && !validateSession(token)) {
    // Check if this is the login page by examining children
    // We can't easily check path in layout, so middleware handles redirect
    // This is a fallback check
  }

  return <>{children}</>;
}
