import React from 'react'
import { useAuth } from '@/context/AuthContext'
import { useWebSocket } from '@/context/WebSocketContext'
import { API_BASE_URL, WS_BASE_URL, CLINICAL_SAFETY_DISCLAIMER } from '@/config/env'
import { ClinicalDisclaimer } from '@/components/common/ClinicalDisclaimer'
import { Settings, Shield, Server, User, Wifi, LogOut } from 'lucide-react'

export const SettingsView: React.FC = () => {
  const { user, logout } = useAuth()
  const { isConnected } = useWebSocket()

  return (
    <div className="space-y-6 max-w-4xl">
      <ClinicalDisclaimer />

      <div className="flex items-center gap-3 pb-2 border-b border-white/5">
        <div className="h-9 w-9 rounded-xl bg-teal-500/15 border border-teal-500/30 flex items-center justify-center text-teal-400">
          <Settings className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">System & Client Settings</h1>
          <p className="text-xs text-slate-400">Environment configuration and active session profile</p>
        </div>
      </div>

      {/* Account Info */}
      <div className="glass-card rounded-2xl p-5 border border-white/5 space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-white/5">
          <User className="h-4 w-4 text-teal-400" />
          <h3 className="text-sm font-semibold text-white">Active Session Profile</h3>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
            <span className="text-[11px] text-slate-400 block">Username</span>
            <span className="font-semibold text-white mt-0.5 block">{user?.username}</span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
            <span className="text-[11px] text-slate-400 block">Clinical Role</span>
            <span className="font-mono text-teal-300 uppercase mt-0.5 block">{user?.role}</span>
          </div>

          {user?.patient_profile_id && (
            <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
              <span className="text-[11px] text-slate-400 block">Patient Profile Record ID</span>
              <span className="font-mono text-white mt-0.5 block">#{user.patient_profile_id}</span>
            </div>
          )}

          {user?.doctor_profile_id && (
            <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
              <span className="text-[11px] text-slate-400 block">Doctor Profile Record ID</span>
              <span className="font-mono text-white mt-0.5 block">#{user.doctor_profile_id}</span>
            </div>
          )}
        </div>

        <div className="pt-2">
          <button
            type="button"
            onClick={logout}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500/15 hover:bg-red-500/25 border border-red-500/30 text-red-300 text-xs font-semibold transition-colors"
          >
            <LogOut className="h-4 w-4" />
            <span>Terminate Active Session</span>
          </button>
        </div>
      </div>

      {/* Backend Endpoint Topology */}
      <div className="glass-card rounded-2xl p-5 border border-white/5 space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-white/5">
          <Server className="h-4 w-4 text-teal-400" />
          <h3 className="text-sm font-semibold text-white">Central Configuration & Topology</h3>
        </div>

        <div className="space-y-3 text-xs">
          <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between">
            <div>
              <span className="text-[11px] text-slate-400 block">REST API Base Endpoint</span>
              <span className="font-mono text-slate-200 mt-0.5 block">{API_BASE_URL}</span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-teal-500/20 text-teal-300">
              VITE_API_BASE_URL
            </span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between">
            <div>
              <span className="text-[11px] text-slate-400 block">WebSocket Host URL</span>
              <span className="font-mono text-slate-200 mt-0.5 block">{WS_BASE_URL}</span>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded ${
                  isConnected ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-800 text-slate-400'
                }`}
              >
                <Wifi className="h-3 w-3" />
                {isConnected ? 'Online' : 'Offline'}
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-teal-500/20 text-teal-300">
                VITE_WS_BASE_URL
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Regulatory & Safety Prototype Notice */}
      <div className="glass-card rounded-2xl p-5 border border-white/5 space-y-2">
        <div className="flex items-center gap-2 text-amber-400 text-xs font-semibold">
          <Shield className="h-4 w-4" />
          <span>Decision-Support Prototype Specification</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          {CLINICAL_SAFETY_DISCLAIMER}
        </p>
        <p className="text-[11px] text-slate-500 leading-relaxed">
          Outputs generated by this platform, including risk predictions, OpenCV wound site analysis heuristics, and vital alerts, are strictly prototype decision-support notifications intended solely for triage and clinician review.
        </p>
      </div>
    </div>
  )
}
