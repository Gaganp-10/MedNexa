import React, { useState, useEffect, useRef } from 'react'
import { apiFetch, getAccessToken, refreshAccessToken } from '@/api/client'
import { WS_BASE_URL } from '@/config/env'
import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/context/ToastContext'
import {
  Send,
  MessageSquare,
  Clock,
  CheckCheck,
  Check,
  User,
  Loader2,
  Stethoscope,
} from 'lucide-react'
import type {
  ConversationItem,
  ChatMessage,
  PaginatedResponse,
  WsChatMessageBroadcast,
} from '@/types/api'

interface ChatPanelProps {
  conversationId?: number | null
  patientProfileId?: number | null
  counterpartName?: string
  counterpartRole?: 'doctor' | 'patient'
  onClose?: () => void
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  conversationId: initialConversationId,
  patientProfileId,
  counterpartName,
  counterpartRole,
  onClose,
}) => {
  const { user } = useAuth()
  const { toast } = useToast()
  const [conversationId, setConversationId] = useState<number | null>(
    initialConversationId || null
  )
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(true)
  const [sending, setSending] = useState<boolean>(false)
  const [wsConnected, setWsConnected] = useState<boolean>(false)

  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const chatWsRef = useRef<WebSocket | null>(null)

  // Scroll to bottom on new message
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // 1. Resolve conversation ID if not provided directly
  useEffect(() => {
    let isMounted = true

    const resolveConversation = async () => {
      if (initialConversationId) {
        setConversationId(initialConversationId)
        return
      }

      setLoading(true)
      try {
        // GET /api/communication/conversations/
        const res = await apiFetch<PaginatedResponse<ConversationItem>>(
          '/communication/conversations/'
        )
        const conversations = res.results || []

        if (conversations.length > 0) {
          // If a patientProfileId is provided, find matching conversation
          if (patientProfileId) {
            const found = conversations.find(
              (c) => c.patient.id === patientProfileId
            )
            if (found && isMounted) {
              setConversationId(found.id)
              return
            }
          }
          // Otherwise pick the first active conversation
          if (isMounted) {
            setConversationId(conversations[0].id)
          }
        } else {
          // If no conversation exists yet, and we are a doctor with a patientProfileId, or a patient
          if (isMounted) {
            setConversationId(null)
          }
        }
      } catch (err: unknown) {
        // Conversation not yet created
        if (isMounted) setConversationId(null)
      } finally {
        if (isMounted) setLoading(false)
      }
    }

    resolveConversation()

    return () => {
      isMounted = false
    }
  }, [initialConversationId, patientProfileId])

  // 2. Load messages for the resolved conversation
  useEffect(() => {
    if (!conversationId) {
      setMessages([])
      setLoading(false)
      return
    }

    let isMounted = true
    setLoading(true)

    // GET /api/communication/conversations/<id>/messages/
    apiFetch<PaginatedResponse<ChatMessage>>(
      `/communication/conversations/${conversationId}/messages/`
    )
      .then((res) => {
        if (isMounted) {
          setMessages(res.results || [])
          setLoading(false)
          setTimeout(scrollToBottom, 100)

          // Mark unread messages sent to current user as read
          const unreadForMe = (res.results || []).filter(
            (m) => !m.is_read && m.sender?.id !== user?.id && m.sender_id !== user?.id
          )
          unreadForMe.forEach((msg) => {
            // PATCH /api/communication/messages/<id>/read/
            apiFetch(`/communication/messages/${msg.id}/read/`, {
              method: 'PATCH',
            }).catch(() => {})
          })
        }
      })
      .catch(() => {
        if (isMounted) {
          setMessages([])
          setLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [conversationId, user?.id])

  // 3. Connect to Chat WebSocket: ws://<backend-host>:8000/ws/chat/<conversation_id>/?token=<access_token>
  useEffect(() => {
    if (!conversationId) return

    let isDisposed = false

    const connectChatWs = async () => {
      let token = getAccessToken()
      if (!token) {
        token = await refreshAccessToken()
      }
      if (!token || isDisposed) return

      try {
        const wsUrl = `${WS_BASE_URL}/ws/chat/${conversationId}/?token=${token}`
        const ws = new WebSocket(wsUrl)
        chatWsRef.current = ws

        ws.onopen = () => {
          if (!isDisposed) setWsConnected(true)
        }

        ws.onmessage = (event) => {
          try {
            const data: WsChatMessageBroadcast = JSON.parse(event.data)
            if (data && data.content) {
              setMessages((prev) => {
                // Deduplicate by message ID
                if (prev.some((m) => m.id === data.id)) return prev
                const newMsg: ChatMessage = {
                  id: data.id,
                  conversation_id: data.conversation_id,
                  sender: {
                    id: data.sender_id,
                    username: data.sender_name,
                    role: data.sender_role,
                  },
                  sender_id: data.sender_id,
                  sender_name: data.sender_name,
                  sender_role: data.sender_role,
                  content: data.content,
                  is_read: data.is_read,
                  created_at: data.created_at,
                }
                return [...prev, newMsg]
              })
              setTimeout(scrollToBottom, 50)

              // If I am the recipient, mark as read
              if (data.sender_id !== user?.id) {
                apiFetch(`/communication/messages/${data.id}/read/`, {
                  method: 'PATCH',
                }).catch(() => {})
              }
            }
          } catch {
            // Ignore parse error
          }
        }

        ws.onclose = () => {
          if (!isDisposed) setWsConnected(false)
        }
      } catch {
        if (!isDisposed) setWsConnected(false)
      }
    }

    connectChatWs()

    return () => {
      isDisposed = true
      if (chatWsRef.current) {
        chatWsRef.current.close(1000)
        chatWsRef.current = null
      }
      setWsConnected(false)
    }
  }, [conversationId, user?.id])

  // 4. Send Message Handler
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = content.trim()
    if (!trimmed || sending) return

    setSending(true)

    try {
      if (conversationId) {
        // Send via REST POST /api/communication/conversations/<conversation_id>/messages/
        const newMsg = await apiFetch<ChatMessage>(
          `/communication/conversations/${conversationId}/messages/`,
          {
            method: 'POST',
            body: JSON.stringify({ content: trimmed }),
          }
        )

        setMessages((prev) => {
          if (prev.some((m) => m.id === newMsg.id)) return prev
          return [...prev, newMsg]
        })
        setContent('')
        setTimeout(scrollToBottom, 50)
      } else {
        // First message flow as documented in FRONTEND.md:
        // POST /api/communication/conversations/<patient_profile_id>/messages/
        // If patient, pass their own profile id or 0
        const targetId = patientProfileId || user?.patient_profile_id || 0
        const newMsg = await apiFetch<ChatMessage>(
          `/communication/conversations/${targetId}/messages/`,
          {
            method: 'POST',
            body: JSON.stringify({ content: trimmed }),
          }
        )

        if (newMsg.conversation || newMsg.conversation_id) {
          setConversationId(newMsg.conversation || newMsg.conversation_id || null)
        }
        setMessages((prev) => [...prev, newMsg])
        setContent('')
        setTimeout(scrollToBottom, 50)
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to deliver message.'
      toast({
        title: 'Message delivery failed',
        description: msg,
        variant: 'danger',
      })
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="glass-card rounded-2xl border border-white/10 flex flex-col h-[600px] max-h-[80vh] overflow-hidden shadow-2xl">
      {/* Chat Header */}
      <div className="p-4 border-b border-white/10 bg-slate-900/60 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-teal-500/15 border border-teal-500/30 flex items-center justify-center text-teal-400">
            {counterpartRole === 'doctor' ? (
              <Stethoscope className="h-5 w-5" />
            ) : (
              <User className="h-5 w-5" />
            )}
          </div>
          <div>
            <h4 className="text-xs font-semibold text-white tracking-tight">
              {counterpartName || (counterpartRole === 'doctor' ? 'Assigned Doctor' : 'Patient')}
            </h4>
            <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
              <span
                className={`h-1.5 w-1.5 rounded-full ${
                  wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'
                }`}
              />
              <span>{wsConnected ? 'Live Channel Active' : 'Connecting channel...'}</span>
            </div>
          </div>
        </div>

        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded-lg bg-white/5"
          >
            Close
          </button>
        )}
      </div>

      {/* Message History List */}
      <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-slate-950/40">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 text-xs gap-2">
            <Loader2 className="h-5 w-5 animate-spin text-teal-400" />
            <span>Loading conversation messages...</span>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-slate-500 text-xs py-8">
            <MessageSquare className="h-8 w-8 text-slate-600 mb-2" />
            <p className="font-medium text-slate-400">No data yet.</p>
            <p className="text-[11px] text-slate-600 mt-1 max-w-xs">
              Direct clinical communication channel between patient and assigned doctor.
            </p>
          </div>
        ) : (
          messages.map((msg) => {
            const isMe =
              msg.sender?.id === user?.id ||
              msg.sender_id === user?.id ||
              msg.sender?.username === user?.username

            return (
              <div
                key={msg.id}
                className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}
              >
                <div className="flex items-baseline gap-1.5 mb-1 px-1">
                  <span className="text-[10px] font-semibold text-slate-400">
                    {isMe ? 'You' : msg.sender?.username || msg.sender_name}
                  </span>
                  <span className="text-[9px] text-slate-500 font-mono">
                    {new Date(msg.created_at).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>

                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed break-words shadow-md ${
                    isMe
                      ? 'bg-teal-600 text-white rounded-tr-none'
                      : 'bg-slate-900 border border-white/10 text-slate-100 rounded-tl-none'
                  }`}
                >
                  <p>{msg.content}</p>
                </div>

                {isMe && (
                  <div className="flex items-center gap-1 mt-0.5 px-1 text-[10px] text-slate-500">
                    {msg.is_read ? (
                      <span className="flex items-center gap-0.5 text-teal-400">
                        <CheckCheck className="h-3 w-3" />
                        <span>Read</span>
                      </span>
                    ) : (
                      <span className="flex items-center gap-0.5">
                        <Check className="h-3 w-3" />
                        <span>Sent</span>
                      </span>
                    )}
                  </div>
                )}
              </div>
            )
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Message Input Box */}
      <form
        onSubmit={handleSendMessage}
        className="p-3 border-t border-white/10 bg-slate-900/80 flex items-center gap-2"
      >
        <input
          type="text"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Type secure clinical message..."
          maxLength={4000}
          className="flex-1 h-10 px-3.5 rounded-xl bg-slate-950 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 transition-colors"
        />
        <button
          type="submit"
          disabled={!content.trim() || sending}
          className="h-10 px-4 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs transition-colors flex items-center justify-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
        >
          {sending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <>
              <Send className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Send</span>
            </>
          )}
        </button>
      </form>
    </div>
  )
}
