'use client';

import { useState, useRef } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useAuth } from '@/hooks/useAuth';
import { useHydrated } from '@/hooks/useHydrated';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Layers,
  ArrowRight,
  Cpu,
  Workflow,
  Sparkles,
  CheckCircle2,
  FileText,
  DollarSign,
  UserCheck,
  Zap,
  TrendingUp,
} from 'lucide-react';
import { motion, useScroll, useTransform } from 'framer-motion';

export default function LandingPage() {
  const { isAuthenticated } = useAuth();
  const hydrated = useHydrated();

  // Scroll Parallax refs and values
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end end'],
  });

  // Transform speeds for background parallax orbs
  const orbY1 = useTransform(scrollYProgress, [0, 1], [0, -150]);
  const orbY2 = useTransform(scrollYProgress, [0, 1], [0, 150]);
  const orbY3 = useTransform(scrollYProgress, [0, 1], [0, -80]);

  // 3D Card Tilt state for Hero
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const cardRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const mouseX = e.clientX - rect.left - width / 2;
    const mouseY = e.clientY - rect.top - height / 2;
    const rX = (mouseY / height) * 15; // Max 15 degree rotation
    const rY = -(mouseX / width) * 15;
    setTilt({ x: rX, y: rY });
  };

  const handleMouseLeave = () => {
    setTilt({ x: 0, y: 0 });
  };

  return (
    <div
      ref={containerRef}
      className="min-h-screen flex flex-col bg-white text-[#001e2b] overflow-x-hidden selection:bg-[#00ed64] selection:text-[#001e2b]"
    >
      {/* ── Background Grid & Parallax Orbs ────────────────────────────── */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#e1e5e8_1px,transparent_1px),linear-gradient(to_bottom,#e1e5e8_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-60 pointer-events-none" />

      {/* Floating Parallax Orbs (soft pastel glows for light theme) */}
      <motion.div
        style={{ y: orbY1 }}
        className="absolute top-[20%] left-[-10%] w-[35rem] h-[35rem] rounded-full bg-gradient-to-tr from-[#00ed64]/10 to-transparent blur-[120px] pointer-events-none"
      />
      <motion.div
        style={{ y: orbY2 }}
        className="absolute top-[50%] right-[-10%] w-[40rem] h-[40rem] rounded-full bg-gradient-to-br from-[#c3f0d2]/30 to-transparent blur-[150px] pointer-events-none"
      />
      <motion.div
        style={{ y: orbY3 }}
        className="absolute bottom-[10%] left-[15%] w-[30rem] h-[30rem] rounded-full bg-gradient-to-tr from-purple-500/5 to-transparent blur-[130px] pointer-events-none"
      />

      {/* ── Navbar ──────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-white/80 border-b border-[#e1e5e8]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-[#00ed64] flex items-center justify-center text-[#001e2b] font-bold text-lg shadow-md shadow-[#00ed64]/10">
              F
            </div>
            <span className="text-xl font-bold tracking-tight text-[#001e2b]">
              FlowPilot <span className="text-[#00684a]">AI</span>
            </span>
          </div>

          <nav className="flex items-center gap-4">
            {hydrated && isAuthenticated ? (
              <Button asChild size="sm">
                <Link href={'/dashboard' as Route}>Dashboard</Link>
              </Button>
            ) : (
              <>
                <Button
                  asChild
                  variant="ghost"
                  size="sm"
                  className="text-[#001e2b] hover:text-[#00684a] hover:bg-[#f9fbfa]"
                >
                  <Link href={'/login' as Route}>Sign in</Link>
                </Button>
                <Button
                  asChild
                  size="sm"
                  className="bg-[#00ed64] text-[#001e2b] hover:bg-[#00b545]"
                >
                  <Link href={'/register' as Route}>Register</Link>
                </Button>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* ── Hero Section with 3D Mouse Parallax ────────────────────────── */}
      <section className="relative flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 md:py-24 grid md:grid-cols-2 gap-12 items-center z-10">
        <div className="space-y-6 text-left">
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#f9fbfa] border border-[#e1e5e8] text-xs font-semibold text-[#00684a] backdrop-blur shadow-sm">
            <Sparkles className="h-3.5 w-3.5 text-[#00ed64]" /> Introducing FlowPilot Orchestrator v1.0
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-[#001e2b] leading-tight">
            AI-Powered <br />
            <span className="bg-gradient-to-r from-[#00684a] via-[#00a35c] to-emerald-600 bg-clip-text text-transparent">
              Inbox Orchestration
            </span>
          </h1>

          <p className="text-base sm:text-lg text-gray-600 max-w-lg leading-relaxed">
            Automatically classify documents, extract intelligence, and route workflows to specialized AI agents—all in one secure, integrated workspace.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 pt-4">
            {hydrated && isAuthenticated ? (
              <Button asChild size="lg" className="text-base px-8">
                <Link
                  href={'/dashboard' as Route}
                  className="inline-flex items-center gap-2"
                >
                  Go to Dashboard <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
            ) : (
              <>
                <Button
                  asChild
                  size="lg"
                  className="text-base px-8 bg-[#00ed64] text-[#001e2b] hover:bg-[#00b545] shadow-lg shadow-[#00ed64]/10"
                >
                  <Link
                    href={'/register' as Route}
                    className="inline-flex items-center gap-2"
                  >
                    Start Automating <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
                <Button
                  asChild
                  variant="outline"
                  size="lg"
                  className="text-base px-8 border-[#c1ccd6] text-[#001e2b] hover:bg-[#f9fbfa]"
                >
                  <Link href={'/login' as Route}>Sign In</Link>
                </Button>
              </>
            )}
          </div>
        </div>

        {/* ── Interactive 3D Mockup Card ──────────────────────────────── */}
        <div
          className="flex justify-center items-center cursor-default perspective-1000"
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
        >
          <motion.div
            ref={cardRef}
            style={{
              rotateX: tilt.x,
              rotateY: tilt.y,
              transformStyle: 'preserve-3d',
            }}
            transition={{ type: 'spring', stiffness: 200, damping: 25 }}
            className="w-full max-w-[450px] bg-white border border-[#e1e5e8] rounded-2xl shadow-xl p-6 space-y-6 relative overflow-hidden"
          >
            {/* Card internal glowing mesh */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-[#00ed64]/10 to-transparent rounded-full pointer-events-none" />

            <div className="flex items-center justify-between border-b border-[#e1e5e8] pb-4">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-red-400" />
                <div className="h-3 w-3 rounded-full bg-yellow-400" />
                <div className="h-3 w-3 rounded-full bg-green-400" />
              </div>
              <Badge variant="secondary" className="bg-[#f9fbfa] text-[#00684a] border border-[#e1e5e8] text-[10px]">
                Pipeline Active
              </Badge>
            </div>

            {/* Simulated live parsing steps */}
            <div className="space-y-4">
              <div className="p-3 bg-[#f9fbfa] rounded-lg border border-[#e1e5e8] space-y-1.5">
                <div className="flex justify-between items-center text-[11px] text-gray-400">
                  <span>INPUT CHANNEL</span>
                  <span>10:24 AM</span>
                </div>
                <div className="text-xs font-semibold truncate text-[#001e2b]">
                  Email: &quot;Urgent inquiry regarding Invoice #2026-F&quot;
                </div>
              </div>

              {/* Progress step visual indicators */}
              <div className="space-y-3 relative pl-4 border-l border-[#e1e5e8]">
                <div className="relative">
                  <div className="absolute -left-[21px] top-0.5 h-3 w-3 rounded-full bg-[#00ed64] border-2 border-white flex items-center justify-center shadow shadow-[#00ed64]/30" />
                  <div className="text-xs font-bold text-[#00684a] flex items-center gap-1.5">
                    Intent Classification <Zap className="h-3 w-3 text-[#00ed64] animate-pulse" />
                  </div>
                  <p className="text-[11px] text-gray-500 mt-0.5">
                    Detected: <span className="text-[#001e2b] font-semibold">Billing/Finance</span> (98% confidence)
                  </p>
                </div>

                <div className="relative">
                  <div className="absolute -left-[21px] top-0.5 h-3 w-3 rounded-full bg-[#00ed64] border-2 border-white flex items-center justify-center shadow shadow-[#00ed64]/30" />
                  <div className="text-xs font-bold text-[#001e2b] flex items-center gap-1.5">
                    Optical Character Recognition
                  </div>
                  <p className="text-[11px] text-gray-500 mt-0.5">
                    Extracted metadata: <span className="text-[#001e2b] font-semibold">$1,248.50 USD</span>
                  </p>
                </div>

                <div className="relative">
                  <div className="absolute -left-[21px] top-0.5 h-3 w-3 rounded-full bg-[#00ed64] border-2 border-white flex items-center justify-center shadow shadow-[#00ed64]/30" />
                  <div className="text-xs font-bold text-[#001e2b]">
                    Agent Routing
                  </div>
                  <p className="text-[11px] text-gray-500 mt-0.5">
                    Routed to: <span className="text-[#00684a] font-semibold">Finance AI Agent</span>
                  </p>
                </div>
              </div>
            </div>

            {/* Mini Graph card snippet */}
            <div className="bg-[#f9fbfa] rounded-lg border border-[#e1e5e8] p-3 flex justify-between items-center">
              <div>
                <span className="text-[10px] text-gray-400 uppercase tracking-wider block">Average SLA Response</span>
                <span className="text-sm font-bold text-[#001e2b]">12.4 seconds</span>
              </div>
              <div className="flex gap-0.5 items-end h-8">
                <div className="w-1.5 bg-[#00ed64]/10 rounded-t h-4" />
                <div className="w-1.5 bg-[#00ed64]/30 rounded-t h-6" />
                <div className="w-1.5 bg-[#00ed64]/60 rounded-t h-5" />
                <div className="w-1.5 bg-[#00ed64] rounded-t h-8" />
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── Core Pipeline Flow Demonstration (Visual Cards) ──────────────── */}
      <section className="bg-[#f9fbfa] py-24 px-4 sm:px-6 lg:px-8 border-t border-[#e1e5e8] relative">
        <div className="max-w-7xl mx-auto space-y-16">
          <div className="text-center space-y-4">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#001e2b]">
              End-to-End Orchestration Flow
            </h2>
            <p className="text-gray-500 max-w-lg mx-auto text-sm sm:text-base">
              See how FlowPilot AI receives, classifies, OCR-processes, and handles pipeline data in seconds.
            </p>
          </div>

          <div className="grid gap-8 md:grid-cols-4">
            <Card className="bg-white border-[#e1e5e8] text-[#001e2b] rounded-xl relative group hover:border-[#00ed64]/50 transition-colors shadow-sm">
              <CardContent className="p-6 space-y-4">
                <div className="h-12 w-12 rounded-lg bg-[#00ed64]/10 flex items-center justify-center text-[#00684a]">
                  <FileText className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-lg font-bold">1. Input Ingest</h3>
                  <p className="text-gray-500 text-xs mt-2 leading-relaxed">
                    PDFs, scanned invoices, or email content are received via endpoints or triggers.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white border-[#e1e5e8] text-[#001e2b] rounded-xl relative group hover:border-[#00ed64]/50 transition-colors shadow-sm">
              <CardContent className="p-6 space-y-4">
                <div className="h-12 w-12 rounded-lg bg-[#c3f0d2]/30 flex items-center justify-center text-[#00684a]">
                  <Cpu className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-lg font-bold">2. Intent Detection</h3>
                  <p className="text-gray-500 text-xs mt-2 leading-relaxed">
                    Custom NLP intelligence reads and understands intention, determining the required workflow.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white border-[#e1e5e8] text-[#001e2b] rounded-xl relative group hover:border-[#00ed64]/50 transition-colors shadow-sm">
              <CardContent className="p-6 space-y-4">
                <div className="h-12 w-12 rounded-lg bg-purple-100 flex items-center justify-center text-purple-600">
                  <Layers className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-lg font-bold">3. OCR Parsing</h3>
                  <p className="text-gray-500 text-xs mt-2 leading-relaxed">
                    Extracts raw content and structure, identifying specific key-value fields.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white border-[#e1e5e8] text-[#001e2b] rounded-xl relative group hover:border-[#00ed64]/50 transition-colors shadow-sm">
              <CardContent className="p-6 space-y-4">
                <div className="h-12 w-12 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600">
                  <Workflow className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-lg font-bold">4. LangGraph Agent</h3>
                  <p className="text-gray-500 text-xs mt-2 leading-relaxed">
                    Dispatches the job to specialized agents to resolve, record, and output actions.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* ── Specialized AI Agents Section (Pure Code Custom Visuals) ───── */}
      <section className="bg-white py-24 px-4 sm:px-6 lg:px-8 border-t border-[#e1e5e8]">
        <div className="max-w-7xl mx-auto space-y-16">
          <div className="text-center space-y-4">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#001e2b]">
              Specialized AI Agents
            </h2>
            <p className="text-gray-500 max-w-lg mx-auto text-sm sm:text-base">
              Each pipeline triggers dedicated agents built with tailored logic and workflows.
            </p>
          </div>

          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-4">
            <div className="border border-[#e1e5e8] bg-[#f9fbfa]/85 p-6 rounded-2xl text-center space-y-4 hover:border-[#00ed64]/50 transition-colors shadow-sm">
              <div className="mx-auto h-12 w-12 rounded-full bg-[#00ed64]/15 flex items-center justify-center text-[#00684a]">
                <TrendingUp className="h-5 w-5" />
              </div>
              <div>
                <span className="text-[10px] text-[#00684a] uppercase font-bold tracking-wider">SALES AGENT</span>
                <h4 className="text-base font-bold text-[#001e2b] mt-1">Lead & Deal Capture</h4>
                <p className="text-gray-500 text-xs mt-2 leading-relaxed">
                  Identifies leads, categorizes queries, and registers deals into CRMs automatically.
                </p>
              </div>
            </div>

            <div className="border border-[#e1e5e8] bg-[#f9fbfa]/85 p-6 rounded-2xl text-center space-y-4 hover:border-[#00ed64]/50 transition-colors shadow-sm">
              <div className="mx-auto h-12 w-12 rounded-full bg-teal-100 flex items-center justify-center text-teal-700">
                <UserCheck className="h-5 w-5" />
              </div>
              <div>
                <span className="text-[10px] text-teal-600 uppercase font-bold tracking-wider">SUPPORT AGENT</span>
                <h4 className="text-base font-bold text-[#001e2b] mt-1">SLA Ticket Routing</h4>
                <p className="text-gray-500 text-xs mt-2 leading-relaxed">
                  Autofills support details, resolves simple FAQs, and flags urgent tickets.
                </p>
              </div>
            </div>

            <div className="border border-[#e1e5e8] bg-[#f9fbfa]/85 p-6 rounded-2xl text-center space-y-4 hover:border-[#00ed64]/50 transition-colors shadow-sm">
              <div className="mx-auto h-12 w-12 rounded-full bg-purple-100 flex items-center justify-center text-purple-700">
                <DollarSign className="h-5 w-5" />
              </div>
              <div>
                <span className="text-[10px] text-purple-600 uppercase font-bold tracking-wider">FINANCE AGENT</span>
                <h4 className="text-base font-bold text-[#001e2b] mt-1">Invoice Audit</h4>
                <p className="text-gray-500 text-xs mt-2 leading-relaxed">
                  Validates billing sums against ledger rules and triggers approval notifications.
                </p>
              </div>
            </div>

            <div className="border border-[#e1e5e8] bg-[#f9fbfa]/85 p-6 rounded-2xl text-center space-y-4 hover:border-[#00ed64]/50 transition-colors shadow-sm">
              <div className="mx-auto h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-700">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <div>
                <span className="text-[10px] text-blue-600 uppercase font-bold tracking-wider">EXECUTIVE AGENT</span>
                <h4 className="text-base font-bold text-[#001e2b] mt-1">High-Level Dispatch</h4>
                <p className="text-gray-500 text-xs mt-2 leading-relaxed">
                  Coordinates complex requirements, summarizes data, and escalates to key decision-makers.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="bg-[#f9fbfa] border-t border-[#e1e5e8] py-12 text-center text-xs text-gray-500">
        <div className="max-w-7xl mx-auto px-4 space-y-4">
          <div className="flex justify-center items-center gap-2">
            <div className="h-5 w-5 rounded bg-[#00ed64] flex items-center justify-center text-[#001e2b] font-bold text-xs">
              F
            </div>
            <span className="font-bold text-[#001e2b] text-sm">FlowPilot AI</span>
          </div>
          <p>&copy; 2026 FlowPilot AI. All rights reserved. Designed with MongoDB Theme Aesthetics.</p>
        </div>
      </footer>
    </div>
  );
}
