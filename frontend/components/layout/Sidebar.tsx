'use client';

import {
  LayoutDashboard,
  Inbox,
  FileText,
  BarChart3,
  History,
  ChevronLeft,
  ChevronRight,
  LogOut,
} from 'lucide-react';
import { useUIStore } from '@/store/ui';
import { useAuth } from '@/hooks/useAuth';
import { NavItem } from './NavItem';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/dashboard/inbox', label: 'AI Inbox', icon: Inbox },
  {
    href: '/dashboard/documents',
    label: 'Document Intelligence',
    icon: FileText,
  },
  { href: '/dashboard/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/dashboard/history', label: 'Workflow History', icon: History },
] as const;

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebarCollapsed, setSidebarOpen } =
    useUIStore();
  const { user, logout } = useAuth();

  const handleNavClick = () => {
    // Close mobile drawer on navigation
    setSidebarOpen(false);
  };

  return (
    <div className="flex h-full flex-col">
      {/* ── Logo + Collapse Button ─────────────────────────────────────── */}
      <div
        className={cn(
          'flex h-16 items-center border-b px-4',
          sidebarCollapsed ? 'justify-center' : 'justify-between',
        )}
      >
        {!sidebarCollapsed && (
          <span className="text-lg font-bold tracking-tight">
            FlowPilot <span className="text-primary">AI</span>
          </span>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebarCollapsed}
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="hidden md:flex"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* ── Navigation Links ──────────────────────────────────────────── */}
      <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Main navigation">
        {NAV_ITEMS.map((item) => (
          <NavItem
            key={item.href}
            href={item.href}
            label={item.label}
            icon={item.icon}
            collapsed={sidebarCollapsed}
            onClick={handleNavClick}
          />
        ))}
      </nav>

      <Separator />

      {/* ── User Profile + Logout ─────────────────────────────────────── */}
      <div className={cn('p-3 space-y-2', sidebarCollapsed && 'flex flex-col items-center')}>
        {user && !sidebarCollapsed && (
          <div className="flex items-center gap-3 rounded-lg px-3 py-2 bg-muted/30">
            <Avatar className="h-8 w-8 flex-shrink-0">
              <AvatarFallback className="text-xs">
                {getInitials(user.full_name)}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{user.full_name}</p>
              <p className="truncate text-xs text-muted-foreground">{user.email}</p>
            </div>
          </div>
        )}
        <Button
          variant="ghost"
          size={sidebarCollapsed ? 'icon' : 'sm'}
          className={cn(
            'text-muted-foreground hover:text-destructive w-full rounded-md',
            !sidebarCollapsed && 'justify-start gap-3 px-3',
          )}
          onClick={logout}
          aria-label="Sign out"
        >
          <LogOut className="h-4 w-4 flex-shrink-0" />
          {!sidebarCollapsed && <span>Sign out</span>}
        </Button>
      </div>
    </div>
  );
}
