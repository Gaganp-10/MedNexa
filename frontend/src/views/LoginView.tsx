import React, { useState } from 'react'
import { HeartPulse, Lock, User, AlertCircle, Loader2 } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { ClinicalDisclaimer } from '@/components/common/ClinicalDisclaimer'

export const LoginView: React.FC = () => {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)

    if (!username.trim() || !password) {
      setErrorMessage('Please enter both username and password.')
      return
    }

    setLoading(true)
    try {
      // Calls POST /api/token/ then GET /api/auth/me/
      await login(username.trim(), password)
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message)
      } else {
        setErrorMessage('Authentication failed. Check credentials and server status.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen w-full flex flex-col justify-between items-center p-4 sm:p-6 bg-[#080d1a]">
      {/* Top safety notice */}
      <div className="w-full max-w-4xl pt-2">
        <ClinicalDisclaimer />
      </div>

      {/* Main card */}
      <div className="w-full max-w-md my-auto py-8">
        <div className="glass-card rounded-3xl p-6 sm:p-8 border border-white/10 shadow-2xl relative overflow-hidden">
          {/* Subtle top teal glow */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-1 bg-gradient-to-r from-transparent via-teal-400 to-transparent opacity-80" />

          {/* Header */}
          <div className="flex flex-col items-center text-center mb-6">
            <div className="h-14 w-14 rounded-2xl bg-teal-500/15 border border-teal-500/30 flex items-center justify-center text-teal-400 shadow-xl shadow-teal-500/10 mb-3">
              <HeartPulse className="h-8 w-8" />
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
              MEDIC Clinical Portal
            </h1>
            <p className="text-xs text-slate-400 mt-1 max-w-xs">
              Post-Surgery Remote Patient Monitoring & Clinical Decision Support
            </p>
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <div
              role="alert"
              className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-2.5 text-xs text-red-300"
            >
              <AlertCircle className="h-4 w-4 shrink-0 text-red-400 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="username-input"
                className="block text-xs font-medium text-slate-300 mb-1.5"
              >
                Username
              </label>
              <div className="relative">
                <User className="h-4 w-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  id="username-input"
                  type="text"
                  autoComplete="username"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter assigned clinical username"
                  className="w-full h-11 pl-10 pr-3 rounded-xl bg-slate-900/80 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="password-input"
                className="block text-xs font-medium text-slate-300 mb-1.5"
              >
                Password
              </label>
              <div className="relative">
                <Lock className="h-4 w-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  id="password-input"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter secure password"
                  className="w-full h-11 pl-10 pr-3 rounded-xl bg-slate-900/80 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full h-11 mt-2 rounded-xl bg-gradient-to-r from-teal-500 to-teal-600 hover:from-teal-400 hover:to-teal-500 text-slate-950 font-semibold text-xs transition-all shadow-lg shadow-teal-500/20 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Verifying Credentials...</span>
                </>
              ) : (
                <span>Access Clinical Dashboard</span>
              )}
            </button>
          </form>

          {/* Quick Help / Hint */}
          <div className="mt-6 pt-4 border-t border-white/5 text-[11px] text-slate-400 text-center">
            <p>Role-based access will automatically route to Doctor or Patient portal.</p>
          </div>
        </div>
      </div>

      {/* Footer info */}
      <footer className="w-full max-w-4xl text-center py-2 text-[11px] text-slate-500 font-mono">
        MEDIC Decision-Support Client • REST & WebSocket Protocol
      </footer>
    </div>
  )
}
