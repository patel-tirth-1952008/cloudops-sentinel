import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'CloudOps Sentinel - Real-Time Infrastructure Health & Incident Monitor',
  description: 'Production-grade microservices health monitor and automated incident alerting engine with latency anomaly detection, uptime SLAs, and webhook notifications.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen antialiased">
        <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/30">
                ⚡
              </div>
              <span className="font-semibold text-lg tracking-tight text-white">cloudops-sentinel</span>
            </div>
            <div className="flex items-center space-x-4 text-xs">
              <span className="px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                System Live
              </span>
              <span className="text-slate-400 hidden sm:inline">v1.0.0</span>
            </div>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
      </body>
    </html>
  )
}
