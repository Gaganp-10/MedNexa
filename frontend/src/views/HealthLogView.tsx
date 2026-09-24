import React, { useState, useEffect } from 'react'
import { apiFetch } from '@/api/client'
import { useAuth } from '@/context/AuthContext'
import { DailyReportForm } from '@/components/patient/DailyReportForm'
import { ClinicalDisclaimer } from '@/components/common/ClinicalDisclaimer'
import { ClipboardList, Activity, RefreshCw, Loader2 } from 'lucide-react'
import type { DailyHealthLog } from '@/types/api'

export const HealthLogView: React.FC = () => {
  const { user } = useAuth()
  const [logs, setLogs] = useState<DailyHealthLog[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const isDoctor = user?.role === 'doctor'

  const fetchLogs = async () => {
    setLoading(true)
    try {
      if (user?.role === 'patient') {
        // GET /api/health/logs/
        const data = await apiFetch<DailyHealthLog[]>('/health/logs/')
        setLogs(data || [])
      } else if (user?.role === 'doctor') {
        // If doctor, load logs for their first patient or overall
        const overview = await apiFetch<any>('/doctor/overview/')
        if (overview.patients && overview.patients.length > 0) {
          const pid = overview.patients[0].patient_id
          const pLogs = await apiFetch<DailyHealthLog[]>(`/patient/${pid}/logs/`)
          setLogs(pLogs || [])
        }
      }
    } catch {
      setLogs([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [user])

  return (
    <div className="space-y-6">
      <ClinicalDisclaimer />

      <div className="flex items-center justify-between pb-2 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-teal-500/15 border border-teal-500/30 flex items-center justify-center text-teal-400">
            <ClipboardList className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              {isDoctor ? 'Patient Health Logs' : 'Daily Health Logs'}
            </h1>
            <p className="text-xs text-slate-400">
              Vitals, pain tracking, and recovery score entries
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={fetchLogs}
          className="p-2 rounded-xl bg-slate-900 border border-white/10 hover:border-white/20 text-slate-300"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {!isDoctor && (
          <div className="lg:col-span-5">
            <DailyReportForm
              onLogSubmitted={(newLog) => setLogs((prev) => [newLog, ...prev])}
            />
          </div>
        )}

        <div className={!isDoctor ? 'lg:col-span-7' : 'lg:col-span-12'}>
          <div className="glass-card rounded-2xl p-5 border border-white/5 space-y-3">
            <div className="flex items-center justify-between pb-3 border-b border-white/5">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-teal-400" />
                <h3 className="text-sm font-semibold text-white">Log History</h3>
              </div>
              <span className="text-xs text-slate-400 font-mono">
                {logs.length} record{logs.length === 1 ? '' : 's'}
              </span>
            </div>

            {loading ? (
              <div className="flex flex-col items-center justify-center py-12 text-slate-400 text-xs gap-2">
                <Loader2 className="h-6 w-6 animate-spin text-teal-400" />
                <span>Loading health logs...</span>
              </div>
            ) : logs.length === 0 ? (
              <div className="text-center py-12 text-xs text-slate-500">
                <p className="font-medium text-slate-400">No data yet.</p>
                <p className="text-[11px] text-slate-600 mt-1">
                  Health logs submitted will appear here.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-400 font-mono text-[11px]">
                      <th className="py-2.5 px-3">Date</th>
                      <th className="py-2.5 px-3">Temp</th>
                      <th className="py-2.5 px-3">Pain</th>
                      <th className="py-2.5 px-3">Swelling</th>
                      <th className="py-2.5 px-3">Meds</th>
                      <th className="py-2.5 px-3">Score</th>
                      <th className="py-2.5 px-3">Notes</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {logs.map((log) => (
                      <tr key={log.id} className="hover:bg-white/5 transition-colors">
                        <td className="py-2.5 px-3 text-slate-300 font-mono text-[11px]">
                          {new Date(log.created_at).toLocaleString()}
                        </td>
                        <td className="py-2.5 px-3 font-semibold text-white">
                          {log.temperature.toFixed(1)}°C
                        </td>
                        <td className="py-2.5 px-3 font-mono font-bold text-teal-300">
                          {log.pain_level}/10
                        </td>
                        <td className="py-2.5 px-3 text-slate-300">
                          {log.swelling ? (
                            <span className="text-amber-400">Yes</span>
                          ) : (
                            <span className="text-slate-500">No</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-slate-300">
                          {log.medication_taken ? (
                            <span className="text-teal-400">Yes</span>
                          ) : (
                            <span className="text-amber-400">No</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 font-mono font-bold text-teal-300">
                          {log.recovery_score}
                        </td>
                        <td className="py-2.5 px-3 text-slate-400 max-w-xs truncate">
                          {log.notes || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
