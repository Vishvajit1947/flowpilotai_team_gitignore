import { DashboardShell } from '@/components/layout/DashboardShell';
import { PageTransition } from '@/components/layout/PageTransition';

export default function DashboardPageLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <DashboardShell>
      <PageTransition>{children}</PageTransition>
    </DashboardShell>
  );
}
