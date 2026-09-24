/**
 * Strict TypeScript API definitions matching FRONTEND.md and backend serializers.
 * Never invent fields or alter response contracts.
 */

export interface TokenResponse {
  access: string
  refresh: string
}

export interface RefreshTokenResponse {
  access: string
}

export interface AssignedDoctor {
  id: number
  name: string
}

export interface AuthMeResponse {
  id: number
  username: string
  role: 'doctor' | 'patient'
  patient_profile_id?: number | null
  doctor_profile_id?: number | null
  assigned_doctor?: AssignedDoctor | null
}

export interface PatientSelfProfile {
  id: number
  username: string
  role: 'patient'
  patient_profile_id: number
  surgery_type: string
  surgery_date: string
  assigned_doctor: AssignedDoctor | null
}

export interface HealthLogSummary {
  id: number
  created_at: string
  temperature: number
  pain_level: number
  swelling: boolean
  recovery_score: number
}

export interface WoundSummary {
  id: number
  uploaded_at: string
  analysis_result: string
  file_url: string
}

export interface MedicationAdherenceSummary {
  total_prescribed: number
  total_scheduled_due: number
  doses_taken: number
  doses_missed: number
  doses_recorded_taken?: number
  adherence_percentage: number
  reporting_window_days?: number
  window_start?: string
  window_end?: string
  pending_count?: number
  taken_count?: number
  missed_count?: number
  total_scheduled?: number
}

export interface DoctorOverviewPatientSummary {
  patient_id: number
  user_id: number
  username: string
  full_name: string
  surgery_type: string
  surgery_date: string
  latest_recovery_score: number
  latest_risk_indicator: string
  alert_count: number
  latest_health_log: HealthLogSummary | null
  latest_wound_upload: WoundSummary | null
  medication_adherence: MedicationAdherenceSummary
}

export interface DoctorOverviewResponse {
  doctor_id: number
  doctor_name: string
  total_patients: number
  patients: DoctorOverviewPatientSummary[]
}

export interface DoctorPatientRecord {
  id: number // PatientProfile.id
  user: {
    id: number
    username: string
    first_name: string
    last_name: string
    role: string
  }
  surgery_type: string
  surgery_date: string
  doctor: number
}

export interface DailyHealthLog {
  id: number
  patient: number
  temperature: number
  pain_level: number
  swelling: boolean
  medication_taken: boolean
  notes: string
  recovery_score: number
  created_at: string
}

export interface CreateHealthLogPayload {
  temperature: number
  pain_level: number
  swelling: boolean
  medication_taken: boolean
  notes?: string
}

export interface WoundImage {
  id: number
  patient: number
  image?: string
  analysis_result: string
  uploaded_at: string
  file_url: string
}

export interface AlertItem {
  id: number
  patient?: number
  message: string
  severity: 'low' | 'medium' | 'high'
  is_read?: boolean
  created_at: string
}

export interface RecoveryTrendItem {
  date: string
  score: number
}

export interface RiskPredictionResponse {
  patient_id: number
  risk_prediction: string
  has_health_logs: boolean
  has_wound_images: boolean
}

export interface MedicationDose {
  id: number
  medication_id: number
  medicine_name: string
  dosage: string
  scheduled_for: string
  status: 'scheduled' | 'taken' | 'missed'
  taken_at: string | null
  reminder_sent_at: string | null
  created_at: string
}

export interface MedicationItem {
  id: number
  patient: number
  medicine_name: string
  dosage: string
  time: string
  taken_status: boolean
  created_at: string
}

export interface CreateMedicationPayload {
  patient_id: number
  medicine_name: string
  dosage: string
  time: string // format "HH:MM:SS" or "HH:MM"
}

export interface ConversationParticipant {
  id: number
  username: string
  full_name?: string
  role: string
}

export interface ConversationItem {
  id: number
  doctor: {
    id: number
    username: string
    first_name: string
    last_name: string
  }
  patient: {
    id: number
    user: {
      id: number
      username: string
      first_name: string
      last_name: string
    }
    surgery_type: string
  }
  created_at: string
  updated_at: string
  latest_message?: {
    id: number
    content: string
    created_at: string
    sender_id: number
    is_read: boolean
  } | null
}

export interface ChatMessage {
  id: number
  conversation?: number
  conversation_id?: number
  sender: {
    id: number
    username: string
    role: string
  }
  sender_id?: number
  sender_name?: string
  sender_role?: 'doctor' | 'patient'
  content: string
  is_read: boolean
  created_at: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// WebSocket Payloads
export interface WsDoctorAlertPayload {
  id: number
  patient_id: number
  patient_display_name: string
  severity: 'low' | 'medium' | 'high'
  message: string
  created_at: string
}

export interface WsMedicationReminderPayload {
  type: 'medication_reminder'
  dose_id: number
  medicine_name: string
  dosage: string
  scheduled_time: string
  message: string
  created_at: string
}

export interface WsPatientChatNotificationPayload {
  type: 'chat_message'
  conversation_id: number
  message_id: number
  sender_name: string
  preview: string
  created_at: string
}

export interface WsChatMessageBroadcast {
  id: number
  conversation_id: number
  sender_id: number
  sender_name: string
  sender_role: 'doctor' | 'patient'
  content: string
  is_read: boolean
  created_at: string
}
