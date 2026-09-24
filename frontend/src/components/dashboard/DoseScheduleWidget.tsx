import React, { useState } from 'react'
import { Pill, CheckCircle2, Clock, Check } from 'lucide-react'
import type { MedicationDose } from '@/types/api'

interface DoseScheduleWidgetProps {
  todayDoses: MedicationDose[]
  upcomingDoses?: MedicationDose[]
  isPatient: boolean
  onMarkTaken?: (doseId: number) => Promise<void>
}

export const DoseScheduleWidget: React.FC<DoseScheduleWidgetProps> = ({
  todayDoses,
  upcomingDoses = [],
  isPatient,
  onMarkTaken,
}) => {
  const [activeTab, setActiveTab] = useState<'today' | 'upcoming'>('today')
  const [processingId, setProcessingId] = useState<number | null>(null)

  const handleTake = async (id: number) => {
    if (!onMarkTaken) return
    setProcessingId(id)
    try {
      await onMarkTaken(id)
    } finally {
      setProcessingId(null)
    }
  }

  const currentList = activeTab === 'today' ? todayDoses : upcomingDoses

  const formatDoseTime = (isoString: string) => {
    try {
      const d = new Date(isoString)
      if (isNaN(d.getTime())) return isoString
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return isoString
    }
  }

  const formatDoseDate = (isoString: string) => {
    try {
      const d = new Date(isoString)
      if (isNaN(d.getTime())) return ''
      return d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })
    } catch {
      return ''
    }
  }

  return (
    <div className="glass-card rounded-2xl p-5 border border-white/5 flex flex-col h-full">
      <div className="flex items-center justify-between pb-3 border-b border-white/5">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400">
            <Pill className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Scheduled Doses</h3>
            <p className="text-[11px] text-slate-400">Prescribed post-surgery regimen</p>
          </div>
        </div>

        {/* Tab switch */}
        <div className="flex rounded-lg bg-slate-900/80 p-0.5 border border-white/5 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('today')}
            className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
              activeTab === 'today'
                ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Today ({todayDoses.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('upcoming')}
            className={`px-2.5 py-1 rounded-md font-medium transition-colors ${
              activeTab === 'upcoming'
                ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Upcoming ({upcomingDoses.length})
          </button>
        </div>
      </div>

      <div className="mt-3 space-y-2.5 flex-1 overflow-y-auto max-h-[320px] pr-1">
        {currentList.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center text-slate-400 text-xs">
            <p className="font-medium text-slate-500">No data yet.</p>
            <p className="text-[11px] text-slate-600 mt-1">
              {activeTab === 'today'
                ? 'No doses scheduled for today.'
                : 'No upcoming scheduled doses found.'}
            </p>
          </div>
        ) : (
          currentList.map((dose) => {
            const isTaken = dose.status === 'taken'
            const isMissed = dose.status === 'missed'
            const isBusy = processingId === dose.id

            return (
              <div
                key={dose.id}
                className="flex items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/50 border border-white/5 hover:border-white/10 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`mt-0.5 h-7 w-7 rounded-lg flex items-center justify-center shrink-0 ${
                      isTaken
                        ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
                        : isMissed
                        ? 'bg-amber-500/15 text-amber-400 border border-amber-500/20'
                        : 'bg-slate-800 text-slate-300 border border-white/5'
                    }`}
                  >
                    {isTaken ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <Clock className="h-4 w-4" />
                    )}
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-white tracking-tight">
                      {dose.medicine_name}
                    </h4>
                    <div className="flex items-center gap-2 mt-0.5 text-[11px] text-slate-400">
                      <span className="font-medium text-teal-300/90">{dose.dosage}</span>
                      <span>•</span>
                      <span>
                        {activeTab === 'upcoming' && (
                          <span className="mr-1">{formatDoseDate(dose.scheduled_for)}</span>
                        )}
                        {formatDoseTime(dose.scheduled_for)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="shrink-0 flex items-center gap-2">
                  {isTaken ? (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Taken
                    </span>
                  ) : isMissed ? (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      Missed
                    </span>
                  ) : isPatient && onMarkTaken ? (
                    <button
                      type="button"
                      disabled={isBusy}
                      onClick={() => handleTake(dose.id)}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-teal-500/20 hover:bg-teal-500/30 border border-teal-500/40 text-teal-200 text-xs font-medium transition-colors disabled:opacity-50"
                    >
                      <Check className="h-3 w-3" />
                      <span>{isBusy ? 'Saving...' : 'Mark Taken'}</span>
                    </button>
                  ) : (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-400">
                      Scheduled
                    </span>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
