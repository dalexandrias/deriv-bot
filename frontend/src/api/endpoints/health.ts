import { api } from '../client'
import type { HealthStatus } from '../types'

export const healthApi = {
  check: () => api.get<HealthStatus>('/health'),
}
