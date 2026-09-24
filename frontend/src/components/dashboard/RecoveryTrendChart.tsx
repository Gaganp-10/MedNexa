import React from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'
import type { RecoveryTrendItem } from '@/types/api'

interface RecoveryTrendChartProps {
  data: RecoveryTrendItem[]
  height?: number
}

export const RecoveryTrendChart: React.FC<RecoveryTrendChartProps> = ({
  data,
  height = 220,
}) => {
  if (!data || data.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center text-slate-400 text-xs py-10"
        style={{ height }}
      >
        <p className="font-medium text-slate-500">No data yet.</p>
        <p className="text-[11px] text-slate-600 mt-1">
          Recovery trend will display as daily health logs are submitted.
        </p>
      </div>
    )
  }

  // Format data for chart display
  const chartData = data.map((item) => {
    // Format date string
    let formattedDate = item.date
    try {
      const d = new Date(item.date)
      if (!isNaN(d.getTime())) {
        formattedDate = d.toLocaleDateString(undefined, {
          month: 'short',
          day: 'numeric',
        })
      }
    } catch {
      // Keep as-is
    }
    return {
      rawDate: item.date,
      displayDate: formattedDate,
      score: item.score,
    }
  })

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 16, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.05)" />
          <XAxis
            dataKey="displayDate"
            stroke="#64748b"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
          />
          <YAxis
            domain={[0, 100]}
            stroke="#64748b"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
            ticks={[0, 25, 50, 75, 100]}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                const item = payload[0].payload
                return (
                  <div className="rounded-lg border border-slate-700 bg-slate-900/95 p-2 shadow-xl backdrop-blur-md text-xs">
                    <p className="text-slate-400 font-mono text-[10px]">{item.rawDate}</p>
                    <p className="font-semibold text-teal-400 mt-0.5">
                      Recovery Score: {item.score}
                    </p>
                  </div>
                )
              }
              return null
            }}
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#14b8a6"
            strokeWidth={2.5}
            dot={{ r: 3, fill: '#14b8a6', strokeWidth: 1, stroke: '#0f172a' }}
            activeDot={{ r: 5, fill: '#2dd4bf', stroke: '#0f172a', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
