import React, { useState } from 'react'
import {
  Bell,
  Search,
  LogOut,
  Radio,
  Check,
  Trash2,
  AlertTriangle,
  Pill,
  MessageSquare,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useWebSocket } from '@/context/WebSocketContext'

interface TopBarProps {
  onSearch?: (query: string) => void
  onOpenChat?: () => void
}

export const TopBar: React.FC<TopBarProps> = ({ onSearch, onOpenChat }) => {
  const { user, logout } = useAuth()
  const {
    isConnected,
    notifications,
    unreadCount,
    markAsRead,
    markAllAsRead,
    clearNotifications,
  } = useWebSocket()
  const [showNotifications, setShowNotifications] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value)
    if (onSearch) onSearch(e.target.value)
  }

  return (
    <header className="h-16 w-full glass-nav border-b border-white/5 px-4 md:px-6 flex items-center justify-between gap-4 sticky top-0 z-30">
      {/* Search Bar */}
      <div className="flex-1 max-w-md">
        <div className="relative">
          <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search records, logs, medications..."
            value={searchQuery}
            onChange={handleSearchChange}
            className="w-full h-9 pl-9 pr-4 rounded-xl bg-slate-900/60 border border-white/10 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-teal-500/50 transition-colors"
          />
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Real-time WS connection status */}
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono border ${
            isConnected
              ? 'bg-teal-500/10 border-teal-500/30 text-teal-300'
              : 'bg-slate-800 border-white/10 text-slate-400'
          }`}
          title={
            isConnected
              ? 'Connected to real-time WebSocket channel'
              : 'Connecting to WebSocket...'
          }
        >
          <span
            className={`h-2 w-2 rounded-full ${
              isConnected ? 'bg-teal-400 animate-pulse' : 'bg-slate-500'
            }`}
          />
          <span className="hidden sm:inline">
            {isConnected ? 'Real-Time Sync' : 'Offline'}
          </span>
        </div>

        {/* Real-time Notification Bell Popover */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowNotifications(!showNotifications)}
            aria-label="View notifications"
            className="relative p-2 rounded-xl bg-slate-900/60 border border-white/10 text-slate-300 hover:text-white hover:border-white/20 transition-colors"
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 h-4 min-w-[16px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center border border-slate-900">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl glass-card border border-white/10 shadow-2xl p-4 z-50 animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between pb-3 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <h4 className="text-xs font-semibold text-white">Live Channel Feed</h4>
                  {unreadCount > 0 && (
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-teal-500/20 text-teal-300 font-mono">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-[11px]">
                  {unreadCount > 0 && (
                    <button
                      type="button"
                      onClick={markAllAsRead}
                      className="text-teal-400 hover:underline flex items-center gap-1"
                    >
                      <Check className="h-3 w-3" /> Mark all read
                    </button>
                  )}
                  {notifications.length > 0 && (
                    <button
                      type="button"
                      onClick={clearNotifications}
                      className="text-slate-400 hover:text-red-400"
                      title="Clear notifications"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  )}
                </div>
              </div>

              <div className="mt-3 space-y-2 max-h-72 overflow-y-auto pr-1">
                {notifications.length === 0 ? (
                  <div className="text-center py-6 text-xs text-slate-500">
                    No data yet.
                    <p className="text-[10px] text-slate-600 mt-0.5">
                      Real-time events will stream here live.
                    </p>
                  </div>
                ) : (
                  notifications.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => markAsRead(item.id)}
                      className={`p-2.5 rounded-xl border text-xs cursor-pointer transition-colors ${
                        item.read
                          ? 'bg-slate-900/30 border-white/5 text-slate-400'
                          : 'bg-slate-900/80 border-teal-500/30 text-slate-200'
                      }`}
                    >
                      <div className="flex items-start gap-2.5">
                        <div className="mt-0.5 shrink-0">
                          {item.type === 'doctor_alert' && (
                            <AlertTriangle
                              className={`h-4 w-4 ${
                                item.data.severity === 'high'
                                  ? 'text-red-400'
                                  : 'text-amber-400'
                              }`}
                            />
                          )}
                          {item.type === 'medication_reminder' && (
                            <Pill className="h-4 w-4 text-teal-400" />
                          )}
                          {item.type === 'chat_notification' && (
                            <MessageSquare className="h-4 w-4 text-teal-400" />
                          )}
                        </div>
                        <div className="flex-1">
                          <p className="font-semibold text-white">
                            {item.type === 'doctor_alert' &&
                              `Alert: ${item.data.patient_display_name}`}
                            {item.type === 'medication_reminder' &&
                              `Reminder: ${item.data.medicine_name}`}
                            {item.type === 'chat_notification' &&
                              `Message: ${item.data.sender_name}`}
                          </p>
                          <p className="mt-0.5 text-[11px] opacity-90 line-clamp-2">
                            {item.type === 'doctor_alert' && item.data.message}
                            {item.type === 'medication_reminder' && item.data.message}
                            {item.type === 'chat_notification' && item.data.preview}
                          </p>
                          <span className="text-[10px] text-slate-500 font-mono mt-1 block">
                            {item.timestamp.toLocaleTimeString()}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Profile & Logout */}
        <div className="flex items-center gap-2 pl-2 border-l border-white/10">
          <div className="flex flex-col text-right hidden sm:block">
            <span className="text-xs font-semibold text-white leading-tight">
              {user?.username}
            </span>
            <span className="text-[10px] uppercase font-mono tracking-wider text-teal-400">
              {user?.role}
            </span>
          </div>
          <button
            type="button"
            onClick={logout}
            title="Log out"
            className="p-2 rounded-xl bg-slate-900/60 border border-white/10 text-slate-400 hover:text-red-400 hover:border-red-500/30 transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  )
}
