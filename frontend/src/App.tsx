import React, { useState } from 'react'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import { ToastProvider } from '@/context/ToastContext'
import { WebSocketProvider, useWebSocket } from '@/context/WebSocketContext'
import { LoginView } from '@/views/LoginView'
import { PatientDashboardView } from '@/views/PatientDashboardView'
import { DoctorDashboardView } from '@/views/DoctorDashboardView'
import { HealthLogView } from '@/views/HealthLogView'
import { MedicationsView } from '@/views/MedicationsView'
import { WoundView } from '@/views/WoundView'
import { AlertsView } from '@/views/AlertsView'
import { ChatView } from '@/views/ChatView'
import { SettingsView } from '@/views/SettingsView'
import { LeftSidebar, type NavTab } from '@/components/layout/LeftSidebar'
import { TopBar } from '@/components/layout/TopBar'
import { Loader2 } from 'lucide-react'

const AuthenticatedApp: React.FC = () => {
  const { user } = useAuth()
  const { unreadCount } = useWebSocket()
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard')

  const renderActiveView = () => {
    switch (activeTab) {
      case 'dashboard':
        return user?.role === 'doctor' ? (
          <DoctorDashboardView />
        ) : (
          <PatientDashboardView />
        )
      case 'health_log':
        return <HealthLogView />
      case 'medications':
        return <MedicationsView />
      case 'wound_upload':
        return <WoundView />
      case 'alerts':
        return <AlertsView />
      case 'chat':
        return <ChatView />
      case 'settings':
        return <SettingsView />
      default:
        return user?.role === 'doctor' ? (
          <DoctorDashboardView />
        ) : (
          <PatientDashboardView />
        )
    }
  }

  return (
    <div className="min-h-screen bg-[#080d1a] flex flex-col md:flex-row text-foreground">
      {/* Desktop Left Sidebar */}
      <LeftSidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        unreadAlertsCount={unreadCount}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar onOpenChat={() => setActiveTab('chat')} />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto pb-20 md:pb-8">
          {renderActiveView()}
        </main>
      </div>

      {/* Mobile Bottom Navigation Bar */}
      <nav
        aria-label="Mobile Navigation"
        className="md:hidden fixed bottom-0 left-0 right-0 glass-nav border-t border-white/10 px-2 py-2 flex items-center justify-around z-40"
      >
        <button
          type="button"
          onClick={() => setActiveTab('dashboard')}
          className={`flex flex-col items-center py-1 text-[10px] font-medium ${
            activeTab === 'dashboard' ? 'text-teal-400 font-bold' : 'text-slate-400'
          }`}
        >
          <span>Dashboard</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('health_log')}
          className={`flex flex-col items-center py-1 text-[10px] font-medium ${
            activeTab === 'health_log' ? 'text-teal-400 font-bold' : 'text-slate-400'
          }`}
        >
          <span>Logs</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('medications')}
          className={`flex flex-col items-center py-1 text-[10px] font-medium ${
            activeTab === 'medications' ? 'text-teal-400 font-bold' : 'text-slate-400'
          }`}
        >
          <span>Meds</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('wound_upload')}
          className={`flex flex-col items-center py-1 text-[10px] font-medium ${
            activeTab === 'wound_upload' ? 'text-teal-400 font-bold' : 'text-slate-400'
          }`}
        >
          <span>Wounds</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('chat')}
          className={`flex flex-col items-center py-1 text-[10px] font-medium ${
            activeTab === 'chat' ? 'text-teal-400 font-bold' : 'text-slate-400'
          }`}
        >
          <span>Chat</span>
        </button>
      </nav>
    </div>
  )
}

const RootApp: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#080d1a] flex flex-col items-center justify-center gap-3 text-slate-400">
        <Loader2 className="h-8 w-8 animate-spin text-teal-400" />
        <p className="text-xs font-medium tracking-wide">Initializing MedNexa Portal...</p>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <LoginView />
  }

  return (
    <WebSocketProvider>
      <AuthenticatedApp />
    </WebSocketProvider>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <RootApp />
      </AuthProvider>
    </ToastProvider>
  )
}
