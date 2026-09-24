import React from 'react'
import { AlertTriangle, ClipboardList, CheckCircle, Activity } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ReactNode
  variant?: 'default' | 'alert' | 'danger' | 'teal'
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  variant = 'default',
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'danger':
        return {
          bg: 'bg-red-500/10 border-red-500/30',
          iconColor: 'text-red-400',
          badge: 'bg-red-500/20 text-red-300',
        }
      case 'alert':
        return {
          bg: 'bg-amber-500/10 border-amber-500/30',
          iconColor: 'text-amber-400',
          badge: 'bg-amber-500/20 text-amber-300',
        }
      case 'teal':
        return {
          bg: 'bg-teal-500/10 border-teal-500/25',
          iconColor: 'text-teal-400',
          badge: 'bg-teal-500/20 text-teal-300',
        }
      default:
        return {
          bg: 'bg-slate-800/40 border-white/5',
          iconColor: 'text-slate-400',
          badge: 'bg-slate-700/50 text-slate-300',
        }
    }
  }

  const styles = getVariantStyles()

  return (
    <div className="glass-card rounded-2xl p-4 border border-white/5 flex items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        <div
          className={`h-11 w-11 rounded-xl flex items-center justify-center shrink-0 border ${styles.bg} ${styles.iconColor}`}
        >
          {icon}
        </div>
        <div>
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">
            {title}
          </span>
          <div className="flex items-baseline gap-2 mt-0.5">
            <span className="text-xl font-bold tracking-tight text-white">{value}</span>
            {subtitle && <span className="text-xs text-slate-400">{subtitle}</span>}
          </div>
        </div>
      </div>
    </div>
  )
}

interface ClinicalStatsGridProps {
  alertCount: number
  hasHighSeverityAlert?: boolean
  recentLogsCount: number
  adherencePercentage: number | null | undefined
  latestLogDate?: string | null
}

export const ClinicalStatsGrid: React.FC<ClinicalStatsGridProps> = ({
  alertCount,
  hasHighSeverityAlert = false,
  recentLogsCount,
  adherencePercentage,
  latestLogDate,
}) => {
  const alertVariant =
    alertCount > 0 ? (hasHighSeverityAlert ? 'danger' : 'alert') : 'default'

  const adherenceValue =
    typeof adherencePercentage === 'number' && !isNaN(adherencePercentage)
      ? `${adherencePercentage}%`
      : 'No data yet.'

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {/* 1. Alerts Stat */}
      <StatCard
        title="Active Alerts"
        value={alertCount}
        subtitle={alertCount === 0 ? 'Normal status' : 'Require review'}
        icon={<AlertTriangle className="h-5 w-5" />}
        variant={alertVariant}
      />

      {/* 2. Health Log Entries */}
      <StatCard
        title="Health Logs"
        value={recentLogsCount}
        subtitle={latestLogDate ? `Last: ${latestLogDate}` : 'Recorded entries'}
        icon={<ClipboardList className="h-5 w-5" />}
        variant="teal"
      />

      {/* 3. Medication Adherence */}
      <StatCard
        title="Med Adherence (7d)"
        value={adherenceValue}
        subtitle={
          typeof adherencePercentage === 'number' && adherencePercentage >= 80
            ? 'Compliant'
            : 'Adherence rate'
        }
        icon={<CheckCircle className="h-5 w-5" />}
        variant={
          typeof adherencePercentage === 'number'
            ? adherencePercentage >= 80
              ? 'teal'
              : 'alert'
            : 'default'
        }
      />
    </div>
  )
}
