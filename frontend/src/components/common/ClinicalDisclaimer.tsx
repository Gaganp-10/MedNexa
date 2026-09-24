import React from 'react'
import { AlertCircle } from 'lucide-react'
import { CLINICAL_SAFETY_DISCLAIMER } from '@/config/env'

export const ClinicalDisclaimer: React.FC<{ className?: string }> = ({ className = '' }) => {
  return (
    <aside
      aria-label="Clinical Decision-Support Disclaimer"
      className={`w-full bg-amber-500/10 border-y md:border md:rounded-xl border-amber-500/20 px-4 py-2.5 flex items-center justify-between gap-3 text-xs text-amber-200/90 shadow-sm backdrop-blur-md ${className}`}
    >
      <div className="flex items-center gap-2.5">
        <AlertCircle className="h-4 w-4 text-amber-400 shrink-0" aria-hidden="true" />
        <span className="font-medium tracking-wide">
          {CLINICAL_SAFETY_DISCLAIMER}
        </span>
      </div>
      <span className="shrink-0 text-[10px] tracking-wider uppercase px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono">
        Prototype v1.0
      </span>
    </aside>
  )
}
