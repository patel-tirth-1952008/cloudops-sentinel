'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type ServiceStatus = 'healthy' | 'degraded' | 'down';
type Severity = 'critical' | 'warning' | 'info';
type IncidentStatus = 'active' | 'resolved';
type SeverityFilter = 'all' | Severity;
type StatusFilter = 'all' | IncidentStatus;

interface Service {
  id: string;
  name: string;
  url: string;
  status: ServiceStatus;
  uptime: number;
  responseTime: number;
  checkInterval: number;
  latencyThreshold: number;
  lastChecked: string;
  sparkline: number[];
}

interface Incident {
  id: string;
  serviceId: string;
  serviceName: string;
  severity: Severity;
  status: IncidentStatus;
  title: string;
  description: string;
  createdAt: string;
  resolvedAt: string | null;
}

interface MetricPoint {
  timestamp: string;
  latency: number;
  errorRate: number;
  cpu: number;
}

interface HealthInfo {
  status: string;
  database: string;
  uptime: string;
  version: string;
}

interface Summary {
  total: number;
  healthy: number;
  degraded: number;
  down: number;
  uptime: number;
  activeIncidents: number;
  avgP95: number;
}

interface RegisterForm {
  name: string;
  url: string;
  checkInterval: number;
  latencyThreshold: number;
}

interface FormErrors {
  name?: string;
  url?: string;
  checkInterval?: string;
  latencyThreshold?: string;
}

/* ------------------------------------------------------------------ */
/*  Constants & helpers                                                */
/* ------------------------------------------------------------------ */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const SEVERITY_META: Record<Severity, { label: string; dot: string; badge: string; ring: string }> = {
  critical: {
    label: 'Critical',
    dot: 'bg-rose-500',
    badge: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
    ring: 'ring-rose-500/40',
  },
  warning: {
    label: 'Warning',
    dot: 'bg-amber-400',
    badge: 'bg-amber-400/15 text-amber-300 border-amber-400/30',
    ring: 'ring-amber-400/40',
  },
  info: {
    label: 'Info',
    dot: 'bg-cyan-400',
    badge: 'bg-cyan-400/15 text-cyan-300 border-cyan-400/30',
    ring: 'ring-cyan-400/40',
  },
};

const STATUS_META: Record<ServiceStatus, { label: string; dot: string; text: string; ring: string; soft: string }> = {
  healthy: {
    label: 'Operational',
    dot: 'bg-emerald-400',
    text: 'text-emerald-300',
    ring: 'ring-emerald-400/40',
    soft: 'bg-emerald-400/10',
  },
  degraded: {
    label: 'Degraded',
    dot: 'bg-amber-400',
    text: 'text-amber-300',
    ring: 'ring-amber-400/40',
    soft: 'bg-amber-400/10',
  },
  down: {
    label: 'Down',
    dot: 'bg-rose-500',
    text: 'text-rose-300',
    ring: 'ring-rose-500/40',
    soft: 'bg-rose-500/10',
  },
};

function formatUptime(seconds: number): string {
  if (!isFinite(seconds) || seconds < 0) return '—';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function timeAgo(iso: string): string {
  if (!iso) return '—';
  const t = new Date(iso).getTime();
  if (isNaN(t)) return '—';
  const diff = Math.max(0, Date.now() - t);
  const s = Math.floor(diff / 1000);
  if (s < 5) return 'just now';
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function clockTime(iso: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '—';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function uptimeColor(u: number): string {
  if (u >= 99.9) return 'text-emerald-300';
  if (u >= 99) return 'text-amber-300';
  return 'text-rose-300';
}

function statusColor(status: ServiceStatus): string {
  if (status === 'healthy') return '#34d399';
  if (status === 'degraded') return '#fbbf24';
  return '#fb7185';
}

function severityColor(sev: Severity): string {
  if (sev === 'critical') return '#fb7185';
  if (sev === 'warning') return '#fbbf24';
  return '#22d3ee';
}

function latencyColor(v: number, threshold: number): string {
  if (v <= threshold * 0.7) return '#34d399';
  if (v <= threshold) return '#fbbf24';
  return '#fb7185';
}

function genSparkline(base: number, n = 26): number[] {
  const out: number[] = [];
  let v = base;
  for (let i = 0; i < n; i++) {
    v += (Math.random() - 0.5) * base * 0.45;
    v = Math.max(base * 0.35, Math.min(base * 1.9, v));
    out.push(Math.round(v));
  }
  return out;
}

function genMetrics(base: number, n = 48): MetricPoint[] {
  const now = Date.now();
  const out: MetricPoint[] = [];
  let v = base;
  for (let i = n - 1; i >= 0; i--) {
    v += (Math.random() - 0.5) * base * 0.4;
    v = Math.max(base * 0.3, Math.min(base * 2, v));
    out.push({
      timestamp: new Date(now - i * 60000).toISOString(),
      latency: Math.round(v),
      errorRate: +(Math.random() * 2.4).toFixed(2),
      cpu: Math.round(18 + Math.random() * 62),
    });
  }
  return out;
}

function genIncident(service: Service, i: number): Incident {
  const sev: Severity =
    service.status === 'down' ? '