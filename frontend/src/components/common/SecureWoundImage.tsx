import React, { useEffect, useState } from 'react'
import { fetchSecureImageBlobUrl } from '@/api/client'
import { Image as ImageIcon, AlertCircle, Loader2 } from 'lucide-react'

interface SecureWoundImageProps {
  fileUrl: string
  alt: string
  className?: string
  analysisResult?: string
  uploadedAt?: string
}

export const SecureWoundImage: React.FC<SecureWoundImageProps> = ({
  fileUrl,
  alt,
  className = '',
  analysisResult,
  uploadedAt,
}) => {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true
    let currentBlobUrl: string | null = null

    if (!fileUrl) {
      setLoading(false)
      setError('No file URL provided')
      return
    }

    setLoading(true)
    setError(null)

    fetchSecureImageBlobUrl(fileUrl)
      .then((url) => {
        if (isMounted) {
          currentBlobUrl = url
          setBlobUrl(url)
          setLoading(false)
        } else {
          URL.revokeObjectURL(url)
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to load image')
          setLoading(false)
        }
      })

    return () => {
      isMounted = false
      if (currentBlobUrl) {
        URL.revokeObjectURL(currentBlobUrl)
      }
    }
  }, [fileUrl])

  return (
    <div className={`overflow-hidden rounded-xl border border-white/10 bg-slate-950/60 flex flex-col ${className}`}>
      <div className="relative aspect-video w-full bg-slate-900 flex items-center justify-center overflow-hidden">
        {loading && (
          <div className="flex flex-col items-center gap-2 text-slate-400 text-xs">
            <Loader2 className="h-5 w-5 animate-spin text-teal-400" />
            <span>Decrypting clinical image...</span>
          </div>
        )}

        {error && !loading && (
          <div className="flex flex-col items-center gap-1.5 p-4 text-center text-slate-400 text-xs">
            <AlertCircle className="h-5 w-5 text-amber-400" />
            <span className="font-medium text-slate-300">Image unavailable</span>
            <span className="text-[11px] text-slate-500">{error}</span>
          </div>
        )}

        {blobUrl && !loading && !error && (
          <img
            src={blobUrl}
            alt={alt}
            className="w-full h-full object-cover transition-transform duration-300 hover:scale-105"
          />
        )}
      </div>

      {(analysisResult || uploadedAt) && (
        <div className="p-3 border-t border-white/5 space-y-1 bg-slate-900/40">
          {analysisResult && (
            <div>
              <span className="text-[10px] uppercase font-mono tracking-wider text-teal-400 block">
                Analysis Output (Verbatim)
              </span>
              {/* Never rephrase or strengthen backend clinical text */}
              <p className="text-xs text-slate-200 mt-0.5 leading-snug">
                {analysisResult}
              </p>
            </div>
          )}
          {uploadedAt && (
            <p className="text-[10px] text-slate-400">
              Uploaded: {new Date(uploadedAt).toLocaleString()}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
