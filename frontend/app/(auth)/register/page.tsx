'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';

export default function RegisterPage() {
  const router = useRouter();
  const { register, isLoading, error, clearError, isAuthenticated } = useAuth();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) router.replace('/dashboard');
  }, [isAuthenticated, router]);

  useEffect(() => () => clearError(), [clearError]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLocalError(null);

    if (fullName.trim().length < 2) {
      setLocalError('Full name must be at least 2 characters');
      return;
    }
    if (!email.includes('@')) {
      setLocalError('Enter a valid email address');
      return;
    }
    if (password.length < 8) {
      setLocalError('Password must be at least 8 characters');
      return;
    }

    try {
      await register(email, password, fullName);
      router.replace('/dashboard');
    } catch {
      // Error displayed from store
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
        <CardTitle className="text-2xl font-bold">Create account</CardTitle>
        <CardDescription>
          Start automating your workflows with FlowPilot AI
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
            <Label htmlFor="fullName">Full name</Label>
            <Input
              id="fullName"
              type="text"
              placeholder="Alice Smith"
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              disabled={isLoading}
              required
            />
          </div>

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
              placeholder="Min. 8 characters"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
              required
            />
          </div>

          <Button type="submit" className="w-full mt-2" disabled={isLoading}>
            {isLoading ? 'Creating account…' : 'Create account'}
          </Button>

          <p className="text-center text-sm text-muted-foreground mt-4">
            Already have an account?{' '}
            <Link href="/login" className="text-[#00684a] font-semibold hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </CardContent>
    </Card>
  );
}
