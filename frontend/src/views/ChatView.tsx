import React, { useState, useEffect } from 'react'
import { apiFetch } from '@/api/client'
import { useAuth } from '@/context/AuthContext'
import { ChatPanel } from '@/components/chat/ChatPanel'
import { ClinicalDisclaimer } from '@/components/common/ClinicalDisclaimer'
import { MessageSquare, Users, Loader2 } from 'lucide-react'
import type { ConversationItem, PaginatedResponse } from '@/types/api'

export const ChatView: React.FC = () => {
  const { user } = useAuth()
  const [conversations, setConversations] = useState<ConversationItem[]>([])
  const [selectedConvId, setSelectedConvId] = useState<number | null>(null)
  const [loading, setLoading] = useState<boolean>(true)

  useEffect(() => {
    let isMounted = true
    setLoading(true)

    // GET /api/communication/conversations/
    apiFetch<PaginatedResponse<ConversationItem>>('/communication/conversations/')
      .then((res) => {
        if (isMounted) {
          const list = res.results || []
          setConversations(list)
          if (list.length > 0 && selectedConvId === null) {
            setSelectedConvId(list[0].id)
          }
          setLoading(false)
        }
      })
      .catch(() => {
        if (isMounted) {
          setConversations([])
          setLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [selectedConvId])

  const selectedConv = conversations.find((c) => c.id === selectedConvId)

  const counterpartName =
    user?.role === 'doctor'
      ? selectedConv?.patient.user.first_name
        ? `${selectedConv.patient.user.first_name} ${selectedConv.patient.user.last_name}`
        : selectedConv?.patient.user.username
      : selectedConv?.doctor.first_name
      ? `Dr. ${selectedConv.doctor.first_name} ${selectedConv.doctor.last_name}`
      : selectedConv?.doctor.username

  return (
    <div className="space-y-6">
      <ClinicalDisclaimer />

      <div className="flex items-center gap-3 pb-2 border-b border-white/5">
        <div className="h-9 w-9 rounded-xl bg-teal-500/15 border border-teal-500/30 flex items-center justify-center text-teal-400">
          <MessageSquare className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Clinical Communications</h1>
          <p className="text-xs text-slate-400">
            Real-time encrypted message channels between assigned clinical team and patients
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
        {/* Conversations List (Doctor or Multi-patient) */}
        <div className="md:col-span-4 glass-card rounded-2xl p-4 border border-white/5 flex flex-col h-[650px] overflow-hidden">
          <div className="flex items-center justify-between pb-3 border-b border-white/5 mb-2">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-teal-400" />
              <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                Conversations
              </h3>
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              {conversations.length}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {loading ? (
              <div className="flex flex-col items-center justify-center h-40 text-slate-400 text-xs gap-2">
                <Loader2 className="h-5 w-5 animate-spin text-teal-400" />
                <span>Loading conversations...</span>
              </div>
            ) : conversations.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-500">
                No data yet.
                <p className="text-[10px] text-slate-600 mt-1">
                  Conversations initialize automatically on first message.
                </p>
              </div>
            ) : (
              conversations.map((conv) => {
                const isSelected = conv.id === selectedConvId
                const name =
                  user?.role === 'doctor'
                    ? conv.patient.user.first_name
                      ? `${conv.patient.user.first_name} ${conv.patient.user.last_name}`
                      : conv.patient.user.username
                    : conv.doctor.first_name
                    ? `Dr. ${conv.doctor.first_name} ${conv.doctor.last_name}`
                    : conv.doctor.username

                return (
                  <button
                    key={conv.id}
                    type="button"
                    onClick={() => setSelectedConvId(conv.id)}
                    className={`w-full text-left p-3 rounded-xl border transition-all ${
                      isSelected
                        ? 'bg-teal-500/15 border-teal-500/30'
                        : 'bg-slate-900/40 border-white/5 hover:border-white/15'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-white truncate">{name}</span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {new Date(conv.updated_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    {conv.patient.surgery_type && user?.role === 'doctor' && (
                      <p className="text-[10px] text-teal-400 mt-0.5">
                        {conv.patient.surgery_type}
                      </p>
                    )}
                    {conv.latest_message && (
                      <p className="text-[11px] text-slate-400 truncate mt-1">
                        {conv.latest_message.content}
                      </p>
                    )}
                  </button>
                )
              })
            )}
          </div>
        </div>

        {/* Selected Active Chat Panel */}
        <div className="md:col-span-8">
          <ChatPanel
            conversationId={selectedConvId}
            counterpartName={counterpartName}
            counterpartRole={user?.role === 'doctor' ? 'patient' : 'doctor'}
          />
        </div>
      </div>
    </div>
  )
}
