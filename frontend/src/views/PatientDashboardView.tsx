import React, { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '@/api/client'
import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/context/ToastContext'
import { RecoveryScoreRing } from '@/components/dashboard/RecoveryScoreRing'
import { RecoveryTrendChart } from '@/components/dashboard/RecoveryTrendChart'
import { ContactCard } from '@/components/dashboard/ContactCard'
import { DoseScheduleWidget } from '@/components/dashboard/DoseScheduleWidget'
import { ClinicalStatsGrid } from '@/components/dashboard/StatCards'
import { DailyReportForm } from '@/components/patient/DailyReportForm'
import { WoundPhotoUpload } from '@/components/patient/WoundPhotoUpload'
import { SecureWoundImage } from '@/components/common/SecureWoundImage'
import { AlertsListView } from '@/components/common/AlertsListView'
import { ChatPanel } from '@/components/chat/ChatPanel'
import { ClinicalDisclaimer } from '@/components/common/ClinicalDisclaimer'
import { unwrapList } from '@/lib/utils'
import {
  HeartPulse,
  Activity,
  AlertTriangle,
  Camera,
  Calendar,
  ShieldCheck,
  RefreshCw,
  Loader2,
} from 'lucide-react'
import type {
  PatientSelfProfile,
  DailyHealthLog,
  WoundImage,
  AlertItem,
  RecoveryTrendItem,
  MedicationDose,
  MedicationAdherenceSummary,
  RiskPredictionResponse,
} from '@/types/api'

interface PatientDashboardViewProps {
  initialTab?: string
}

export const PatientDashboardView: React.FC<PatientDashboardViewProps> = ({
  initialTab = 'dashboard',
}) => {
  const { user } = useAuth()
  const { toast } = useToast()

  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [profile, setProfile] = useState<PatientSelfProfile | null>(null)
  const [recoveryTrend, setRecoveryTrend] = useState<RecoveryTrendItem[]>([])
  const [riskData, setRiskData] = useState<RiskPredictionResponse | null>(null)
  const [todayDoses, setTodayDoses] = useState<MedicationDose[]>([])
  const [upcomingDoses, setUpcomingDoses] = useState<MedicationDose[]>([])
  const [adherence, setAdherence] = useState<MedicationAdherenceSummary | null>(null)
  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const [healthLogs, setHealthLogs] = useState<DailyHealthLog[]>([])
  const [woundImages, setWoundImages] = useState<WoundImage[]>([])
  const [activeSection, setActiveSection] = useState<string>(initialTab)
  const [showChatModal, setShowChatModal] = useState<boolean>(false)

  const patientProfileId = user?.patient_profile_id

  const loadAllData = useCallback(async () => {
    try {
      // 1. GET /api/patient/profile/
      const profileData = await apiFetch<PatientSelfProfile>('/patient/profile/').catch(() => null)
      setProfile(profileData)

      const pid = profileData?.patient_profile_id || patientProfileId

      if (pid) {
        // Run parallel queries against the exact documented endpoints
        const [
          trendRes,
          riskRes,
          todayDosesRes,
          upcomingDosesRes,
          adherenceRes,
          alertsRes,
          logsRes,
          woundsRes,
        ] = await Promise.allSettled([
          // GET /api/patient/<patient_id>/recovery-trend/
          apiFetch<RecoveryTrendItem[]>(`/patient/${pid}/recovery-trend/`),
          // GET /api/patient/<patient_id>/risk/
          apiFetch<RiskPredictionResponse>(`/patient/${pid}/risk/`),
          // GET /api/medication/doses/today/
          apiFetch<MedicationDose[]>('/medication/doses/today/'),
          // GET /api/medication/doses/upcoming/?days=7
          apiFetch<MedicationDose[]>('/medication/doses/upcoming/?days=7'),
          // GET /api/patient/<patient_id>/medication-adherence/?days=7
          apiFetch<MedicationAdherenceSummary>(`/patient/${pid}/medication-adherence/?days=7`),
          // GET /api/patient/<patient_id>/alerts/
          apiFetch<AlertItem[]>(`/patient/${pid}/alerts/`),
          // GET /api/health/logs/
          apiFetch<DailyHealthLog[]>('/health/logs/'),
          // GET /api/wound/images/
          apiFetch<WoundImage[]>('/wound/images/'),
        ])

        if (trendRes.status === 'fulfilled') setRecoveryTrend(unwrapList<RecoveryTrendItem>(trendRes.value))
        if (riskRes.status === 'fulfilled') setRiskData(riskRes.value)
        if (todayDosesRes.status === 'fulfilled') setTodayDoses(unwrapList<MedicationDose>(todayDosesRes.value))
        if (upcomingDosesRes.status === 'fulfilled') setUpcomingDoses(unwrapList<MedicationDose>(upcomingDosesRes.value))
        if (adherenceRes.status === 'fulfilled') setAdherence(adherenceRes.value)
        if (alertsRes.status === 'fulfilled') setAlerts(unwrapList<AlertItem>(alertsRes.value))
        if (logsRes.status === 'fulfilled') setHealthLogs(unwrapList<DailyHealthLog>(logsRes.value))
        if (woundsRes.status === 'fulfilled') setWoundImages(unwrapList<WoundImage>(woundsRes.value))
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error fetching patient data.'
      toast({
        title: 'Error updating dashboard',
        description: msg,
        variant: 'danger',
      })
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [patientProfileId, toast])

  useEffect(() => {
    loadAllData()
  }, [loadAllData])

  // Handle Dose Mark Taken
  const handleMarkDoseTaken = async (doseId: number) => {
    try {
      // PATCH /api/medication/doses/<dose_id>/take/
      await apiFetch<MedicationDose>(`/medication/doses/${doseId}/take/`, {
        method: 'PATCH',
      })

      toast({
        title: 'Dose Recorded',
        description: 'Scheduled dose marked as taken.',
        variant: 'success',
      })

      // Reload dose schedule
      const [todayDosesRes, upcomingDosesRes] = await Promise.all([
        apiFetch<MedicationDose[]>('/medication/doses/today/'),
        apiFetch<MedicationDose[]>('/medication/doses/upcoming/?days=7'),
      ])
      setTodayDoses(unwrapList<MedicationDose>(todayDosesRes))
      setUpcomingDoses(unwrapList<MedicationDose>(upcomingDosesRes))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to record dose.'
      toast({
        title: 'Action Error',
        description: msg,
        variant: 'danger',
      })
    }
  }

  // Handle Health Log submitted
  const handleHealthLogSubmitted = (newLog: DailyHealthLog) => {
    setHealthLogs((prev) => [newLog, ...prev])
    loadAllData()
  }

  // Handle Wound uploaded
  const handleWoundUploaded = (newWound: WoundImage) => {
    setWoundImages((prev) => [newWound, ...prev])
    loadAllData()
  }

  const latestScore =
    healthLogs.length > 0
      ? healthLogs[0].recovery_score
      : recoveryTrend.length > 0
      ? recoveryTrend[recoveryTrend.length - 1].score
      : null

  const latestLogDate =
    healthLogs.length > 0
      ? new Date(healthLogs[0].created_at).toLocaleDateString()
      : null

  const hasHighAlert = alerts.some((a) => a.severity === 'high')

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-slate-400">
        <Loader2 className="h-8 w-8 animate-spin text-teal-400" />
        <p className="text-xs font-medium">Loading clinical recovery data...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Permanent Medical Safety Disclaimer */}
      <ClinicalDisclaimer />

      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-white/5">
        <div>
          <span className="text-[11px] font-mono uppercase tracking-wider text-teal-400 font-semibold">
            Patient Portal
          </span>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white mt-0.5">
            Post-Operative Recovery Overview
          </h1>
          <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-slate-400">
            {profile?.surgery_type && (
              <span className="flex items-center gap-1.5">
                <HeartPulse className="h-3.5 w-3.5 text-teal-400" />
                Procedure: <strong className="text-white">{profile.surgery_type}</strong>
              </span>
            )}
            {profile?.surgery_date && (
              <span className="flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5 text-slate-400" />
                Date: {profile.surgery_date}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={refreshing}
            onClick={() => {
              setRefreshing(true)
              loadAllData()
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/80 border border-white/10 hover:border-white/20 text-slate-300 text-xs font-medium transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Stat Cards Grid */}
      <ClinicalStatsGrid
        alertCount={alerts.length}
        hasHighSeverityAlert={hasHighAlert}
        recentLogsCount={healthLogs.length}
        adherencePercentage={adherence?.adherence_percentage}
        latestLogDate={latestLogDate}
      />

      {/* Assigned Doctor Contact Card */}
      {profile?.assigned_doctor && (
        <ContactCard
          role="doctor"
          name={profile.assigned_doctor.name}
          subtitle="Primary Attending Surgeon"
          onOpenChat={() => setShowChatModal(true)}
        />
      )}

      {/* Main Grid: Recovery Score Ring, Trend Chart, & Dose Schedule */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Recovery Score Card */}
        <div className="lg:col-span-4 glass-card rounded-2xl p-5 border border-white/5 flex flex-col justify-between">
          <div className="flex items-center justify-between pb-3 border-b border-white/5">
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
              Current Recovery
            </h3>
            <span className="text-[10px] text-slate-400 font-mono">Real Heuristic</span>
          </div>

          <div className="my-auto py-2">
            <RecoveryScoreRing score={latestScore} subtitle="Overall Recovery Index" />
          </div>

          {/* Prototype Risk Indicator (verbatim) */}
          <div className="p-3 rounded-xl bg-slate-900/80 border border-white/5 text-center mt-2">
            <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block mb-0.5">
              Risk Indicator (Decision Support)
            </span>
            {riskData?.risk_prediction ? (
              <p className="text-xs font-semibold text-teal-300">
                {riskData.risk_prediction}
              </p>
            ) : (
              <p className="text-xs text-slate-500">No data yet.</p>
            )}
          </div>
        </div>

        {/* Recovery Trend Chart */}
        <div className="lg:col-span-8 glass-card rounded-2xl p-5 border border-white/5 flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-white/5 mb-3">
            <div>
              <h3 className="text-sm font-semibold text-white">Recovery Trend History</h3>
              <p className="text-[11px] text-slate-400">Chronological score progression</p>
            </div>
            <span className="text-[10px] text-slate-400 font-mono">0 – 100 scale</span>
          </div>

          <div className="flex-1 min-h-[220px]">
            <RecoveryTrendChart data={recoveryTrend} height={230} />
          </div>
        </div>
      </div>

      {/* Schedule & Daily Tasks Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Dose Schedule Widget */}
        <div className="lg:col-span-6">
          <DoseScheduleWidget
            todayDoses={todayDoses}
            upcomingDoses={upcomingDoses}
            isPatient={true}
            onMarkTaken={handleMarkDoseTaken}
          />
        </div>

        {/* Daily Report Form */}
        <div className="lg:col-span-6">
          <DailyReportForm onLogSubmitted={handleHealthLogSubmitted} />
        </div>
      </div>

      {/* Wound Site Photo & Recent Images */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-6">
          <WoundPhotoUpload onUploadSuccess={handleWoundUploaded} />
        </div>

        <div className="lg:col-span-6 glass-card rounded-2xl p-5 border border-white/5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-white/5">
            <div className="flex items-center gap-2">
              <Camera className="h-4 w-4 text-teal-400" />
              <h3 className="text-sm font-semibold text-white">Uploaded Wound Images</h3>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">
              {woundImages.length} record{woundImages.length === 1 ? '' : 's'}
            </span>
          </div>

          {woundImages.length === 0 ? (
            <div className="text-center py-10 text-xs text-slate-400">
              <p className="font-medium text-slate-500">No data yet.</p>
              <p className="text-[11px] text-slate-600 mt-1">
                Photographs uploaded will be displayed here securely.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-[380px] overflow-y-auto pr-1">
              {woundImages.map((w) => (
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
      </div>

      {/* Active Clinical Alerts Section */}
      <div className="glass-card rounded-2xl p-5 border border-white/5 space-y-3">
        <div className="flex items-center justify-between pb-3 border-b border-white/5">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            <h3 className="text-sm font-semibold text-white">Clinical Alerts</h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {alerts.length} active
          </span>
        </div>

        <AlertsListView alerts={alerts} isDoctor={false} />
      </div>

      {/* Embedded Doctor-Patient Chat Modal / Drawer */}
      {showChatModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-xl">
            <ChatPanel
              patientProfileId={patientProfileId}
              counterpartName={profile?.assigned_doctor?.name}
              counterpartRole="doctor"
              onClose={() => setShowChatModal(false)}
            />
          </div>
        </div>
      )}
    </div>
  )
}
