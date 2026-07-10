'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { Route } from 'next';
import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface NavItemProps {
  href: string;
  label: string;
  icon: LucideIcon;
  collapsed?: boolean;
  onClick?: () => void;
}

export function NavItem({
  href,
  label,
  icon: Icon,
  collapsed = false,
  onClick,
}: NavItemProps) {
  const pathname = usePathname();
  const isActive =
    href === '/dashboard'
      ? pathname === '/dashboard'
      : pathname.startsWith(href);

  const linkContent = (
    <Link
      href={href as Route}
      onClick={onClick}
      className={cn(
        'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
        'hover:bg-accent hover:text-accent-foreground',
        isActive
          ? 'bg-primary/10 text-primary'
          : 'text-muted-foreground',
        collapsed && 'justify-center px-2',
      )}
      aria-current={isActive ? 'page' : undefined}
    >
      <Icon className="h-5 w-5 flex-shrink-0" />
      {!collapsed && <span>{label}</span>}
    </Link>
  );

  if (collapsed) {
    return (
      <TooltipProvider delayDuration={100}>
        <Tooltip>
          <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
          <TooltipContent side="right">
            <p>{label}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return linkContent;
}
