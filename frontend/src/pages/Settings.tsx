import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as Tabs from '@radix-ui/react-tabs'
import * as Popover from '@radix-ui/react-popover'
import { HelpCircle } from 'lucide-react'
import { botApi } from '@/api/endpoints/bot'
import { indicatorsApi } from '@/api/endpoints/indicators'
import { collectorApi } from '@/api/endpoints/collector'
import { toast } from 'sonner'
import type { IndicatorConfig } from '@/api/types'
import { PromptEditor } from '@/components/domain/PromptEditor'

// ─── Parameter Help Component ─────────────────────────────────────────────────

function ParamHelp({ title, description }: { title: string; description: string }) {
  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          type="button"
          className="inline-flex items-center justify-center w-4 h-4 ml-1.5 text-lumen-muted hover:text-lumen-body transition-colors rounded-full hover:bg-lumen-surface-2"
          title={title}
        >
          <HelpCircle size={14} />
        </button>
      </Popover.Trigger>
      <Popover.Content className="bg-lumen-surface border border-lumen-border rounded-lumen p-3 shadow-lumen z-50 max-w-xs" side="right" sideOffset={8}>
        <div className="space-y-2">
          <p className="text-xs font-medium text-lumen-text">{title}</p>
          <p className="text-xs text-lumen-muted leading-relaxed">{description}</p>
        </div>
      </Popover.Content>
    </Popover.Root>
  )
}

// ─── Bot Tab ──────────────────────────────────────────────────────────────────

function BotTab() {
  const qc = useQueryClient()
  const { data: config = {} } = useQuery({
    queryKey: ['bot', 'config'],
    queryFn: botApi.getConfig,
  })
  const { data: status } = useQuery({
    queryKey: ['bot', 'status'],
    queryFn: botApi.getStatus,
    refetchInterval: 5000,
  })

  const [form, setForm] = useState<Record<string, string>>({})
  const dirty = { ...config, ...form }

  const updateMut = useMutation({
    mutationFn: () =>
      botApi.updateConfig(
        Object.fromEntries(
          Object.entries(form).map(([k, v]) => [k, isNaN(Number(v)) ? v : Number(v)])
        )
      ),
    onSuccess: () => {
      toast.success('Configurações salvas')
      setForm({})
      qc.invalidateQueries({ queryKey: ['bot', 'config'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const startMut = useMutation({
    mutationFn: botApi.start,
    onSuccess: () => {
      toast.success('Bot iniciado')
      qc.invalidateQueries({ queryKey: ['bot', 'status'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const stopMut = useMutation({
    mutationFn: botApi.stop,
    onSuccess: () => {
      toast.success('Bot parado')
      qc.invalidateQueries({ queryKey: ['bot', 'status'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const isRunning = status?.running === true

  const fields = [
    {
      key: 'symbol',
      label: 'Símbolo',
      description: 'Símbolo do ativo para análise e operações',
      detail: 'Exemplo: R_25, R_50, R_100. Define qual mercado o bot monitora e opera.',
    },
    {
      key: 'decision_timeframe',
      label: 'Timeframe Decisão',
      description: 'Timeframe principal para análise técnica',
      detail: 'O bot analisa velas deste período para tomar decisões de entrada. Exemplo: 5m, 15m, 1h.',
    },
    {
      key: 'context_timeframe',
      label: 'Timeframe Contexto',
      description: 'Timeframe secundário para contexto de mercado',
      detail: 'Usado para entender a tendência maior antes de operar no timeframe de decisão. Deve ser maior que o timeframe de decisão.',
    },
    {
      key: 'loop_interval',
      label: 'Intervalo (s)',
      description: 'Intervalo entre cada ciclo do bot',
      detail: 'Define com que frequência o bot analisa o mercado. Valor menor = mais análises por hora.',
    },
    {
      key: 'duration',
      label: 'Duração Operação (s)',
      description: 'Duração de cada operação aberta',
      detail: 'Após este tempo em segundos, a posição é encerrada automaticamente.',
    },
    {
      key: 'min_confidence',
      label: 'Confiança Mínima',
      description: 'Confiança mínima para emitir sinal',
      detail: 'Valor de 0 a 1. Alto (ex: 0.8) = sinais mais seletivos. Baixo (ex: 0.5) = mais operações, menor precisão.',
    },
    {
      key: 'model',
      label: 'Modelo LLM',
      description: 'Modelo de linguagem para análise e decisão',
      detail: 'Define qual LLM será usado para analisar indicadores e decidir a direção da operação.',
    },
    {
      key: 'candle_settle_delay',
      label: 'Delay Vela (s)',
      description: 'Tempo de espera após fechamento da vela',
      detail: 'Garante que todos os dados da vela estejam disponíveis antes da análise começar.',
    },
    {
      key: 'candles_count',
      label: 'Qtd. Velas',
      description: 'Quantidade de velas históricas para análise',
      detail: 'Mais velas = mais contexto, mas mais tokens usados pelo LLM. Valor típico: 60.',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Start/stop */}
      <div className="bg-lumen-surface border border-lumen-border rounded-lumen p-5 shadow-lumen flex items-center justify-between">
        <div>
          <div className="font-medium text-lumen-text text-sm">Controle do Bot</div>
          <div className="text-xs text-lumen-muted mt-0.5">
            Status: <span className="font-mono">{status?.running ? 'Rodando' : status != null ? 'Parado' : '—'}</span>
            {status?.uptime != null && status.uptime > 0 && (
              <span className="ml-2 text-lumen-faint">uptime {Math.floor(status.uptime / 60)}min</span>
            )}
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => startMut.mutate()}
            disabled={isRunning || startMut.isPending}
            className="px-4 py-2 rounded-lumen-sm text-sm font-medium bg-lumen-primary text-white hover:bg-lumen-primary-hover disabled:opacity-50 transition-colors"
          >
            Iniciar
          </button>
          <button
            onClick={() => stopMut.mutate()}
            disabled={!isRunning || stopMut.isPending}
            className="px-4 py-2 rounded-lumen-sm text-sm font-medium bg-lumen-surface border border-lumen-border-strong text-lumen-body hover:bg-lumen-surface-2 disabled:opacity-50 transition-colors"
          >
            Parar
          </button>
        </div>
      </div>

      {/* Config form */}
      <div className="bg-lumen-surface border border-lumen-border rounded-lumen p-5 shadow-lumen">
        <h2 className="text-xs tracking-[0.08em] uppercase text-lumen-muted font-medium mb-4">Parâmetros</h2>
        <div className="grid grid-cols-2 gap-4">
          {fields.map(({ key, label, description, detail }) => (
            <div key={key}>
              <div className="flex items-center mb-1">
                <label className="block text-xs text-lumen-muted">{label}</label>
                <ParamHelp title={description} description={detail} />
              </div>
              <input
                type="text"
                className="w-full px-3 py-2 text-sm font-mono border border-lumen-border rounded-lumen-sm bg-lumen-bg text-lumen-text placeholder:text-lumen-faint focus:outline-none focus:ring-2 focus:ring-lumen-primary focus:border-lumen-primary hover:border-lumen-border-strong transition-colors"
                value={form[key] ?? String(dirty[key] ?? '')}
                onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
              />
            </div>
          ))}
        </div>
        <div className="mt-5 flex justify-end">
          <button
            onClick={() => updateMut.mutate()}
            disabled={Object.keys(form).length === 0 || updateMut.isPending}
            className="px-4 py-2 rounded-lumen-sm text-sm font-medium bg-lumen-primary text-white hover:bg-lumen-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {updateMut.isPending ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Indicators Tab ───────────────────────────────────────────────────────────

function IndicatorsTab() {
  const qc = useQueryClient()
  const { data: indicators = [], isLoading } = useQuery({
    queryKey: ['indicators'],
    queryFn: indicatorsApi.list,
  })

  const [showAdd, setShowAdd] = useState(false)
  const [newInd, setNewInd] = useState({
    name: '',
    indicator_type: '',
    parameters: '{}',
    enabled: true,
  })

  const toggleMut = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      indicatorsApi.update(id, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['indicators'] }),
    onError: (e: Error) => toast.error(e.message),
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => indicatorsApi.delete(id),
    onSuccess: () => {
      toast.success('Indicador removido')
      qc.invalidateQueries({ queryKey: ['indicators'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const createMut = useMutation({
    mutationFn: () => {
      let params: Record<string, number>
      try {
        params = JSON.parse(newInd.parameters)
      } catch {
        throw new Error('JSON de parâmetros inválido')
      }
      return indicatorsApi.create({
        name: newInd.name,
        indicator_type: newInd.indicator_type,
        parameters: params,
        enabled: newInd.enabled,
      })
    },
    onSuccess: () => {
      toast.success('Indicador criado')
      setShowAdd(false)
      setNewInd({ name: '', indicator_type: '', parameters: '{}', enabled: true })
      qc.invalidateQueries({ queryKey: ['indicators'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const resetMut = useMutation({
    mutationFn: indicatorsApi.resetDefaults,
    onSuccess: () => {
      toast.success('Indicadores resetados')
      qc.invalidateQueries({ queryKey: ['indicators'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  if (isLoading) return <div className="text-lumen-muted text-sm">Carregando...</div>

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <span className="text-sm text-lumen-muted">{indicators.length} indicadores</span>
        <div className="flex gap-2">
          <button
            onClick={() => resetMut.mutate()}
            className="px-3 py-1.5 text-xs font-medium border border-lumen-border rounded-lumen-sm text-lumen-body bg-lumen-surface hover:bg-lumen-surface-2 transition-colors"
          >
            Resetar padrões
          </button>
          <button
            onClick={() => setShowAdd((v) => !v)}
            className="px-3 py-1.5 text-xs font-medium rounded-lumen-sm bg-lumen-primary text-white hover:bg-lumen-primary-hover transition-colors"
          >
            + Adicionar
          </button>
        </div>
      </div>

      {showAdd && (
        <div className="bg-lumen-surface border border-lumen-border rounded-lumen p-4 shadow-lumen space-y-3">
          <h3 className="text-xs tracking-[0.08em] uppercase text-lumen-muted font-medium">
            Novo Indicador
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-lumen-muted mb-1">Nome</label>
              <input
                className="w-full px-3 py-2 text-sm border border-lumen-border rounded-lumen-sm bg-lumen-bg focus:outline-none focus:ring-2 focus:ring-lumen-primary-ring focus:border-lumen-primary"
                value={newInd.name}
                onChange={(e) => setNewInd((p) => ({ ...p, name: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-xs text-lumen-muted mb-1">
                Tipo (RSI, MACD, BB, EMA, ADX, ATR)
              </label>
              <input
                className="w-full px-3 py-2 text-sm border border-lumen-border rounded-lumen-sm bg-lumen-bg focus:outline-none focus:ring-2 focus:ring-lumen-primary-ring focus:border-lumen-primary"
                value={newInd.indicator_type}
                onChange={(e) => setNewInd((p) => ({ ...p, indicator_type: e.target.value }))}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-lumen-muted mb-1">Parâmetros (JSON)</label>
              <input
                className="w-full px-3 py-2 text-sm font-mono border border-lumen-border rounded-lumen-sm bg-lumen-bg focus:outline-none focus:ring-2 focus:ring-lumen-primary-ring focus:border-lumen-primary"
                value={newInd.parameters}
                onChange={(e) => setNewInd((p) => ({ ...p, parameters: e.target.value }))}
              />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowAdd(false)}
              className="px-3 py-1.5 text-xs border border-lumen-border rounded-lumen-sm text-lumen-body bg-lumen-surface hover:bg-lumen-surface-2"
            >
              Cancelar
            </button>
            <button
              onClick={() => createMut.mutate()}
              disabled={createMut.isPending}
              className="px-3 py-1.5 text-xs rounded-lumen-sm bg-lumen-primary text-white hover:bg-lumen-primary-hover disabled:opacity-50"
            >
              {createMut.isPending ? 'Criando...' : 'Criar'}
            </button>
          </div>
        </div>
      )}

      <div className="bg-lumen-surface border border-lumen-border rounded-lumen overflow-hidden shadow-lumen">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-lumen-surface-2 border-b border-lumen-border">
              {['Nome', 'Tipo', 'Parâmetros', 'Ativo', ''].map((h) => (
                <th
                  key={h}
                  className="text-left text-[11px] tracking-[0.06em] uppercase text-lumen-muted font-medium px-4 py-3"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {indicators.map((ind: IndicatorConfig) => (
              <tr
                key={ind.id}
                className="border-b border-lumen-border last:border-0 hover:bg-lumen-surface-2 transition-colors"
              >
                <td className="px-4 py-3 font-medium text-lumen-text">{ind.name}</td>
                <td className="px-4 py-3 text-lumen-muted">{ind.indicator_type}</td>
                <td className="px-4 py-3 font-mono text-xs text-lumen-muted">
                  {JSON.stringify(ind.parameters)}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => toggleMut.mutate({ id: ind.id, enabled: !ind.enabled })}
                    className={`w-10 h-5 rounded-full transition-colors relative ${
                      ind.enabled ? 'bg-lumen-primary' : 'bg-lumen-border-strong'
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform shadow-lumen-sm ${
                        ind.enabled ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </button>
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => deleteMut.mutate(ind.id)}
                    className="text-xs text-lumen-muted hover:text-lumen-down transition-colors"
                  >
                    Remover
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Collector Tab ────────────────────────────────────────────────────────────

function CollectorTab() {
  const qc = useQueryClient()
  const { data: status } = useQuery({
    queryKey: ['collector', 'status'],
    queryFn: collectorApi.getStatus,
    refetchInterval: 10000,
  })

  const [symbols, setSymbols] = useState('')
  const [timeframes, setTimeframes] = useState('')

  const updateMut = useMutation({
    mutationFn: () => {
      const body: { symbols?: string[]; timeframes?: string[] } = {}
      if (symbols.trim())
        body.symbols = symbols
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
      if (timeframes.trim())
        body.timeframes = timeframes
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean)
      return collectorApi.updateConfig(body)
    },
    onSuccess: () => {
      toast.success('Collector atualizado')
      setSymbols('')
      setTimeframes('')
      qc.invalidateQueries({ queryKey: ['collector'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="space-y-6">
      <div className="bg-lumen-surface border border-lumen-border rounded-lumen p-5 shadow-lumen">
        <h2 className="text-xs tracking-[0.08em] uppercase text-lumen-muted font-medium mb-4">
          Status Atual
        </h2>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="text-xs text-lumen-muted mb-1">Rodando</div>
            <div
              className={`font-mono text-sm font-semibold ${
                status?.running ? 'text-lumen-live' : 'text-lumen-muted'
              }`}
            >
              {status?.running ? 'Sim' : 'Não'}
            </div>
          </div>
          <div>
            <div className="text-xs text-lumen-muted mb-1">Símbolos</div>
            <div className="font-mono text-sm text-lumen-body">
              {status?.symbols?.join(', ') ?? '—'}
            </div>
          </div>
          <div>
            <div className="text-xs text-lumen-muted mb-1">Timeframes</div>
            <div className="font-mono text-sm text-lumen-body">
              {status?.timeframes?.join(', ') ?? '—'}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-lumen-surface border border-lumen-border rounded-lumen p-5 shadow-lumen">
        <h2 className="text-xs tracking-[0.08em] uppercase text-lumen-muted font-medium mb-4">
          Atualizar
        </h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-lumen-muted mb-1">
              Símbolos (separados por vírgula)
            </label>
            <input
              type="text"
              placeholder={status?.symbols?.join(', ') ?? 'R_25, R_50'}
              className="w-full px-3 py-2 text-sm font-mono border border-lumen-border rounded-lumen-sm bg-lumen-bg focus:outline-none focus:ring-2 focus:ring-lumen-primary-ring focus:border-lumen-primary"
              value={symbols}
              onChange={(e) => setSymbols(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs text-lumen-muted mb-1">
              Timeframes (separados por vírgula)
            </label>
            <input
              type="text"
              placeholder={status?.timeframes?.join(', ') ?? '5m, 15m'}
              className="w-full px-3 py-2 text-sm font-mono border border-lumen-border rounded-lumen-sm bg-lumen-bg focus:outline-none focus:ring-2 focus:ring-lumen-primary-ring focus:border-lumen-primary"
              value={timeframes}
              onChange={(e) => setTimeframes(e.target.value)}
            />
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <button
            onClick={() => updateMut.mutate()}
            disabled={(!symbols.trim() && !timeframes.trim()) || updateMut.isPending}
            className="px-4 py-2 rounded-lumen-sm text-sm font-medium bg-lumen-primary text-white hover:bg-lumen-primary-hover disabled:opacity-50 transition-colors"
          >
            {updateMut.isPending ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Main Settings Page ───────────────────────────────────────────────────────

export default function Settings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-display font-semibold text-lumen-text">Configurações</h1>
        <p className="text-sm text-lumen-muted mt-1">Gerencie o bot, indicadores e coletor.</p>
      </div>

      <Tabs.Root defaultValue="bot">
        <Tabs.List className="flex border-b border-lumen-border mb-6">
          {[
            { value: 'bot', label: 'Bot' },
            { value: 'indicators', label: 'Indicadores' },
            { value: 'collector', label: 'Collector' },
            { value: 'prompt', label: 'Prompt' },
          ].map(({ value, label }) => (
            <Tabs.Trigger
              key={value}
              value={value}
              className="px-4 py-2.5 text-sm font-medium border-b-2 border-transparent text-lumen-muted hover:text-lumen-body transition-colors data-[state=active]:border-lumen-primary data-[state=active]:text-lumen-primary"
            >
              {label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>
        <Tabs.Content value="bot">
          <BotTab />
        </Tabs.Content>
        <Tabs.Content value="indicators">
          <IndicatorsTab />
        </Tabs.Content>
        <Tabs.Content value="collector">
          <CollectorTab />
        </Tabs.Content>
        <Tabs.Content value="prompt">
          <PromptEditor />
        </Tabs.Content>
      </Tabs.Root>
    </div>
  )
}
