import React from 'react'
import { AlertTriangle, Check, Clock } from 'lucide-react'
import type { AlertItem } from '@/types/api'

interface AlertsListViewProps {
  alerts: AlertItem[]
  isDoctor?: boolean
  onMarkRead?: (alertId: number) => Promise<void>
}

export const AlertsListView: React.FC<AlertsListViewProps> = ({
  alerts,
  isDoctor = false,
  onMarkRead,
}) => {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="glass-card rounded-2xl p-8 border border-white/5 text-center text-slate-400 text-xs">
        <p className="font-medium text-slate-400">No data yet.</p>
        <p className="text-[11px] text-slate-500 mt-1">
          No clinical threshold alerts have been triggered.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2.5">
      {alerts.map((alert) => {
        const isHigh = alert.severity === 'high'
        const isRead = alert.is_read

        return (
          <div
            key={alert.id}
            className={`p-4 rounded-2xl border transition-all ${
              isHigh
                ? 'bg-red-950/40 border-red-500/30'
                : 'bg-amber-950/30 border-amber-500/25'
            } ${isRead ? 'opacity-70' : 'opacity-100 shadow-md'}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div
                  className={`mt-0.5 h-8 w-8 rounded-xl flex items-center justify-center shrink-0 ${
                    isHigh
                      ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                      : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  }`}
                >
                  <AlertTriangle className="h-4 w-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-mono uppercase font-bold px-2 py-0.5 rounded-full ${
                        isHigh
                          ? 'bg-red-500/20 text-red-300'
                          : 'bg-amber-500/20 text-amber-300'
                      }`}
                    >
                      {alert.severity} Severity Alert
                    </span>
                    {isRead && (
                      <span className="text-[10px] text-slate-400 font-mono">
                        (Reviewed)
                      </span>
                    )}
                  </div>

                  {/* HARD RESTRICTION: Never rephrase or strengthen alert messages */}
                  <p className="text-xs text-white font-medium mt-1 leading-relaxed">
                    {alert.message}
                  </p>

                  <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mt-2 font-mono">
                    <Clock className="h-3 w-3" />
                    <span>{new Date(alert.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>

              {/* Action for doctors to mark as read */}
              {isDoctor && !isRead && onMarkRead && (
                <button
                  type="button"
                  onClick={() => onMarkRead(alert.id)}
                  className="shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-lg bg-teal-500/15 hover:bg-teal-500/25 border border-teal-500/30 text-teal-300 text-xs font-medium transition-colors"
                >
                  <Check className="h-3.5 w-3.5" />
                  <span>Mark Read</span>
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
