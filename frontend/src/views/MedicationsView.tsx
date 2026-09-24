import React, { useState, useEffect } from 'react'
import { apiFetch } from '@/api/client'
import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/context/ToastContext'
import { DoseScheduleWidget } from '@/components/dashboard/DoseScheduleWidget'
import { ClinicalDisclaimer } from '@/components/common/ClinicalDisclaimer'
import { Pill, CheckCircle, Clock, RefreshCw, Loader2 } from 'lucide-react'
import type { MedicationDose, MedicationItem, MedicationAdherenceSummary } from '@/types/api'

export const MedicationsView: React.FC = () => {
  const { user } = useAuth()
  const { toast } = useToast()
  const [todayDoses, setTodayDoses] = useState<MedicationDose[]>([])
  const [upcomingDoses, setUpcomingDoses] = useState<MedicationDose[]>([])
  const [prescriptions, setPrescriptions] = useState<MedicationItem[]>([])
  const [adherence, setAdherence] = useState<MedicationAdherenceSummary | null>(null)
  const [loading, setLoading] = useState(true)

  const isPatient = user?.role === 'patient'
  const pid = user?.patient_profile_id

  const loadMedicationData = async () => {
    setLoading(true)
    try {
      if (isPatient) {
        const [todayRes, upcomingRes] = await Promise.all([
          apiFetch<MedicationDose[]>('/medication/doses/today/').catch(() => []),
          apiFetch<MedicationDose[]>('/medication/doses/upcoming/?days=7').catch(() => []),
        ])
        setTodayDoses(todayRes)
        setUpcomingDoses(upcomingRes)

        if (pid) {
          const [adhRes, medsRes] = await Promise.all([
            apiFetch<MedicationAdherenceSummary>(`/patient/${pid}/medication-adherence/?days=7`).catch(() => null),
            apiFetch<MedicationItem[]>(`/medication/${pid}/`).catch(() => []),
          ])
          setAdherence(adhRes)
          setPrescriptions(medsRes)
        }
      } else {
        // Doctor: get first patient from overview or list
        const overview = await apiFetch<any>('/doctor/overview/').catch(() => null)
        if (overview?.patients?.[0]) {
          const firstPid = overview.patients[0].patient_id
          const [adhRes, medsRes] = await Promise.all([
            apiFetch<MedicationAdherenceSummary>(`/patient/${firstPid}/medication-adherence/?days=7`).catch(() => null),
            apiFetch<MedicationItem[]>(`/medication/${firstPid}/`).catch(() => []),
          ])
          setAdherence(adhRes)
          setPrescriptions(medsRes)
        }
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadMedicationData()
  }, [user])

  const handleMarkDoseTaken = async (doseId: number) => {
    try {
      await apiFetch<MedicationDose>(`/medication/doses/${doseId}/take/`, {
        method: 'PATCH',
      })
      toast({
        title: 'Dose Recorded',
        description: 'Medication dose marked as taken.',
        variant: 'success',
      })
      loadMedicationData()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update dose.'
      toast({
        title: 'Action Error',
        description: msg,
        variant: 'danger',
      })
    }
  }

  return (
    <div className="space-y-6">
      <ClinicalDisclaimer />

      <div className="flex items-center justify-between pb-2 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-teal-500/15 border border-teal-500/30 flex items-center justify-center text-teal-400">
            <Pill className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Medication Schedule & Adherence
            </h1>
            <p className="text-xs text-slate-400">
              Prescription tracking, scheduled dose times, and compliance metrics
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={loadMedicationData}
          className="p-2 rounded-xl bg-slate-900 border border-white/10 hover:border-white/20 text-slate-300"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {/* Adherence Summary Card */}
      {adherence && (
        <div className="glass-card rounded-2xl p-5 border border-white/5 grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
          <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
            <span className="text-[11px] text-slate-400 block">Compliance Rate (7d)</span>
            <span className="text-xl font-bold text-teal-400 mt-1 block">
              {adherence.adherence_percentage}%
            </span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
            <span className="text-[11px] text-slate-400 block">Total Due</span>
            <span className="text-xl font-bold text-white mt-1 block">
              {adherence.total_scheduled || adherence.total_scheduled_due}
            </span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
            <span className="text-[11px] text-slate-400 block">Doses Taken</span>
            <span className="text-xl font-bold text-emerald-400 mt-1 block">
              {adherence.taken_count || adherence.doses_taken}
            </span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5">
            <span className="text-[11px] text-slate-400 block">Doses Missed</span>
            <span className="text-xl font-bold text-amber-400 mt-1 block">
              {adherence.missed_count || adherence.doses_missed}
            </span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Scheduled Doses Widget */}
        <div className="lg:col-span-7">
          <DoseScheduleWidget
            todayDoses={todayDoses}
            upcomingDoses={upcomingDoses}
            isPatient={isPatient}
            onMarkTaken={handleMarkDoseTaken}
          />
        </div>

        {/* Prescriptions List */}
        <div className="lg:col-span-5 glass-card rounded-2xl p-5 border border-white/5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-white/5">
            <h3 className="text-sm font-semibold text-white">Active Prescriptions</h3>
            <span className="text-[11px] font-mono text-slate-400">
              {prescriptions.length} prescribed
            </span>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-10 text-slate-400 text-xs gap-2">
              <Loader2 className="h-5 w-5 animate-spin text-teal-400" />
              <span>Loading prescriptions...</span>
            </div>
          ) : prescriptions.length === 0 ? (
            <div className="text-center py-10 text-xs text-slate-500">
              <p className="font-medium text-slate-400">No data yet.</p>
              <p className="text-[11px] text-slate-600 mt-1">
                Prescribed medications will appear here.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5 max-h-[400px] overflow-y-auto pr-1">
              {prescriptions.map((med) => (
                <div
                  key={med.id}
                  className="p-3.5 rounded-xl bg-slate-900/50 border border-white/5 flex items-center justify-between"
                >
                  <div>
                    <h4 className="text-xs font-semibold text-white">{med.medicine_name}</h4>
                    <p className="text-[11px] text-teal-300 mt-0.5">{med.dosage}</p>
                    <p className="text-[10px] text-slate-400 font-mono mt-0.5">
                      Schedule: Daily at {med.time}
                    </p>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-slate-800 text-slate-400">
                    ID #{med.id}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
