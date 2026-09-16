'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type ServiceStatus = 'healthy' | 'degraded' | 'down' | 'unknown';
type Severity = 'critical' | 'warning' | 'info';
type IncidentStatus = 'active' | 'resolved';
type MetricKey = 'latency' | 'errorRate' | 'cpu';

interface Service {
  id: string;
  name: string;
  url: string;
  status: ServiceStatus;
  uptime: number;
  responseTime: number;
  latencyHistory: number[];
  checkInterval: number;
  latencyThreshold: number;
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
  value: number;
}

interface MetricsResponse {
  serviceId: string;
  latency: MetricPoint[];
  errorRate: MetricPoint[];
  cpu: MetricPoint[];
}

interface Summary {
  total: number;
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
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function normalizeStatus(raw: unknown): ServiceStatus {
  const s = String(raw ?? '').toLowerCase();
  if (s.includes('down') || s.includes('error') || s.includes('fail') || s.includes('crit')) return 'down';
  if (s.includes('degrad') || s.includes('warn') || s.includes('slow')) return 'degraded';
  if (s.includes('health') || s.includes('ok') || s.includes('up') || s.includes('pass')) return 'healthy';
  return 'unknown';
}

function normalizeSeverity(raw: unknown): Severity {
  const s = String(raw ?? '').toLowerCase();
  if (s.includes('crit')) return 'critical';
  if (s.includes('warn')) return 'warning';
  return 'info';
}

function normalizeIncidentStatus(raw: unknown): IncidentStatus {
  const s = String(raw ?? '').toLowerCase();
  if (s.includes('resolv') || s.includes('closed') || s.includes('ack')) return 'resolved';
  return 'active';
}

function toNumber(v: unknown, fallback = 0): number {
  const n = typeof v === 'number' ? v : parseFloat(String(v));
  return Number.isFinite(n) ? n : fallback;
}

function toHistory(v: unknown): number[] {
  if (Array.isArray(v)) return v.map((x) => toNumber(x, 0));
  return [];
}

function mapService(raw: any): Service {
  const id = String(raw?.id ?? raw?._id ?? raw?.serviceId ?? Math.random().toString(36).slice(2));
  const name = String(raw?.name ?? raw?.serviceName ?? 'Unnamed Service');
  const url = String(raw?.url ?? raw?.healthcheckUrl ?? raw?.endpoint ?? '');
  const status = normalizeStatus(raw?.status ?? raw?.state ?? raw?.health);
  const uptime = toNumber(raw?.uptime ?? raw?.uptimePercent ?? raw?.uptime_pct, 100);
  const responseTime = toNumber(raw?.responseTime ?? raw?.response_time ?? raw?.latency ?? raw?.avgLatency, 0);
  const latencyHistory = toHistory(raw?.latencyHistory ?? raw?.latency_history ?? raw?.history ?? raw?.sparkline);
  const checkInterval = toNumber(raw?.checkInterval ?? raw?.check_interval ?? raw?.interval, 30);
  const latencyThreshold = toNumber(raw?.latencyThreshold ?? raw?.latency_threshold ?? raw?.threshold, 500);
  return { id, name, url, status, uptime, responseTime, latencyHistory, checkInterval, latencyThreshold };
}

function mapIncident(raw: any): Incident {
  const id = String(raw?.id ?? raw?._id ?? raw?.incidentId ?? Math.random().toString(36).slice(2));
  const serviceId = String(raw?.serviceId ?? raw?.service_id ?? '');
  const serviceName = String(raw?.serviceName ?? raw?.service_name ?? raw?.service ?? 'Unknown Service');
  const severity = normalizeSeverity(raw?.severity ?? raw?.level);
  const status = normalizeIncidentStatus(raw?.status ?? raw?.state);
  const title = String(raw?.title ?? raw?.name ?? raw?.summary ?? 'Incident');
  const description = String(raw?.description ?? raw?.message ?? raw?.details ?? '');
  const createdAt = String(raw?.createdAt ?? raw?.created_at ?? raw?.timestamp ?? new Date().toISOString());
  const resolvedAt = raw?.resolvedAt ?? raw?.resolved_at ?? null;
  return { id, serviceId, serviceName, severity, status, title, description, createdAt, resolvedAt: resolvedAt ? String(resolvedAt) : null };
}

function mapMetrics(raw: any): MetricsResponse {
  const pick = (arr: unknown): MetricPoint[] =>
    Array.isArray(arr)
      ? arr.map((p: any) => ({
          timestamp: String(p?.timestamp ?? p?.time ?? p?.t ?? ''),
          value: toNumber(p?.value ?? p?.v ?? p, 0),
        }))
      : [];
  return {
    serviceId: String(raw?.serviceId ?? raw?.service_id ?? ''),
    latency: pick(raw?.latency ?? raw?.latencySeries ?? raw?.latency_series),
    errorRate: pick(raw?.errorRate ?? raw?.error_rate ?? raw?.errors),
    cpu: pick(raw?.cpu ?? raw?.cpuUsage ?? raw?.cpu_usage),
  };
}

function extractArray(data: any): any[] {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.services)) return data.services;
  if (Array.isArray(data?.incidents)) return data.incidents;
  if (Array.isArray(data?.data)) return data.data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '—';
  const diff = Date.now() - then;
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

function fmtClock(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function fmtNum(n: number, digits = 0): string {
  return n.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function statusMeta(status: ServiceStatus) {
  switch (status) {
    case 'healthy':
      return { label: 'Healthy', dot: 'bg-emerald-400', text: 'text-emerald-300', ring: 'ring-emerald-500/30', glow: 'shadow-[0_0_12px_rgba(52,211,153,0.5)]' };
    case 'degraded':
      return { label: 'Degraded', dot: 'bg-amber-400', text: 'text-amber-300