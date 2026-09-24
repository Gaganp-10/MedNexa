import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react'
import { WS_BASE_URL } from '@/config/env'
import { getAccessToken, refreshAccessToken } from '@/api/client'
import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/context/ToastContext'
import type {
  WsDoctorAlertPayload,
  WsMedicationReminderPayload,
  WsPatientChatNotificationPayload,
} from '@/types/api'

export type NotificationEvent =
  | { type: 'doctor_alert'; data: WsDoctorAlertPayload; id: string; timestamp: Date; read: boolean }
  | { type: 'medication_reminder'; data: WsMedicationReminderPayload; id: string; timestamp: Date; read: boolean }
  | { type: 'chat_notification'; data: WsPatientChatNotificationPayload; id: string; timestamp: Date; read: boolean }

interface WebSocketContextType {
  isConnected: boolean
  notifications: NotificationEvent[]
  unreadCount: number
  markAsRead: (id: string) => void
  markAllAsRead: () => void
  clearNotifications: () => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isAuthenticated } = useAuth()
  const { toast } = useToast()
  const [isConnected, setIsConnected] = useState<boolean>(false)
  const [notifications, setNotifications] = useState<NotificationEvent[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const markAsRead = useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    )
  }, [])

  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
  }, [])

  const clearNotifications = useCallback(() => {
    setNotifications([])
  }, [])

  const unreadCount = notifications.filter((n) => !n.read).length

  useEffect(() => {
    if (!isAuthenticated || !user) {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      setIsConnected(false)
      return
    }

    let isDisposed = false

    const connectWebSocket = async () => {
      let token = getAccessToken()
      if (!token) {
        token = await refreshAccessToken()
      }
      if (!token || isDisposed) return

      let wsUrl = ''
      if (user.role === 'doctor') {
        // ws://<backend-host>:8000/ws/alerts/?token=<access_token>
        wsUrl = `${WS_BASE_URL}/ws/alerts/?token=${token}`
      } else if (user.role === 'patient') {
        // ws://<backend-host>:8000/ws/notifications/?token=<access_token>
        wsUrl = `${WS_BASE_URL}/ws/notifications/?token=${token}`
      }

      if (!wsUrl) return

      try {
        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => {
          if (!isDisposed) {
            setIsConnected(true)
          }
        }

        ws.onmessage = (event) => {
          try {
            const raw = JSON.parse(event.data)
            const id = `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`

            if (user.role === 'doctor') {
              const alertData = raw as WsDoctorAlertPayload
              const newNotification: NotificationEvent = {
                type: 'doctor_alert',
                data: alertData,
                id,
                timestamp: new Date(alertData.created_at || Date.now()),
                read: false,
              }
              setNotifications((prev) => [newNotification, ...prev])

              toast({
                title: `Alert: ${alertData.patient_display_name || 'Patient'}`,
                description: alertData.message,
                variant: alertData.severity === 'high' ? 'danger' : 'alert',
              })
            } else if (user.role === 'patient') {
              if (raw.type === 'medication_reminder') {
                const medData = raw as WsMedicationReminderPayload
                const newNotification: NotificationEvent = {
                  type: 'medication_reminder',
                  data: medData,
                  id,
                  timestamp: new Date(medData.created_at || Date.now()),
                  read: false,
                }
                setNotifications((prev) => [newNotification, ...prev])

                toast({
                  title: `Medication Reminder: ${medData.medicine_name}`,
                  description: medData.message,
                  variant: 'alert',
                })
              } else if (raw.type === 'chat_message') {
                const chatData = raw as WsPatientChatNotificationPayload
                const newNotification: NotificationEvent = {
                  type: 'chat_notification',
                  data: chatData,
                  id,
                  timestamp: new Date(chatData.created_at || Date.now()),
                  read: false,
                }
                setNotifications((prev) => [newNotification, ...prev])

                toast({
                  title: `Message from ${chatData.sender_name}`,
                  description: chatData.preview,
                  variant: 'default',
                })
              }
            }
          } catch {
            // Ignore unparseable frames
          }
        }

        ws.onclose = (event) => {
          if (!isDisposed) {
            setIsConnected(false)
            // Reconnect if not closed intentionally or unauthorized (4401/4403)
            if (event.code !== 4401 && event.code !== 4403 && event.code !== 1000) {
              reconnectTimeoutRef.current = setTimeout(() => {
                if (!isDisposed) connectWebSocket()
              }, 4000)
            }
          }
        }

        ws.onerror = () => {
          // Handled by onclose
        }
      } catch {
        // Fallback reconnection
        if (!isDisposed) {
          reconnectTimeoutRef.current = setTimeout(() => {
            if (!isDisposed) connectWebSocket()
          }, 4000)
        }
      }
    }

    connectWebSocket()

    return () => {
      isDisposed = true
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close(1000)
        wsRef.current = null
      }
      setIsConnected(false)
    }
  }, [user, isAuthenticated, toast])

  return (
    <WebSocketContext.Provider
      value={{
        isConnected,
        notifications,
        unreadCount,
        markAsRead,
        markAllAsRead,
        clearNotifications,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocket() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}
