import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import MDEditor from '@uiw/react-md-editor'
import '@uiw/react-md-editor/markdown-editor.css'
import { toast } from 'sonner'
import * as Dialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'
import { promptApi } from '@/api/endpoints/prompt'
import type { PromptHistoryItem } from '@/api/types'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

export function PromptEditor() {
  const [content, setContent] = useState('')
  const [note, setNote] = useState('')
  const [selectedHistoryId, setSelectedHistoryId] = useState<number | null>(null)
  const [showHistoryDetail, setShowHistoryDetail] = useState(false)
  const queryClient = useQueryClient()

  const { data: activePrompt } = useQuery({
    queryKey: ['prompt', 'active'],
    queryFn: () => promptApi.getActive(),
  })

  const { data: history = [] } = useQuery({
    queryKey: ['prompt', 'history'],
    queryFn: () => promptApi.getHistory(),
  })

  const { data: selectedHistoryDetail } = useQuery({
    queryKey: ['prompt', 'history', selectedHistoryId],
    queryFn: () =>
      selectedHistoryId ? promptApi.getHistoryItem(selectedHistoryId) : Promise.resolve(null),
    enabled: !!selectedHistoryId,
  })

  const updateMutation = useMutation({
    mutationFn: () => promptApi.update({ content, note }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompt'] })
      toast.success('Prompt atualizado com sucesso')
      setContent(activePrompt?.content || '')
      setNote('')
    },
    onError: () => toast.error('Erro ao atualizar prompt'),
  })

  const restoreMutation = useMutation({
    mutationFn: (versionId: number) => promptApi.restore(versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompt'] })
      toast.success('Prompt restaurado com sucesso')
      setShowHistoryDetail(false)
      setSelectedHistoryId(null)
    },
    onError: () => toast.error('Erro ao restaurar prompt'),
  })

  const hasChanges = activePrompt && content !== activePrompt.content

  const handleReset = () => {
    setContent(activePrompt?.content || '')
    setNote('')
  }

  const handleSelectHistory = (historyItem: PromptHistoryItem) => {
    setSelectedHistoryId(historyItem.id)
    setShowHistoryDetail(true)
  }

  const currentContent = content || activePrompt?.content || ''

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-4">
          <div className="space-y-2">
            <h2 className="text-lg font-semibold text-lumen-text">Editor de Prompt</h2>
            {activePrompt && (
              <p className="text-sm text-lumen-muted">
                Atualizado em {format(new Date(activePrompt.created_at), 'PPP HH:mm', { locale: ptBR })}
                {activePrompt.note && ` • ${activePrompt.note}`}
              </p>
            )}
          </div>

          <div className="border border-lumen-border rounded-lumen overflow-hidden" data-color-mode="light">
            <MDEditor
              value={currentContent}
              onChange={(val) => setContent(val || '')}
              preview="live"
              height={500}
              visibleDragbar={false}
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-lumen-text">Nota (opcional)</label>
            <input
              type="text"
              placeholder="Descreva a mudança (ex: ajuste de confiança mínima)"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-lumen-border rounded-lumen-sm bg-lumen-bg text-lumen-text placeholder:text-lumen-faint focus:outline-none focus:ring-2 focus:ring-lumen-primary focus:border-lumen-primary hover:border-lumen-border-strong transition-colors"
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => updateMutation.mutate()}
              disabled={!hasChanges || updateMutation.isPending}
              className="flex-1 px-4 py-2 rounded-lumen-sm text-sm font-medium bg-lumen-primary text-white hover:bg-lumen-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {updateMutation.isPending ? 'Salvando...' : 'Salvar nova versão'}
            </button>
            <button
              onClick={handleReset}
              disabled={!hasChanges}
              className="px-4 py-2 rounded-lumen-sm text-sm font-medium bg-lumen-surface border border-lumen-border-strong text-lumen-body hover:bg-lumen-surface-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Descartar
            </button>
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-lumen-text">Histórico (últimas 10)</h3>
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {history.map((item) => (
              <button
                key={item.id}
                onClick={() => handleSelectHistory(item)}
                className="w-full text-left p-3 rounded-lumen-sm border border-lumen-border bg-lumen-surface hover:bg-lumen-surface-2 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-lumen-text">
                      v{item.id}
                      {item.is_active && (
                        <span className="ml-2 inline-block text-xs bg-lumen-success-bg text-lumen-success px-2 py-0.5 rounded">
                          Ativa
                        </span>
                      )}
                    </p>
                    {item.note && <p className="text-xs text-lumen-muted mt-1">{item.note}</p>}
                    <p className="text-xs text-lumen-faint mt-1">
                      {format(new Date(item.created_at), 'PPP HH:mm', { locale: ptBR })}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      <Dialog.Root open={showHistoryDetail} onOpenChange={setShowHistoryDetail}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50" />
          <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-lumen-bg border border-lumen-border rounded-lumen shadow-lumen p-6 max-w-2xl max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-lumen-text">Versão {selectedHistoryId}</h2>
              <Dialog.Close asChild>
                <button className="p-1 hover:bg-lumen-surface rounded transition-colors">
                  <X size={20} className="text-lumen-muted" />
                </button>
              </Dialog.Close>
            </div>

            {selectedHistoryDetail && (
              <div className="space-y-4">
                <div
                  className="border border-lumen-border rounded-lumen-sm overflow-hidden bg-lumen-surface p-4"
                  data-color-mode="light"
                >
                  <MDEditor.Markdown source={selectedHistoryDetail.content} />
                </div>

                <div className="flex gap-2 justify-end pt-4 border-t border-lumen-border">
                  <button
                    onClick={() => setShowHistoryDetail(false)}
                    className="px-4 py-2 rounded-lumen-sm text-sm font-medium bg-lumen-surface border border-lumen-border-strong text-lumen-body hover:bg-lumen-surface-2 transition-colors"
                  >
                    Fechar
                  </button>
                  {!selectedHistoryDetail.is_active && (
                    <button
                      onClick={() => restoreMutation.mutate(selectedHistoryDetail.id)}
                      disabled={restoreMutation.isPending}
                      className="px-4 py-2 rounded-lumen-sm text-sm font-medium bg-lumen-primary text-white hover:bg-lumen-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {restoreMutation.isPending ? 'Restaurando...' : 'Restaurar esta versão'}
                    </button>
                  )}
                </div>
              </div>
            )}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  )
}
