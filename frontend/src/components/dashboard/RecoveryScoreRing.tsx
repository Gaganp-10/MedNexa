import React from 'react'

interface RecoveryScoreRingProps {
  score: number | null | undefined
  size?: number
  strokeWidth?: number
  subtitle?: string
}

export const RecoveryScoreRing: React.FC<RecoveryScoreRingProps> = ({
  score,
  size = 140,
  strokeWidth = 10,
  subtitle = 'Recovery Score',
}) => {
  const hasScore = typeof score === 'number' && !isNaN(score)
  const safeScore = hasScore ? Math.max(0, Math.min(100, Math.round(score))) : 0

  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (safeScore / 100) * circumference

  // Color logic: calm teal/green for positive status; amber/red reserved strictly for clinical low recovery (<50)
  const getStrokeColor = (val: number) => {
    if (val >= 80) return '#14b8a6' // calm teal
    if (val >= 60) return '#2dd4bf' // teal light
    if (val >= 40) return '#f59e0b' // clinical amber
    return '#ef4444' // clinical red
  }

  const strokeColor = hasScore ? getStrokeColor(safeScore) : '#334155'

  return (
    <div className="flex flex-col items-center justify-center p-3 text-center">
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          className="transform -rotate-90 origin-center"
          aria-label={`Recovery Score: ${hasScore ? safeScore : 'No data'}`}
        >
          {/* Background circle track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="rgba(255, 255, 255, 0.08)"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Progress circle */}
          {hasScore && (
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              stroke={strokeColor}
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              fill="transparent"
              style={{
                transition: 'stroke-dashoffset 0.6s ease',
              }}
            />
          )}
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold tracking-tight text-white">
            {hasScore ? safeScore : '—'}
          </span>
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
            / 100
          </span>
        </div>
      </div>

      <p className="mt-2 text-xs font-medium text-slate-300">{subtitle}</p>
      {hasScore && (
        <span
          className="mt-1 text-[11px] px-2 py-0.5 rounded-full font-medium"
          style={{
            backgroundColor: `${strokeColor}22`,
            color: strokeColor,
          }}
        >
          {safeScore >= 80 ? 'Optimal' : safeScore >= 60 ? 'Satisfactory' : safeScore >= 40 ? 'Moderate' : 'Critical Review'}
        </span>
      )}
    </div>
  )
}
