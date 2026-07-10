'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useAuth } from '@/hooks/useAuth';
import { useHydrated } from '@/hooks/useHydrated';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Layers,
  ArrowRight,
  Cpu,
  Workflow,
  Sparkles,
} from 'lucide-react';
import { motion } from 'framer-motion';

export default function LandingPage() {
  const { isAuthenticated } = useAuth();
  const hydrated = useHydrated();

  return (
    <div className="min-h-screen flex flex-col bg-[#001e2b] text-white overflow-x-hidden selection:bg-[#00ed64] selection:text-[#001e2b]">
      {/* ── Navbar ──────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-[#001e2b]/80 border-b border-[#003d4f]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-[#00ed64] flex items-center justify-center text-[#001e2b] font-bold text-lg shadow-md shadow-[#00ed64]/10">
              F
            </div>
            <span className="text-xl font-bold tracking-tight text-white">
              FlowPilot <span className="text-[#00ed64]">AI</span>
            </span>
          </div>

          <nav className="flex items-center gap-4">
            {hydrated && isAuthenticated ? (
              <Button asChild size="sm">
                <Link href={'/dashboard' as Route}>Dashboard</Link>
              </Button>
            ) : (
              <>
                <Button asChild variant="ghost" size="sm" className="text-white hover:text-[#00ed64] hover:bg-[#003d4f]">
                  <Link href={'/login' as Route}>Sign in</Link>
                </Button>
                <Button asChild size="sm" className="bg-[#00ed64] text-[#001e2b] hover:bg-[#00b545]">
                  <Link href={'/register' as Route}>Register</Link>
                </Button>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* ── Hero Section ────────────────────────────────────────────────── */}
      <section className="relative flex-1 flex flex-col justify-center items-center py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto text-center z-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(0,237,100,0.08),transparent_40%)] pointer-events-none" />

        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="space-y-6 max-w-3xl"
        >
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#003d4f] border border-[#00684a] text-xs font-semibold text-[#00ed64]">
            <Sparkles className="h-3.5 w-3.5" /> Introducing FlowPilot Orchestrator v1.0
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
            AI-Powered <br />
            <span className="bg-gradient-to-r from-[#00ed64] via-[#00a35c] to-teal-400 bg-clip-text text-transparent">
              Inbox Orchestration
            </span>
          </h1>

          <p className="text-lg sm:text-xl text-gray-300 max-w-2xl mx-auto leading-relaxed">
            Automatically classify documents, extract intelligence, and route workflows to specialized AI agents in real-time.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-4">
            {hydrated && isAuthenticated ? (
              <Button asChild size="lg" className="w-full sm:w-auto text-base">
                <Link href={'/dashboard' as Route} className="inline-flex items-center gap-2">
                  Go to Dashboard <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            ) : (
              <>
                <Button asChild size="lg" className="w-full sm:w-auto text-base bg-[#00ed64] text-[#001e2b] hover:bg-[#00b545] shadow-lg shadow-[#00ed64]/10">
                  <Link href={'/register' as Route} className="inline-flex items-center gap-2">
                    Start Automating <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
                <Button asChild variant="outline" size="lg" className="w-full sm:w-auto text-base border-[#00684a] text-white hover:bg-[#003d4f]/50">
                  <Link href={'/login' as Route}>Sign In</Link>
                </Button>
              </>
            )}
          </div>
        </motion.div>
      </section>

      {/* ── Features Grid ───────────────────────────────────────────────── */}
      <section className="bg-[#00141d] py-20 px-4 sm:px-6 lg:px-8 border-t border-[#003d4f]/50">
        <div className="max-w-7xl mx-auto space-y-12">
          <div className="text-center space-y-3">
            <h2 className="text-3xl font-bold tracking-tight">Built for Next-Gen Operations</h2>
            <p className="text-gray-400 max-w-lg mx-auto">
              Automate complex email inboxes and document routing pipelines out of the box.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            <Card className="bg-[#001e2b] border-[#003d4f] text-white rounded-xl">
              <CardContent className="p-6 space-y-4">
                <div className="h-10 w-10 rounded-lg bg-[#00ed64]/10 flex items-center justify-center text-[#00ed64]">
                  <Cpu className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-bold">Intent Classification</h3>
                <p className="text-gray-400 text-sm leading-relaxed">
                  Real-time natural language processing identifies incoming intentions (e.g. billing issues, sales requests) instantly.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-[#001e2b] border-[#003d4f] text-white rounded-xl">
              <CardContent className="p-6 space-y-4">
                <div className="h-10 w-10 rounded-lg bg-teal-400/10 flex items-center justify-center text-teal-400">
                  <Layers className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-bold">Document Intelligence</h3>
                <p className="text-gray-400 text-sm leading-relaxed">
                  Extracts structured metadata, dates, and currency totals from attachments and PDFs using integrated OCR pipelines.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-[#001e2b] border-[#003d4f] text-white rounded-xl">
              <CardContent className="p-6 space-y-4">
                <div className="h-10 w-10 rounded-lg bg-purple-400/10 flex items-center justify-center text-purple-400">
                  <Workflow className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-bold">LangGraph Orchestration</h3>
                <p className="text-gray-400 text-sm leading-relaxed">
                  Routes assignments dynamic to Sales, Support, Finance, or Executive agents based on intent confidence scores.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="bg-[#001e2b] border-t border-[#003d4f] py-8 text-center text-xs text-gray-500">
        <p>&copy; 2026 FlowPilot AI. All rights reserved. Designed with MongoDB Theme Aesthetics.</p>
      </footer>
    </div>
  );
}
