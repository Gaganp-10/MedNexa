import React from 'react'
import { MessageSquare, UserCheck, Stethoscope } from 'lucide-react'

interface ContactCardProps {
  role: 'doctor' | 'patient'
  name: string
  subtitle?: string
  extraInfo?: string
  onOpenChat: () => void
}

export const ContactCard: React.FC<ContactCardProps> = ({
  role,
  name,
  subtitle,
  extraInfo,
  onOpenChat,
}) => {
  const isDoctorRole = role === 'doctor'

  return (
    <div className="glass-card rounded-2xl p-4 flex items-center justify-between gap-4 border border-white/5">
      <div className="flex items-center gap-3">
        <div className="h-11 w-11 rounded-xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 shrink-0">
          {isDoctorRole ? (
            <Stethoscope className="h-5 w-5" />
          ) : (
            <UserCheck className="h-5 w-5" />
          )}
        </div>
        <div>
          <span className="text-[11px] font-medium text-teal-400 uppercase tracking-wider block">
            {isDoctorRole ? 'Assigned Doctor' : 'Assigned Patient'}
          </span>
          <h4 className="text-sm font-semibold text-white tracking-tight">{name}</h4>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
          {extraInfo && <p className="text-[11px] text-slate-500">{extraInfo}</p>}
        </div>
      </div>

      <button
        type="button"
        onClick={onOpenChat}
        className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal-500/15 hover:bg-teal-500/25 border border-teal-500/30 text-teal-300 text-xs font-medium transition-colors"
      >
        <MessageSquare className="h-3.5 w-3.5" />
        <span>Chat</span>
      </button>
    </div>
  )
}
