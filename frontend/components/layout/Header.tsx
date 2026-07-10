'use client';

import { Menu, Bell, LogOut, User } from 'lucide-react';
import { useUIStore } from '@/store/ui';
import { useAuth } from '@/hooks/useAuth';
import { PageTitle } from './PageTitle';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

export function Header() {
  const { toggleSidebar } = useUIStore();
  const { user, logout } = useAuth();

  return (
    <header className="flex h-16 items-center gap-4 border-b bg-card px-4 md:px-6">
      {/* ── Hamburger (mobile only) ──────────────────────────────────── */}
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={toggleSidebar}
        aria-label="Open navigation menu"
      >
        <Menu className="h-5 w-5" />
      </Button>

      {/* ── Page Title ──────────────────────────────────────────────── */}
      <div className="flex-1">
        <PageTitle />
      </div>

      {/* ── Actions ─────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        {/* Theme Toggle */}
        <ThemeToggle />

        {/* Notification Bell */}
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Notifications (coming soon)"
                className="rounded-md"
              >
                <Bell className="h-5 w-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Notifications coming soon</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {/* User Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="rounded-full"
              aria-label="User menu"
            >
              <Avatar className="h-8 w-8">
                <AvatarFallback className="text-xs bg-primary text-primary-foreground">
                  {user ? getInitials(user.full_name) : 'U'}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end" className="w-56 bg-card border border-border">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">
                  {user?.full_name}
                </p>
                <p className="text-xs leading-none text-muted-foreground">
                  {user?.email}
                </p>
              </div>
            </DropdownMenuLabel>

            <DropdownMenuSeparator />

            <DropdownMenuItem disabled className="gap-2 rounded-md">
              <User className="h-4 w-4" />
              <span>Profile settings</span>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <DropdownMenuItem
              onClick={logout}
              className="gap-2 text-destructive focus:text-destructive rounded-md"
            >
              <LogOut className="h-4 w-4" />
              <span>Sign out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
