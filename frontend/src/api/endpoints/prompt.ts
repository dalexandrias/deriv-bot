import { api } from '../client'
import type { PromptVersion, PromptHistoryItem } from '../types'

export const promptApi = {
  getActive: () => api.get<PromptVersion>('/prompt'),
  getHistory: () => api.get<PromptHistoryItem[]>('/prompt/history'),
  getHistoryItem: (versionId: number) => api.get<PromptVersion>(`/prompt/history/${versionId}`),
  update: (data: { content: string; note?: string }) => api.put<PromptVersion>('/prompt', data),
  restore: (versionId: number) => api.post<PromptVersion>(`/prompt/restore/${versionId}`),
}
