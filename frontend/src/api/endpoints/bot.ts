import { api } from '../client'
import type { BotStatus, BotConfig } from '../types'

export const botApi = {
  getStatus: () => api.get<BotStatus>('/bot/status'),
  getConfig: () => api.get<BotConfig>('/bot/config'),
  updateConfig: (config: Partial<BotConfig>) => api.patch<BotConfig>('/bot/config', config),
  start: () => api.post<BotStatus>('/bot/start'),
  stop: () => api.post<BotStatus>('/bot/stop'),
}
