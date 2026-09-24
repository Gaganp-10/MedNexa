/**
 * Centralized Application Environment Configuration
 * Single source of truth for REST API base URL and WebSocket host.
 * Never hardcode these anywhere else in the application.
 */

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
).replace(/\/+$/, '')

export const WS_BASE_URL = (
  import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'
).replace(/\/+$/, '')

export const CLINICAL_SAFETY_DISCLAIMER =
  'MedNexa is a decision-support prototype, not a diagnostic tool. All indicators require clinical review.'
