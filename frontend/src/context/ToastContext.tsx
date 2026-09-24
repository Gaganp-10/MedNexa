import React, { createContext, useContext, useState, useCallback } from 'react'
import * as ToastPrimitive from '@radix-ui/react-toast'
import { X, AlertTriangle, Info, Bell, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export type ToastVariant = 'default' | 'success' | 'alert' | 'danger'

export interface ToastItem {
  id: string
  title: string
  description?: string
  variant?: ToastVariant
}

interface ToastContextType {
  toast: (options: { title: string; description?: string; variant?: ToastVariant }) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const addToast = useCallback(
    ({ title, description, variant = 'default' }: { title: string; description?: string; variant?: ToastVariant }) => {
      const id = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
      setToasts((prev) => [...prev, { id, title, description, variant }])
    },
    []
  )

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      <ToastPrimitive.Provider swipeDirection="right">
        {children}
        {toasts.map((t) => {
          const isDanger = t.variant === 'danger'
          const isAlert = t.variant === 'alert'
          const isSuccess = t.variant === 'success'

          return (
            <ToastPrimitive.Root
              key={t.id}
              duration={6000}
              onOpenChange={(open) => {
                if (!open) removeToast(t.id)
              }}
              className={cn(
                'fixed bottom-4 right-4 z-50 flex w-full max-w-md items-start gap-3 rounded-xl p-4 shadow-2xl backdrop-blur-xl border transition-all duration-200',
                isDanger && 'bg-red-950/90 border-red-500/40 text-red-100',
                isAlert && 'bg-amber-950/90 border-amber-500/40 text-amber-100',
                isSuccess && 'bg-teal-950/90 border-teal-500/40 text-teal-100',
                !isDanger && !isAlert && !isSuccess && 'bg-slate-900/90 border-slate-700/60 text-slate-100'
              )}
            >
              <div className="mt-0.5 shrink-0">
                {isDanger && <AlertTriangle className="h-5 w-5 text-red-400" />}
                {isAlert && <AlertTriangle className="h-5 w-5 text-amber-400" />}
                {isSuccess && <CheckCircle2 className="h-5 w-5 text-teal-400" />}
                {!isDanger && !isAlert && !isSuccess && <Bell className="h-5 w-5 text-teal-400" />}
              </div>
              <div className="flex-1">
                <ToastPrimitive.Title className="text-sm font-semibold tracking-tight">
                  {t.title}
                </ToastPrimitive.Title>
                {t.description && (
                  <ToastPrimitive.Description className="mt-1 text-xs opacity-90 leading-relaxed">
                    {t.description}
                  </ToastPrimitive.Description>
                )}
              </div>
              <ToastPrimitive.Close className="shrink-0 rounded-lg p-1 text-slate-400 hover:text-white transition-colors">
                <X className="h-4 w-4" />
              </ToastPrimitive.Close>
            </ToastPrimitive.Root>
          )
        })}
        <ToastPrimitive.Viewport className="fixed bottom-0 right-0 z-50 flex flex-col p-4 gap-2 w-full max-w-sm m-0 list-none outline-none" />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}
