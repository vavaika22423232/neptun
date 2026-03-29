import { Suspense } from 'react';
import HomePageClient from './HomePageClient';

// Server Component — reads searchParams at request time
// so ?embed=1 is resolved during SSR, not after hydration
export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = await searchParams;
  const isEmbed = params.embed === '1';

  return (
    <Suspense fallback={<div className="h-full w-full bg-[var(--surface-dim)]" />}>
      <HomePageClient isEmbed={isEmbed} />
    </Suspense>
  );
}
