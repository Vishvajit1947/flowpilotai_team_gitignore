'use client';

import { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

import type { Route } from 'next';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isLoading, error, clearError, isAuthenticated } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  const returnTo = searchParams.get('returnTo') ?? '/dashboard';

  useEffect(() => {
    if (isAuthenticated) {
      router.replace(returnTo as Route);
    }
  }, [isAuthenticated, router, returnTo]);

  useEffect(() => {
    return () => clearError();
  }, [clearError]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLocalError(null);

    if (!email.trim()) {
      setLocalError('Email is required');
      return;
    }
    if (!password) {
      setLocalError('Password is required');
      return;
    }

    try {
      await login(email, password);
      router.replace(returnTo as Route);
    } catch {
      // Error is set in store — displayed via `error`
    }
  }

  const displayError = localError ?? error;

  return (
    <Card className="border border-border/80 shadow-md">
      <CardHeader className="space-y-1.5 pb-6">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xl font-bold tracking-tight text-foreground">
            FlowPilot <span className="text-primary">AI</span>
          </span>
        </div>
        <CardTitle className="text-2xl font-bold">Sign in</CardTitle>
        <CardDescription>
          Enter your credentials to access your orchestration dashboard
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {displayError && (
            <div
              role="alert"
              className="rounded-md bg-destructive/10 px-4 py-3 text-sm font-medium text-destructive border border-destructive/20"
            >
              {displayError}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              required
            />
          </div>

          <Button type="submit" className="w-full mt-2" disabled={isLoading}>
            {isLoading ? 'Signing in…' : 'Sign in'}
          </Button>

          <p className="text-center text-sm text-muted-foreground mt-4">
            Don&apos;t have an account?{' '}
            <Link
              href="/register"
              className="text-[#00684a] font-semibold hover:underline"
            >
              Sign up
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center p-8">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    }>
      <LoginForm />
    </Suspense>
  );
}
