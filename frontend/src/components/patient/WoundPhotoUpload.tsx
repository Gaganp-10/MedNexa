import React, { useState, useRef } from 'react'
import { apiFetch } from '@/api/client'
import { useToast } from '@/context/ToastContext'
import { Camera, Upload, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import type { WoundImage } from '@/types/api'

interface WoundPhotoUploadProps {
  onUploadSuccess?: (wound: WoundImage) => void
}

export const WoundPhotoUpload: React.FC<WoundPhotoUploadProps> = ({ onUploadSuccess }) => {
  const { toast } = useToast()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [uploading, setUploading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [latestAnalysis, setLatestAnalysis] = useState<string | null>(null)

  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const cameraInputRef = useRef<HTMLInputElement | null>(null)

  const handleFileSelect = (file: File | undefined) => {
    setError(null)
    setLatestAnalysis(null)
    if (!file) return

    // 5MB limit
    if (file.size > 5 * 1024 * 1024) {
      setError('Selected image exceeds the 5MB file size limit.')
      return
    }

    const validExtensions = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']
    if (!validExtensions.includes(file.type)) {
      setError('Unsupported file type. Please select a JPEG, PNG, or WebP image.')
      return
    }

    setSelectedFile(file)
    const objectUrl = URL.createObjectURL(file)
    setPreviewUrl(objectUrl)
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select or capture a wound photograph first.')
      return
    }

    setUploading(true)
    setError(null)

    const formData = new FormData()
    // Backend requires field named 'image'
    formData.append('image', selectedFile)

    try {
      // POST /api/wound/upload/
      const result = await apiFetch<WoundImage>('/wound/upload/', {
        method: 'POST',
        body: formData,
      })

      // Verbatim analysis text
      setLatestAnalysis(result.analysis_result)

      toast({
        title: 'Wound Upload Successful',
        description: 'Analysis completed. Output logged for clinical review.',
        variant: 'success',
      })

      setSelectedFile(null)
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
        setPreviewUrl(null)
      }

      if (onUploadSuccess) onUploadSuccess(result)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to upload wound image.'
      setError(msg)
      toast({
        title: 'Upload Failed',
        description: msg,
        variant: 'danger',
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="glass-card rounded-2xl p-5 border border-white/5 space-y-4">
      <div className="flex items-center gap-2.5 pb-3 border-b border-white/5">
        <div className="h-8 w-8 rounded-lg bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400">
          <Camera className="h-4 w-4" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">Wound Site Photo Upload</h3>
          <p className="text-[11px] text-slate-400">
            Upload wound photographs for automated heuristic tracking and doctor review
          </p>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-2 text-xs text-red-300">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-400 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Hidden file & camera inputs */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => handleFileSelect(e.target.files?.[0])}
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => handleFileSelect(e.target.files?.[0])}
      />

      {/* Image Preview or Selector */}
      {previewUrl ? (
        <div className="space-y-3">
          <div className="relative aspect-video w-full rounded-xl overflow-hidden border border-teal-500/30 bg-slate-950">
            <img
              src={previewUrl}
              alt="Selected wound site preview"
              className="w-full h-full object-contain"
            />
          </div>
          <div className="flex items-center justify-between text-xs text-slate-400 px-1">
            <span>{selectedFile?.name}</span>
            <span>{((selectedFile?.size || 0) / (1024 * 1024)).toFixed(2)} MB</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={uploading}
              onClick={handleUpload}
              className="flex-1 h-10 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {uploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Processing & Uploading...</span>
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  <span>Confirm & Upload Photo</span>
                </>
              )}
            </button>
            <button
              type="button"
              disabled={uploading}
              onClick={() => {
                setSelectedFile(null)
                if (previewUrl) URL.revokeObjectURL(previewUrl)
                setPreviewUrl(null)
              }}
              className="px-3 h-10 rounded-xl bg-slate-900 border border-white/10 text-slate-300 text-xs hover:text-white"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => cameraInputRef.current?.click()}
            className="p-4 rounded-xl border border-white/10 bg-slate-900/40 hover:bg-slate-900/80 hover:border-teal-500/30 flex flex-col items-center justify-center gap-2 text-center transition-all group"
          >
            <div className="h-10 w-10 rounded-xl bg-teal-500/10 text-teal-400 flex items-center justify-center group-hover:scale-105 transition-transform">
              <Camera className="h-5 w-5" />
            </div>
            <div>
              <span className="text-xs font-semibold text-white block">Take Photo</span>
              <span className="text-[11px] text-slate-400">Use mobile or webcam</span>
            </div>
          </button>

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="p-4 rounded-xl border border-white/10 bg-slate-900/40 hover:bg-slate-900/80 hover:border-teal-500/30 flex flex-col items-center justify-center gap-2 text-center transition-all group"
          >
            <div className="h-10 w-10 rounded-xl bg-teal-500/10 text-teal-400 flex items-center justify-center group-hover:scale-105 transition-transform">
              <Upload className="h-5 w-5" />
            </div>
            <div>
              <span className="text-xs font-semibold text-white block">Browse Files</span>
              <span className="text-[11px] text-slate-400">JPEG, PNG, WebP up to 5MB</span>
            </div>
          </button>
        </div>
      )}

      {/* Verbatim Analysis Output */}
      {latestAnalysis && (
        <div className="p-3.5 rounded-xl bg-teal-500/10 border border-teal-500/30 space-y-1 animate-in fade-in">
          <div className="flex items-center gap-1.5 text-teal-400 text-xs font-semibold">
            <CheckCircle className="h-4 w-4" />
            <span>Analysis Result (Verbatim Backend Heuristic):</span>
          </div>
          {/* HARD RESTRICTION: Never rephrase or strengthen backend clinical text */}
          <p className="text-xs text-teal-100 font-mono leading-relaxed pl-5">
            {latestAnalysis}
          </p>
        </div>
      )}
    </div>
  )
}
