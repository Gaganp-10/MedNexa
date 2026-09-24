import React, { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '@/api/client'
import { useToast } from '@/context/ToastContext'
import { RecoveryScoreRing } from '@/components/dashboard/RecoveryScoreRing'
import { RecoveryTrendChart } from '@/components/dashboard/RecoveryTrendChart'
import { ContactCard } from '@/components/dashboard/ContactCard'
import { ClinicalStatsGrid } from '@/components/dashboard/StatCards'
import { SecureWoundImage } from '@/components/common/SecureWoundImage'
import { AlertsListView } from '@/components/common/AlertsListView'
import { ChatPanel } from '@/components/chat/ChatPanel'
import { PrescribeMedicationModal } from '@/components/doctor/PrescribeMedicationModal'
import { ClinicalDisclaimer } from '@/components/common/ClinicalDisclaimer'
import {
  Users,
  Search,
  AlertTriangle,
  HeartPulse,
  Calendar,
  Activity,
  Pill,
  Camera,
  RefreshCw,
  Plus,
  Loader2,
  ChevronRight,
  UserCheck,
} from 'lucide-react'
import type {
  DoctorOverviewResponse,
  DoctorOverviewPatientSummary,
  DailyHealthLog,
  WoundImage,
  AlertItem,
  RecoveryTrendItem,
  MedicationItem,
  MedicationAdherenceSummary,
  RiskPredictionResponse,
} from '@/types/api'

export const DoctorDashboardView: React.FC = () => {
  const { toast } = useToast()

  const [loading, setLoading] = useState<boolean>(true)
  const [refreshing, setRefreshing] = useState<boolean>(false)
  const [overview, setOverview] = useState<DoctorOverviewResponse | null>(null)
  const [searchFilter, setSearchFilter] = useState<string>('')
  const [selectedPatientId, setSelectedPatientId] = useState<number | null>(null)

  // Selected Patient Deep Details State
  const [detailLoading, setDetailLoading] = useState<boolean>(false)
  const [patientLogs, setPatientLogs] = useState<DailyHealthLog[]>([])
  const [patientWounds, setPatientWounds] = useState<WoundImage[]>([])
  const [patientTrend, setPatientTrend] = useState<RecoveryTrendItem[]>([])
  const [patientRisk, setPatientRisk] = useState<RiskPredictionResponse | null>(null)
  const [patientAlerts, setPatientAlerts] = useState<AlertItem[]>([])
  const [patientMeds, setPatientMeds] = useState<MedicationItem[]>([])
  const [patientAdherence, setPatientAdherence] = useState<MedicationAdherenceSummary | null>(null)

  // Modals
  const [showPrescribeModal, setShowPrescribeModal] = useState<boolean>(false)
  const [showChatModal, setShowChatModal] = useState<boolean>(false)

  // 1. Load Doctor Overview (GET /api/doctor/overview/)
  const loadOverview = useCallback(async () => {
    try {
      // GET /api/doctor/overview/
      const data = await apiFetch<DoctorOverviewResponse>('/doctor/overview/')
      setOverview(data)

      // Set initial selected patient if none selected yet
      if (data.patients && data.patients.length > 0 && selectedPatientId === null) {
        setSelectedPatientId(data.patients[0].patient_id)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load doctor overview.'
      toast({
        title: 'Error loading dashboard',
        description: msg,
        variant: 'danger',
      })
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [selectedPatientId, toast])

  useEffect(() => {
    loadOverview()
  }, [loadOverview])

  // 2. Load Patient Specific Details when selected
  useEffect(() => {
    if (!selectedPatientId) {
      setPatientLogs([])
      setPatientWounds([])
      setPatientTrend([])
      setPatientAlerts([])
      setPatientMeds([])
      setPatientRisk(null)
      return
    }

    let isMounted = true
    setDetailLoading(true)

    Promise.allSettled([
      // GET /api/patient/<patient_id>/logs/
      apiFetch<DailyHealthLog[]>(`/patient/${selectedPatientId}/logs/`),
      // GET /api/patient/<patient_id>/wounds/
      apiFetch<WoundImage[]>(`/patient/${selectedPatientId}/wounds/`),
      // GET /api/patient/<patient_id>/recovery-trend/
      apiFetch<RecoveryTrendItem[]>(`/patient/${selectedPatientId}/recovery-trend/`),
      // GET /api/patient/<patient_id>/risk/
      apiFetch<RiskPredictionResponse>(`/patient/${selectedPatientId}/risk/`),
      // GET /api/patient/<patient_id>/alerts/
      apiFetch<AlertItem[]>(`/patient/${selectedPatientId}/alerts/`),
      // GET /api/medication/<patient_id>/
      apiFetch<MedicationItem[]>(`/medication/${selectedPatientId}/`),
      // GET /api/patient/<patient_id>/medication-adherence/?days=7
      apiFetch<MedicationAdherenceSummary>(`/patient/${selectedPatientId}/medication-adherence/?days=7`),
    ]).then(
      ([
        logsRes,
        woundsRes,
        trendRes,
        riskRes,
        alertsRes,
        medsRes,
        adherenceRes,
      ]) => {
        if (!isMounted) return
        if (logsRes.status === 'fulfilled') setPatientLogs(logsRes.value || [])
        if (woundsRes.status === 'fulfilled') setPatientWounds(woundsRes.value || [])
        if (trendRes.status === 'fulfilled') setPatientTrend(trendRes.value || [])
        if (riskRes.status === 'fulfilled') setPatientRisk(riskRes.value)
        if (alertsRes.status === 'fulfilled') setPatientAlerts(alertsRes.value || [])
        if (medsRes.status === 'fulfilled') setPatientMeds(medsRes.value || [])
        if (adherenceRes.status === 'fulfilled') setPatientAdherence(adherenceRes.value)
        setDetailLoading(false)
      }
    )

    return () => {
      isMounted = false
    }
  }, [selectedPatientId])

  // Handle Mark Alert As Read: PATCH /api/alerts/<alert_id>/read/
  const handleMarkAlertRead = async (alertId: number) => {
    try {
      await apiFetch<AlertItem>(`/alerts/${alertId}/read/`, {
        method: 'PATCH',
        body: JSON.stringify({ is_read: true }),
      })

      setPatientAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, is_read: true } : a))
      )

      toast({
        title: 'Alert Reviewed',
        description: 'Alert marked as read in clinical record.',
        variant: 'success',
      })

      // Refresh overview counts
      loadOverview()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update alert.'
      toast({
        title: 'Action Error',
        description: msg,
        variant: 'danger',
      })
    }
  }

  // Filter patients by name or surgery
  const filteredPatients = (overview?.patients || []).filter((p) => {
    const q = searchFilter.toLowerCase()
    return (
      p.full_name.toLowerCase().includes(q) ||
      p.username.toLowerCase().includes(q) ||
      p.surgery_type.toLowerCase().includes(q)
    )
  })

  const selectedPatient = overview?.patients.find(
    (p) => p.patient_id === selectedPatientId
  )

  const selectedPatientHasHighAlert = patientAlerts.some(
    (a) => a.severity === 'high' && !a.is_read
  )

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-slate-400">
        <Loader2 className="h-8 w-8 animate-spin text-teal-400" />
        <p className="text-xs font-medium">Loading clinical doctor overview...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Permanent Medical Safety Disclaimer */}
      <ClinicalDisclaimer />

      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-white/5">
        <div>
          <span className="text-[11px] font-mono uppercase tracking-wider text-teal-400 font-semibold">
            Doctor Command Center
          </span>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white mt-0.5">
            Post-Surgical Inpatient & Outpatient Monitoring
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Attending: <strong className="text-white">{overview?.doctor_name}</strong> •{' '}
            <span className="font-mono text-teal-300">
              {overview?.total_patients} Assigned Patient
              {overview?.total_patients === 1 ? '' : 's'}
            </span>
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={refreshing}
            onClick={() => {
              setRefreshing(true)
              loadOverview()
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/80 border border-white/10 hover:border-white/20 text-slate-300 text-xs font-medium transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh Overview</span>
          </button>
        </div>
      </div>

      {/* Master-Detail Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Assigned Patients List */}
        <div className="lg:col-span-4 glass-card rounded-2xl p-4 border border-white/5 flex flex-col h-[750px] overflow-hidden">
          <div className="pb-3 border-b border-white/5">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-teal-400" />
                <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                  Assigned Patients
                </h3>
              </div>
              <span className="text-[11px] font-mono text-slate-400">
                {filteredPatients.length} shown
              </span>
            </div>

            {/* Filter Search */}
            <div className="relative mt-2">
              <Search className="h-3.5 w-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                placeholder="Filter by name, procedure..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="w-full h-8 pl-8 pr-3 rounded-lg bg-slate-900/80 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500"
              />
            </div>
          </div>

          {/* Patients scrollable list */}
          <div className="flex-1 overflow-y-auto mt-3 space-y-2 pr-1">
            {filteredPatients.length === 0 ? (
              <div className="text-center py-10 text-xs text-slate-500">
                No data yet.
                <p className="text-[10px] text-slate-600 mt-1">
                  No assigned patients found matching query.
                </p>
              </div>
            ) : (
              filteredPatients.map((p) => {
                const isSelected = p.patient_id === selectedPatientId
                const unreadAlerts = p.alert_count

                return (
                  <button
                    key={p.patient_id}
                    type="button"
                    onClick={() => setSelectedPatientId(p.patient_id)}
                    className={`w-full text-left p-3.5 rounded-xl border transition-all ${
                      isSelected
                        ? 'bg-teal-500/15 border-teal-500/40 shadow-sm'
                        : 'bg-slate-900/40 border-white/5 hover:border-white/15 hover:bg-slate-900/70'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="text-xs font-bold text-white tracking-tight">
                          {p.full_name}
                        </h4>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          {p.surgery_type}
                        </p>
                        <p className="text-[10px] text-slate-500 font-mono">
                          Date: {p.surgery_date}
                        </p>
                      </div>

                      <div className="flex flex-col items-end gap-1 shrink-0">
                        {/* Recovery Score Pill */}
                        <span
                          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-md ${
                            p.latest_recovery_score >= 80
                              ? 'bg-teal-500/20 text-teal-300'
                              : p.latest_recovery_score >= 50
                              ? 'bg-amber-500/20 text-amber-300'
                              : 'bg-red-500/20 text-red-300'
                          }`}
                        >
                          Score: {p.latest_recovery_score}
                        </span>

                        {/* Unread Alert badge */}
                        {unreadAlerts > 0 && (
                          <span className="flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/30">
                            <AlertTriangle className="h-2.5 w-2.5" />
                            {unreadAlerts} alert{unreadAlerts === 1 ? '' : 's'}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Verbatim risk text */}
                    <div className="mt-2 pt-2 border-t border-white/5 flex items-center justify-between text-[10px]">
                      <span className="text-slate-400">Risk Indicator:</span>
                      <span className="text-slate-300 truncate max-w-[170px] text-right font-medium">
                        {p.latest_risk_indicator || 'Not recorded'}
                      </span>
                    </div>
                  </button>
                )
              })
            )}
          </div>
        </div>

        {/* Right Column: Selected Patient Deep Details */}
        <div className="lg:col-span-8 space-y-5">
          {!selectedPatient ? (
            <div className="glass-card rounded-2xl p-12 border border-white/5 text-center text-slate-400 text-xs">
              <p className="font-medium text-slate-300">Select a patient to inspect records</p>
              <p className="text-[11px] text-slate-500 mt-1">
                Clinical history, trend, wound images, and prescription tools will appear here.
              </p>
            </div>
          ) : detailLoading ? (
            <div className="glass-card rounded-2xl p-12 border border-white/5 flex flex-col items-center justify-center gap-3 text-slate-400">
              <Loader2 className="h-6 w-6 animate-spin text-teal-400" />
              <p className="text-xs">Loading patient clinical file #{selectedPatient.patient_id}...</p>
            </div>
          ) : (
            <>
              {/* Patient Banner & Actions */}
              <div className="glass-card rounded-2xl p-5 border border-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-white tracking-tight">
                      {selectedPatient.full_name}
                    </h2>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      ID #{selectedPatient.patient_id}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-slate-400">
                    <span>
                      Procedure: <strong className="text-slate-200">{selectedPatient.surgery_type}</strong>
                    </span>
                    <span>•</span>
                    <span>Date: {selectedPatient.surgery_date}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setShowChatModal(true)}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-teal-500/15 hover:bg-teal-500/25 border border-teal-500/30 text-teal-300 text-xs font-semibold transition-colors"
                  >
                    <span>Open Patient Chat</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowPrescribeModal(true)}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-semibold transition-colors"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    <span>Prescribe Medication</span>
                  </button>
                </div>
              </div>

              {/* Stats Grid for this Patient */}
              <ClinicalStatsGrid
                alertCount={patientAlerts.length}
                hasHighSeverityAlert={selectedPatientHasHighAlert}
                recentLogsCount={patientLogs.length}
                adherencePercentage={patientAdherence?.adherence_percentage}
                latestLogDate={
                  patientLogs.length > 0
                    ? new Date(patientLogs[0].created_at).toLocaleDateString()
                    : null
                }
              />

              {/* Recovery Score & Trend */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
                <div className="md:col-span-5 glass-card rounded-2xl p-5 border border-white/5 flex flex-col justify-between">
                  <div className="pb-3 border-b border-white/5">
                    <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                      Patient Recovery Status
                    </h3>
                  </div>
                  <div className="py-2 my-auto">
                    <RecoveryScoreRing
                      score={selectedPatient.latest_recovery_score}
                      subtitle="Current Recovery Index"
                    />
                  </div>
                  {/* Verbatim risk text */}
                  <div className="p-3 rounded-xl bg-slate-900/80 border border-white/5 text-center">
                    <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block mb-0.5">
                      Prototype Risk Indicator (Verbatim)
                    </span>
                    <p className="text-xs font-semibold text-teal-300">
                      {patientRisk?.risk_prediction || selectedPatient.latest_risk_indicator || 'No data yet.'}
                    </p>
                  </div>
                </div>

                <div className="md:col-span-7 glass-card rounded-2xl p-5 border border-white/5 flex flex-col">
                  <div className="pb-3 border-b border-white/5 mb-2">
                    <h3 className="text-sm font-semibold text-white">Chronological Recovery Trend</h3>
                    <p className="text-[11px] text-slate-400">Score history over surgical recovery period</p>
                  </div>
                  <div className="flex-1 min-h-[220px]">
                    <RecoveryTrendChart data={patientTrend} height={230} />
                  </div>
                </div>
              </div>

              {/* Wound Site Photos */}
              <div className="glass-card rounded-2xl p-5 border border-white/5 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-white/5">
                  <div className="flex items-center gap-2">
                    <Camera className="h-4 w-4 text-teal-400" />
                    <h3 className="text-sm font-semibold text-white">Patient Wound Records</h3>
                  </div>
                  <span className="text-[11px] text-slate-400 font-mono">
                    {patientWounds.length} upload{patientWounds.length === 1 ? '' : 's'}
                  </span>
                </div>

                {patientWounds.length === 0 ? (
                  <div className="text-center py-8 text-xs text-slate-400">
                    <p className="font-medium text-slate-500">No data yet.</p>
                    <p className="text-[11px] text-slate-600 mt-1">
                      No wound images uploaded by patient yet.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[350px] overflow-y-auto pr-1">
                    {patientWounds.map((w) => (
                      <SecureWoundImage
                        key={w.id}
                        fileUrl={w.file_url}
                        alt={`Wound record #${w.id}`}
                        analysisResult={w.analysis_result}
                        uploadedAt={w.uploaded_at}
                      />
                    ))}
                  </div>
                )}
              </div>

              {/* Patient Active Alerts (with Doctor Mark as Read action) */}
              <div className="glass-card rounded-2xl p-5 border border-white/5 space-y-3">
                <div className="flex items-center justify-between pb-3 border-b border-white/5">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                    <h3 className="text-sm font-semibold text-white">Patient Decision-Support Alerts</h3>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    {patientAlerts.length} total
                  </span>
                </div>

                <AlertsListView
                  alerts={patientAlerts}
                  isDoctor={true}
                  onMarkRead={handleMarkAlertRead}
                />
              </div>

              {/* Health Logs Table */}
              <div className="glass-card rounded-2xl p-5 border border-white/5 space-y-3">
                <div className="flex items-center justify-between pb-3 border-b border-white/5">
                  <div className="flex items-center gap-2">
                    <Activity className="h-4 w-4 text-teal-400" />
                    <h3 className="text-sm font-semibold text-white">Daily Health Log History</h3>
                  </div>
                  <span className="text-[11px] text-slate-400 font-mono">
                    {patientLogs.length} entries
                  </span>
                </div>

                {patientLogs.length === 0 ? (
                  <div className="text-center py-6 text-xs text-slate-400">
                    <p className="font-medium text-slate-500">No data yet.</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-white/10 text-slate-400 font-mono text-[11px]">
                          <th className="py-2 px-3">Date</th>
                          <th className="py-2 px-3">Temp (°C)</th>
                          <th className="py-2 px-3">Pain (0-10)</th>
                          <th className="py-2 px-3">Swelling</th>
                          <th className="py-2 px-3">Meds Taken</th>
                          <th className="py-2 px-3">Score</th>
                          <th className="py-2 px-3">Notes</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {patientLogs.map((log) => (
                          <tr key={log.id} className="hover:bg-white/5 transition-colors">
                            <td className="py-2.5 px-3 text-slate-300 font-mono text-[11px]">
                              {new Date(log.created_at).toLocaleDateString()}
                            </td>
                            <td className="py-2.5 px-3 font-semibold text-white">
                              {log.temperature.toFixed(1)}°
                            </td>
                            <td className="py-2.5 px-3">
                              <span
                                className={`px-2 py-0.5 rounded font-mono font-bold ${
                                  log.pain_level > 6
                                    ? 'bg-red-500/20 text-red-300'
                                    : log.pain_level > 3
                                    ? 'bg-amber-500/20 text-amber-300'
                                    : 'bg-teal-500/20 text-teal-300'
                                }`}
                              >
                                {log.pain_level}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-slate-300">
                              {log.swelling ? (
                                <span className="text-amber-400 font-medium">Yes</span>
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

              {/* Active Prescribed Medications */}
              <div className="glass-card rounded-2xl p-5 border border-white/5 space-y-3">
                <div className="flex items-center justify-between pb-3 border-b border-white/5">
                  <div className="flex items-center gap-2">
                    <Pill className="h-4 w-4 text-teal-400" />
                    <h3 className="text-sm font-semibold text-white">Prescribed Medications</h3>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowPrescribeModal(true)}
                    className="flex items-center gap-1 text-xs text-teal-400 hover:text-teal-300 font-medium"
                  >
                    <Plus className="h-3 w-3" /> Add Prescription
                  </button>
                </div>

                {patientMeds.length === 0 ? (
                  <div className="text-center py-6 text-xs text-slate-400">
                    <p className="font-medium text-slate-500">No data yet.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {patientMeds.map((med) => (
                      <div
                        key={med.id}
                        className="p-3.5 rounded-xl bg-slate-900/50 border border-white/5 flex items-center justify-between"
                      >
                        <div>
                          <h4 className="text-xs font-semibold text-white">{med.medicine_name}</h4>
                          <p className="text-[11px] text-teal-300 mt-0.5">{med.dosage}</p>
                          <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                            Daily at: {med.time}
                          </p>
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                          ID #{med.id}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Prescribe Medication Modal */}
      {showPrescribeModal && selectedPatient && (
        <PrescribeMedicationModal
          patientId={selectedPatient.patient_id}
          patientName={selectedPatient.full_name}
          onClose={() => setShowPrescribeModal(false)}
          onSuccess={(newMed) => {
            setPatientMeds((prev) => [newMed, ...prev])
            loadOverview()
          }}
        />
      )}

      {/* Chat Modal with Patient */}
      {showChatModal && selectedPatient && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-xl">
            <ChatPanel
              patientProfileId={selectedPatient.patient_id}
              counterpartName={selectedPatient.full_name}
              counterpartRole="patient"
              onClose={() => setShowChatModal(false)}
            />
          </div>
        </div>
      )}
    </div>
  )
}
