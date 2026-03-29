import { Suspense } from 'react';
import DashboardClient from './DashboardClient';

/**
 * Inline CSS that forces light theme variables at the server-render level.
 * This <style> tag ships in the HTML BEFORE any JS executes,
 * so the WebView never flashes dark.
 */
const LIGHT_THEME_CSS = `
:root, :root.dark, html, html.dark {
  --surface: #f5f7fa !important;
  --surface-dim: #e8ecf0 !important;
  --surface-container-lowest: #ffffff !important;
  --surface-container-low: #f0f3f8 !important;
  --surface-container: #e8ecf2 !important;
  --surface-container-high: #e0e5ec !important;
  --surface-container-highest: #d8dee6 !important;
  --on-surface: #1a1d24 !important;
  --on-surface-variant: #4a4e58 !important;
  --outline: #6c7079 !important;
  --outline-variant: #a8acb4 !important;
  --primary: #00668a !important;
  --primary-container: #b8e5ff !important;
  --on-primary: #ffffff !important;
  --on-primary-container: #003548 !important;
  --secondary: #8b5a00 !important;
  --secondary-container: #ffddb3 !important;
  --on-secondary-container: #2b1700 !important;
  --tertiary: #9e0042 !important;
  --tertiary-container: #ffd9e6 !important;
  --on-tertiary-container: #3d0019 !important;
  --error: #ba1a1a !important;
  --error-container: #ffdad6 !important;
  --on-error-container: #410002 !important;
  color-scheme: light !important;
}
body {
  background: #e8ecf0 !important;
  color: #1a1d24 !important;
}
`;

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;
  const isEmbed = params.embed === '1';
  const theme = params.theme === 'light' ? 'light' : 'dark';

  return (
    <>
      {theme === 'light' && (
        <style dangerouslySetInnerHTML={{ __html: LIGHT_THEME_CSS }} />
      )}
      <Suspense fallback={<div className="w-full h-full bg-[var(--surface)]" />}>
        <DashboardClient isEmbed={isEmbed} theme={theme} />
      </Suspense>
    </>
  );
}
