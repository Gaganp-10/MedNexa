import React, { useState, useEffect } from 'react'
import { apiFetch } from '@/api/client'
import { useAuth } from '@/context/AuthContext'
import { WoundPhotoUpload } from '@/components/patient/WoundPhotoUpload'
import { SecureWoundImage } from '@/components/common/SecureWoundImage'
import { ClinicalDisclaimer } from '@/components/common/ClinicalDisclaimer'
import { Camera, RefreshCw, Loader2 } from 'lucide-react'
import type { WoundImage } from '@/types/api'

export const WoundView: React.FC = () => {
  const { user } = useAuth()
  const [wounds, setWounds] = useState<WoundImage[]>([])
  const [loading, setLoading] = useState(true)

  const isPatient = user?.role === 'patient'

  const fetchWounds = async () => {
    setLoading(true)
    try {
      if (isPatient) {
        // GET /api/wound/images/
        const data = await apiFetch<WoundImage[]>('/wound/images/')
        setWounds(data || [])
      } else {
        // Doctor: get wounds of first assigned patient
        const overview = await apiFetch<any>('/doctor/overview/').catch(() => null)
        if (overview?.patients?.[0]) {
          const firstPid = overview.patients[0].patient_id
          const pWounds = await apiFetch<WoundImage[]>(`/patient/${firstPid}/wounds/`)
          setWounds(pWounds || [])
        }
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchWounds()
  }, [user])

  return (
    <div className="space-y-6">
      <ClinicalDisclaimer />

      <div className="flex items-center justify-between pb-2 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-teal-500/15 border border-teal-500/30 flex items-center justify-center text-teal-400">
            <Camera className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Wound Monitoring & Imagery</h1>
            <p className="text-xs text-slate-400">
              Incision site photography, OpenCV analysis indicators, and historical records
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={fetchWounds}
          className="p-2 rounded-xl bg-slate-900 border border-white/10 hover:border-white/20 text-slate-300"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {isPatient && (
          <div className="lg:col-span-5">
            <WoundPhotoUpload
              onUploadSuccess={(newWound) => setWounds((prev) => [newWound, ...prev])}
            />
          </div>
        )}

        <div className={isPatient ? 'lg:col-span-7' : 'lg:col-span-12'}>
          <div className="glass-card rounded-2xl p-5 border border-white/5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-white/5">
              <h3 className="text-sm font-semibold text-white">Wound Imagery Records</h3>
              <span className="text-[11px] font-mono text-slate-400">
                {wounds.length} upload{wounds.length === 1 ? '' : 's'}
              </span>
            </div>

            {loading ? (
              <div className="flex flex-col items-center justify-center py-12 text-slate-400 text-xs gap-2">
                <Loader2 className="h-6 w-6 animate-spin text-teal-400" />
                <span>Decrypting wound records...</span>
              </div>
            ) : wounds.length === 0 ? (
              <div className="text-center py-12 text-xs text-slate-500">
                <p className="font-medium text-slate-400">No data yet.</p>
                <p className="text-[11px] text-slate-600 mt-1">
                  Uploaded incision photos will appear here.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-h-[600px] overflow-y-auto pr-1">
                {wounds.map((w) => (
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
      </div>
    </div>
  )
}
