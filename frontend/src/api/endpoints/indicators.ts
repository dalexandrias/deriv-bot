import { api } from '../client'
import type { IndicatorConfig } from '../types'

export const indicatorsApi = {
  list: () => api.get<IndicatorConfig[]>('/indicators/'),
  create: (data: Omit<IndicatorConfig, 'id' | 'created_at' | 'updated_at'>) =>
    api.post<IndicatorConfig>('/indicators/', data),
  update: (id: number, data: Partial<IndicatorConfig>) =>
    api.patch<IndicatorConfig>(`/indicators/${id}`, data),
  delete: (id: number) => api.delete<void>(`/indicators/${id}`),
  resetDefaults: () => api.post<void>('/indicators/reset-defaults'),
}
