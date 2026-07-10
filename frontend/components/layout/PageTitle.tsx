'use client';

import { usePathname } from 'next/navigation';

const ROUTE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/dashboard/inbox': 'AI Inbox',
  '/dashboard/documents': 'Document Intelligence',
  '/dashboard/analytics': 'Analytics',
  '/dashboard/history': 'Workflow History',
  '/dashboard/admin': 'Admin',
};

export function PageTitle() {
  const pathname = usePathname();

  // Find the most specific matching route
  const title =
    ROUTE_TITLES[pathname] ??
    Object.entries(ROUTE_TITLES)
      .filter(([route]) => pathname.startsWith(route))
      .sort((a, b) => b[0].length - a[0].length)[0]?.[1] ??
    'FlowPilot AI';

  return (
    <h1 className="text-lg font-semibold truncate max-w-[200px] sm:max-w-none">
      {title}
    </h1>
  );
}
