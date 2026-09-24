import React, { useState } from 'react'
import { apiFetch } from '@/api/client'
import { useToast } from '@/context/ToastContext'
import { Thermometer, Activity, CheckSquare, FileText, Send, Loader2 } from 'lucide-react'
import type { DailyHealthLog, CreateHealthLogPayload } from '@/types/api'

interface DailyReportFormProps {
  onLogSubmitted?: (log: DailyHealthLog) => void
}

export const DailyReportForm: React.FC<DailyReportFormProps> = ({ onLogSubmitted }) => {
  const { toast } = useToast()
  const [temperature, setTemperature] = useState<string>('36.8')
  const [painLevel, setPainLevel] = useState<number>(2)
  const [swelling, setSwelling] = useState<boolean>(false)
  const [medicationTaken, setMedicationTaken] = useState<boolean>(true)
  const [notes, setNotes] = useState<string>('')
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [formError, setFormError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    const tempNum = parseFloat(temperature)
    if (isNaN(tempNum) || tempNum < 35.0 || tempNum > 42.0) {
      setFormError('Temperature must be within physiological range: 35.0°C - 42.0°C.')
      return
    }

    if (painLevel < 0 || painLevel > 10) {
      setFormError('Pain level must be between 0 and 10.')
      return
    }

    if (notes.length > 1000) {
      setFormError('Notes cannot exceed 1000 characters.')
      return
    }

    setSubmitting(true)

    const payload: CreateHealthLogPayload = {
      temperature: tempNum,
      pain_level: painLevel,
      swelling,
      medication_taken: medicationTaken,
      notes: notes.trim(),
    }

    try {
      // POST /api/health/create/
      const newLog = await apiFetch<DailyHealthLog>('/health/create/', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      toast({
        title: 'Health Log Recorded',
        description: `Recovery score calculated: ${newLog.recovery_score}/100.`,
        variant: 'success',
      })

      // Reset form defaults
      setNotes('')
      if (onLogSubmitted) onLogSubmitted(newLog)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit health log.'
      setFormError(msg)
      toast({
        title: 'Submission Error',
        description: msg,
        variant: 'danger',
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="glass-card rounded-2xl p-5 border border-white/5">
      <div className="flex items-center gap-2.5 pb-3 border-b border-white/5 mb-4">
        <div className="h-8 w-8 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400">
          <Activity className="h-4 w-4" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">Daily Health Report</h3>
          <p className="text-[11px] text-slate-400">
            Submit daily recovery vitals and symptoms for clinical monitoring
          </p>
        </div>
      </div>

      {formError && (
        <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-xs text-red-300">
          {formError}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Temperature */}
        <div>
          <div className="flex justify-between items-center mb-1">
            <label
              htmlFor="temperature-input"
              className="text-xs font-medium text-slate-300 flex items-center gap-1.5"
            >
              <Thermometer className="h-3.5 w-3.5 text-teal-400" />
              Body Temperature (°C)
            </label>
            <span className="text-[11px] text-slate-500 font-mono">Range: 35.0 – 42.0</span>
          </div>
          <input
            id="temperature-input"
            type="number"
            step="0.1"
            min="35.0"
            max="42.0"
            required
            value={temperature}
            onChange={(e) => setTemperature(e.target.value)}
            className="w-full h-10 px-3 rounded-xl bg-slate-900/80 border border-white/10 text-xs text-white focus:outline-none focus:border-teal-500"
          />
        </div>

        {/* Pain Level 0 to 10 */}
        <div>
          <div className="flex justify-between items-center mb-1.5">
            <label className="text-xs font-medium text-slate-300">
              Pain Level (0 = No Pain, 10 = Worst)
            </label>
            <span className="text-xs font-mono font-bold text-teal-400 px-2 py-0.5 rounded bg-teal-500/10">
              {painLevel} / 10
            </span>
          </div>
          <div className="grid grid-cols-11 gap-1">
            {Array.from({ length: 11 }, (_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setPainLevel(i)}
                className={`h-8 rounded-lg text-xs font-mono font-medium transition-colors ${
                  painLevel === i
                    ? i > 7
                      ? 'bg-red-500 text-white font-bold'
                      : i > 4
                      ? 'bg-amber-500 text-slate-950 font-bold'
                      : 'bg-teal-500 text-slate-950 font-bold'
                    : 'bg-slate-900/80 text-slate-400 hover:text-white border border-white/5'
                }`}
              >
                {i}
              </button>
            ))}
          </div>
        </div>

        {/* Swelling & Medication Taken Switches */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
          <label className="flex items-center gap-2.5 p-3 rounded-xl bg-slate-900/50 border border-white/5 cursor-pointer hover:border-white/10 transition-colors">
            <input
              type="checkbox"
              checked={swelling}
              onChange={(e) => setSwelling(e.target.checked)}
              className="h-4 w-4 rounded border-slate-700 text-teal-500 focus:ring-teal-500/30"
            />
            <span className="text-xs text-slate-200">Swelling Present</span>
          </label>

          <label className="flex items-center gap-2.5 p-3 rounded-xl bg-slate-900/50 border border-white/5 cursor-pointer hover:border-white/10 transition-colors">
            <input
              type="checkbox"
              checked={medicationTaken}
              onChange={(e) => setMedicationTaken(e.target.checked)}
              className="h-4 w-4 rounded border-slate-700 text-teal-500 focus:ring-teal-500/30"
            />
            <span className="text-xs text-slate-200">Medication Taken Today</span>
          </label>
        </div>

        {/* Clinical notes */}
        <div>
          <label htmlFor="notes-input" className="block text-xs font-medium text-slate-300 mb-1">
            Notes / Observations (Optional, max 1000 characters)
          </label>
          <textarea
            id="notes-input"
            rows={2}
            maxLength={1000}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Report any specific sensations, dressing changes, or symptoms..."
            className="w-full p-3 rounded-xl bg-slate-900/80 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 resize-none"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full h-10 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {submitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Submitting Vitals...</span>
            </>
          ) : (
            <>
              <Send className="h-3.5 w-3.5" />
              <span>Submit Daily Log</span>
            </>
          )}
        </button>
      </form>
    </div>
  )
}
