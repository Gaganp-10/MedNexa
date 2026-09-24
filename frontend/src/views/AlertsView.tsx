import React, { useState, useEffect } from 'react'
import { apiFetch } from '@/api/client'
import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/context/ToastContext'
import { AlertsListView } from '@/components/common/AlertsListView'
import { ClinicalDisclaimer } from '@/components/common/ClinicalDisclaimer'
import { AlertTriangle, RefreshCw, Loader2 } from 'lucide-react'
import type { AlertItem } from '@/types/api'

export const AlertsView: React.FC = () => {
  const { user } = useAuth()
  const { toast } = useToast()
  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const [loading, setLoading] = useState(true)

  const isDoctor = user?.role === 'doctor'
  const pid = user?.patient_profile_id

  const fetchAlerts = async () => {
    setLoading(true)
    try {
      if (!isDoctor && pid) {
        // GET /api/patient/<patient_id>/alerts/
        const data = await apiFetch<AlertItem[]>(`/patient/${pid}/alerts/`)
        setAlerts(data || [])
      } else if (isDoctor) {
        // Load first patient or from overview
        const overview = await apiFetch<any>('/doctor/overview/').catch(() => null)
        if (overview?.patients?.[0]) {
          const firstPid = overview.patients[0].patient_id
          const data = await apiFetch<AlertItem[]>(`/patient/${firstPid}/alerts/`)
          setAlerts(data || [])
        }
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAlerts()
  }, [user])

  const handleMarkAlertRead = async (alertId: number) => {
    try {
      await apiFetch<AlertItem>(`/alerts/${alertId}/read/`, {
        method: 'PATCH',
        body: JSON.stringify({ is_read: true }),
      })
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, is_read: true } : a))
      )
      toast({
        title: 'Alert Reviewed',
        description: 'Alert status updated to read.',
        variant: 'success',
      })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update alert.'
      toast({
        title: 'Action Error',
        description: msg,
        variant: 'danger',
      })
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <ClinicalDisclaimer />

      <div className="flex items-center justify-between pb-2 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Clinical Alerts Feed</h1>
            <p className="text-xs text-slate-400">
              Automated threshold notifications and missed-dose alerts requiring medical triage
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={fetchAlerts}
          className="p-2 rounded-xl bg-slate-900 border border-white/10 hover:border-white/20 text-slate-300"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      <div className="glass-card rounded-2xl p-5 border border-white/5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-white/5">
          <h3 className="text-sm font-semibold text-white">Active System Alerts</h3>
          <span className="text-xs font-mono text-slate-400">
            {alerts.length} record{alerts.length === 1 ? '' : 's'}
          </span>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-400 text-xs gap-2">
            <Loader2 className="h-6 w-6 animate-spin text-teal-400" />
            <span>Loading clinical alerts...</span>
          </div>
        ) : (
          <AlertsListView
            alerts={alerts}
            isDoctor={isDoctor}
            onMarkRead={handleMarkAlertRead}
          />
        )}
      </div>
    </div>
  )
}
