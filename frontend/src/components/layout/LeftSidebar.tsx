import React from 'react'
import {
  LayoutDashboard,
  ClipboardList,
  Pill,
  Camera,
  AlertTriangle,
  MessageSquare,
  Settings,
  HeartPulse,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'

export type NavTab =
  | 'dashboard'
  | 'health_log'
  | 'medications'
  | 'wound_upload'
  | 'alerts'
  | 'chat'
  | 'settings'

interface LeftSidebarProps {
  activeTab: NavTab
  onSelectTab: (tab: NavTab) => void
  unreadAlertsCount?: number
  unreadChatCount?: number
}

export const LeftSidebar: React.FC<LeftSidebarProps> = ({
  activeTab,
  onSelectTab,
  unreadAlertsCount = 0,
  unreadChatCount = 0,
}) => {
  const { user } = useAuth()
  const isDoctor = user?.role === 'doctor'

  const navItems: { id: NavTab; label: string; icon: React.ReactNode; badge?: number }[] = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: <LayoutDashboard className="h-4 w-4" />,
    },
    {
      id: 'health_log',
      label: isDoctor ? 'Patient Health Logs' : 'Health Log',
      icon: <ClipboardList className="h-4 w-4" />,
    },
    {
      id: 'medications',
      label: isDoctor ? 'Prescribe & Doses' : 'Medications',
      icon: <Pill className="h-4 w-4" />,
    },
    {
      id: 'wound_upload',
      label: isDoctor ? 'Wound Images' : 'Wound Upload',
      icon: <Camera className="h-4 w-4" />,
    },
    {
      id: 'alerts',
      label: 'Alerts',
      icon: <AlertTriangle className="h-4 w-4" />,
      badge: unreadAlertsCount > 0 ? unreadAlertsCount : undefined,
    },
    {
      id: 'chat',
      label: 'Chat',
      icon: <MessageSquare className="h-4 w-4" />,
      badge: unreadChatCount > 0 ? unreadChatCount : undefined,
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: <Settings className="h-4 w-4" />,
    },
  ]

  return (
    <aside className="w-64 h-screen sticky top-0 shrink-0 glass-nav border-r border-white/5 flex flex-col justify-between p-4 hidden md:flex z-40">
      <div>
        {/* Logo / Brand Header */}
        <div className="flex items-center gap-3 px-2 py-3 mb-6">
          <div className="h-10 w-10 rounded-xl bg-teal-500/15 border border-teal-500/30 flex items-center justify-center text-teal-400 shadow-lg shadow-teal-500/10">
            <HeartPulse className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-base font-bold tracking-tight text-white">MEDIC</span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-teal-500/20 text-teal-300">
                PRO
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Post-Surgery Care</p>
          </div>
        </div>

        {/* Navigation items */}
        <nav className="space-y-1.5" aria-label="Main Navigation">
          {navItems.map((item) => {
            const isActive = activeTab === item.id
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-teal-500/15 text-teal-300 border border-teal-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-white/5 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className={isActive ? 'text-teal-400' : 'text-slate-400'}>
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </div>
                {item.badge !== undefined && (
                  <span className="px-1.5 py-0.5 rounded-full text-[10px] font-mono bg-red-500 text-white font-semibold">
                    {item.badge}
                  </span>
                )}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Role / Session Box */}
      <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 text-xs">
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span>Active Role</span>
          <span className="capitalize font-mono text-teal-400">{user?.role}</span>
        </div>
        <p className="text-white font-medium mt-1 truncate">{user?.username}</p>
        {user?.patient_profile_id && (
          <p className="text-[10px] text-slate-500 font-mono mt-0.5">
            Profile #{user.patient_profile_id}
          </p>
        )}
      </div>
    </aside>
  )
}
