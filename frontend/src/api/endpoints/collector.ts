import { api } from '../client'
import type { CollectorStatus } from '../types'

export const collectorApi = {
  getStatus: () => api.get<CollectorStatus>('/collector/status'),
  updateConfig: (config: { symbols?: string[]; timeframes?: string[] }) =>
    api.patch<CollectorStatus>('/collector/config', config),
}
