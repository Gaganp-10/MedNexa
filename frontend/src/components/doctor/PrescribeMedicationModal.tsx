import React, { useState } from 'react'
import { apiFetch } from '@/api/client'
import { useToast } from '@/context/ToastContext'
import { Pill, X, Clock, Loader2, Plus } from 'lucide-react'
import type { MedicationItem, CreateMedicationPayload } from '@/types/api'

interface PrescribeMedicationModalProps {
  patientId: number
  patientName: string
  onClose: () => void
  onSuccess: (med: MedicationItem) => void
}

export const PrescribeMedicationModal: React.FC<PrescribeMedicationModalProps> = ({
  patientId,
  patientName,
  onClose,
  onSuccess,
}) => {
  const { toast } = useToast()
  const [medicineName, setMedicineName] = useState('')
  const [dosage, setDosage] = useState('')
  const [time, setTime] = useState('08:00')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!medicineName.trim() || !dosage.trim() || !time) {
      setError('Please fill in all prescription fields.')
      return
    }

    setSubmitting(true)
    const payload: CreateMedicationPayload = {
      patient_id: patientId,
      medicine_name: medicineName.trim(),
      dosage: dosage.trim(),
      time: time.length === 5 ? `${time}:00` : time,
    }

    try {
      // POST /api/medication/create/
      const newMed = await apiFetch<MedicationItem>('/medication/create/', {
        method: 'POST',
        body: JSON.stringify(payload),
      })

      toast({
        title: 'Medication Prescribed',
        description: `Prescribed ${newMed.medicine_name} (${newMed.dosage}). 7-day dose schedule generated.`,
        variant: 'success',
      })

      onSuccess(newMed)
      onClose()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to prescribe medication.'
      setError(msg)
      toast({
        title: 'Prescription Failed',
        description: msg,
        variant: 'danger',
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="glass-card rounded-2xl border border-white/10 max-w-md w-full p-6 shadow-2xl animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between pb-3 border-b border-white/5 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400">
              <Pill className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Prescribe Medication</h3>
              <p className="text-[11px] text-slate-400">Patient: {patientName}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-2.5 rounded-xl bg-red-500/10 border border-red-500/30 text-xs text-red-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Medication Name
            </label>
            <input
              type="text"
              required
              value={medicineName}
              onChange={(e) => setMedicineName(e.target.value)}
              placeholder="e.g. Amoxicillin, Ibuprofen"
              className="w-full h-10 px-3 rounded-xl bg-slate-900 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Dosage</label>
            <input
              type="text"
              required
              value={dosage}
              onChange={(e) => setDosage(e.target.value)}
              placeholder="e.g. 500mg, 1 tablet"
              className="w-full h-10 px-3 rounded-xl bg-slate-900 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Daily Administration Time
            </label>
            <div className="relative">
              <Clock className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="time"
                required
                value={time}
                onChange={(e) => setTime(e.target.value)}
                className="w-full h-10 pl-9 pr-3 rounded-xl bg-slate-900 border border-white/10 text-xs text-white focus:outline-none focus:border-teal-500"
              />
            </div>
            <p className="text-[10px] text-slate-400 mt-1">
              Upcoming 7-day dose schedule will automatically be scheduled upon prescribing.
            </p>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 h-9 rounded-xl bg-slate-900 border border-white/10 text-slate-300 text-xs hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 h-9 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Prescribing...</span>
                </>
              ) : (
                <>
                  <Plus className="h-3.5 w-3.5" />
                  <span>Confirm Prescription</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
