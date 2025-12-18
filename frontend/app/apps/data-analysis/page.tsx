'use client'

import { useEffect, useMemo, useState } from 'react'
import AppHeader from '@/app/components/AppHeader'
import Card from '@/app/components/Card'
import Button from '@/app/components/Button'
import { useAuth } from '@/app/hooks/useAuth'
import { useModel } from '@/app/components/ModelProvider'
import { daApi, type DatasetDetails, type DatasetListItem, type RunStatus, type ChatResponse, type AgentStep, type PreviewResponse, type ChartData, type SuggestionsResponse } from './api'
import { api } from '@/app/services/api'

const SAMPLE_DATASETS = [
  { name: 'Orders', file: 'orders.csv', description: 'E-commerce orders with revenue data' },
  { name: 'Customers', file: 'customers.csv', description: 'Customer profiles with tiers' },
  { name: 'Products', file: 'products.csv', description: 'Product catalog with pricing' },
  { name: 'Sales', file: 'sales.csv', description: 'Regional sales performance' },
]

type SourceMode = 'upload' | 's3' | 'postgres' | 'sample'
type PipelineEvent = { id: number; timestamp: string; type: string; state_name?: string | null; error?: string; cause?: string }
type StepStatus = 'pending' | 'running' | 'succeeded' | 'failed'

type PipelineStep = {
  key: string
  label: string
  description: string
  stateNames: string[]
}

const PIPELINE_STEPS: PipelineStep[] = [
  { key: 'validate', label: 'Validate', description: 'Validate inputs and policy checks', stateNames: ['Validate'] },
  { key: 'choose', label: 'Route Job', description: 'Choose Storage vs Postgres processing', stateNames: ['ChooseJob'] },
  { key: 'glue', label: 'ETL', description: 'Convert → Parquet + transforms + PII handling', stateNames: ['GlueETLS3', 'GlueETLPostgres'] },
  { key: 'catalog', label: 'Catalog', description: 'Create/Update table for SQL queries', stateNames: ['Catalog'] },
  { key: 'finalize', label: 'Finalize', description: 'Publish outputs and mark run complete', stateNames: ['Finalize'] },
]

const STATUS_STYLE: Record<StepStatus, { label: string; color: string; border: string; bg: string }> = {
  pending: { label: 'Pending', color: '#94a3b8', border: '#334155', bg: '#0b1220' },
  running: { label: 'Running', color: '#fbbf24', border: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
  succeeded: { label: 'Succeeded', color: '#34d399', border: '#10b981', bg: 'rgba(16,185,129,0.12)' },
  failed: { label: 'Failed', color: '#f87171', border: '#ef4444', bg: 'rgba(239,68,68,0.12)' },
}

export default function DataAnalysisApp() {
  const { user, loading } = useAuth(true)
  const { selectedModel, setSelectedModel } = useModel()

  const [datasets, setDatasets] = useState<DatasetListItem[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null)
  const [datasetDetails, setDatasetDetails] = useState<DatasetDetails | null>(null)

  const [sourceMode, setSourceMode] = useState<SourceMode>('upload')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [selectedSample, setSelectedSample] = useState<string>('')
  const [datasetName, setDatasetName] = useState('')
  const [s3Uri, setS3Uri] = useState('')
  const [pgSchema, setPgSchema] = useState('public')
  const [pgTable, setPgTable] = useState('')
  const [pgQuery, setPgQuery] = useState('')

  const [runId, setRunId] = useState<number | null>(null)
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [pipelineEvents, setPipelineEvents] = useState<PipelineEvent[]>([])
  const [pipelineConnected, setPipelineConnected] = useState(false)
  const [pipelineError, setPipelineError] = useState<string>('')

  const [chatInput, setChatInput] = useState('')
  const [chatLog, setChatLog] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([])
  const [lastSql, setLastSql] = useState<string>('')
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([])
  const [isAsking, setIsAsking] = useState(false)
  const [preview, setPreview] = useState<PreviewResponse | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [chartData, setChartData] = useState<ChartData | null>(null)
  const [error, setError] = useState<string>('')

  const selectedDataset = useMemo(
    () => datasets.find(d => d.id === selectedDatasetId) || null,
    [datasets, selectedDatasetId]
  )

  const pipelineStepLive = useMemo(() => {
    const stateToKey = new Map<string, string>()
    for (const step of PIPELINE_STEPS) {
      for (const stateName of step.stateNames) stateToKey.set(stateName, step.key)
    }

    const byKey: Record<string, { status: StepStatus; stateName?: string; startedAt?: string; endedAt?: string; error?: string; cause?: string }> = {}
    for (const step of PIPELINE_STEPS) byKey[step.key] = { status: 'pending' }

    const events = [...pipelineEvents].sort((a, b) => a.id - b.id)
    for (const e of events) {
      const stateName = e.state_name || ''
      const key = stateName ? stateToKey.get(stateName) : undefined

      const failureEvent = e.type === 'TaskFailed' || e.type === 'TaskTimedOut' || e.type === 'TaskAborted'
      if (!key && failureEvent && (e.error || e.cause)) {
        const lastRunning = [...PIPELINE_STEPS]
          .map(s => byKey[s.key])
          .map((live, idx) => ({ live, key: PIPELINE_STEPS[idx].key }))
          .filter(x => x.live.status === 'running')
          .map(x => x.key)
          .pop()
        if (lastRunning) {
          byKey[lastRunning].status = 'failed'
          byKey[lastRunning].error = e.error
          byKey[lastRunning].cause = e.cause
        }
        continue
      }

      if (!key) continue

      const target = byKey[key]
      target.stateName = stateName
      if (e.type.endsWith('StateEntered')) {
        if (!target.startedAt) target.startedAt = e.timestamp
        if (target.status !== 'succeeded') target.status = 'running'
      }
      if (e.type.endsWith('StateExited')) {
        target.endedAt = e.timestamp
        target.status = 'succeeded'
      }
      if (failureEvent && (e.error || e.cause)) {
        target.status = 'failed'
        target.error = e.error
        target.cause = e.cause
      }
    }

    const execStatus = (runStatus?.execution_status || '').toUpperCase()
    const execFailed = execStatus === 'FAILED' || execStatus === 'ABORTED' || execStatus === 'TIMED_OUT'
    const execSucceeded = execStatus === 'SUCCEEDED'

    if (execFailed) {
      const execFailEvent = [...events].reverse().find(e => e.type === 'ExecutionFailed' || e.type === 'ExecutionAborted' || e.type === 'ExecutionTimedOut')
      const fallbackError = execFailEvent?.error
      const fallbackCause = execFailEvent?.cause
      const candidate = PIPELINE_STEPS.map(s => ({ key: s.key, live: byKey[s.key] }))
        .filter(x => x.live.startedAt && !x.live.endedAt && x.live.status !== 'succeeded')
        .map(x => x.key)
        .pop()
      if (candidate) {
        byKey[candidate].status = 'failed'
        byKey[candidate].error = byKey[candidate].error || fallbackError
        byKey[candidate].cause = byKey[candidate].cause || fallbackCause
      }
    }

    if (execSucceeded) {
      for (const step of PIPELINE_STEPS) {
        const live = byKey[step.key]
        if (live.status === 'running') live.status = 'succeeded'
      }
    }

    return PIPELINE_STEPS.map(step => ({
      ...step,
      ...byKey[step.key],
    }))
  }, [pipelineEvents, runStatus])

  const currentPipelineStep = useMemo(() => {
    const running = pipelineStepLive.find(s => s.status === 'running')
    if (running) return running
    const failed = pipelineStepLive.find(s => s.status === 'failed')
    if (failed) return failed
    const succeeded = [...pipelineStepLive].reverse().find(s => s.status === 'succeeded')
    return succeeded || null
  }, [pipelineStepLive])

  const canAskQuestions = useMemo(() => {
    const execStatus = (runStatus?.execution_status || '').toUpperCase()
    const readyByRun = execStatus === 'SUCCEEDED'
    const readyByDataset = (datasetDetails?.status || '').toLowerCase() === 'ready'
    const hasTable = !!datasetDetails?.glue_database && !!datasetDetails?.glue_table
    return !!selectedDatasetId && hasTable && (readyByRun || readyByDataset)
  }, [datasetDetails?.glue_database, datasetDetails?.glue_table, datasetDetails?.status, runStatus?.execution_status, selectedDatasetId])

  const refreshDatasets = async () => {
    const items = await daApi.listDatasets()
    setDatasets(items)
    if (!selectedDatasetId && items.length) setSelectedDatasetId(items[0].id)
  }

  const refreshDatasetDetails = async (id: number) => {
    const details = await daApi.getDataset(id)
    setDatasetDetails(details)
  }

  useEffect(() => {
    if (!user) return
    refreshDatasets().catch(e => setError(e?.message || 'Failed to load datasets'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

  useEffect(() => {
    if (!selectedDatasetId) return
    refreshDatasetDetails(selectedDatasetId).catch(() => setDatasetDetails(null))
    setChatLog([])
    setLastSql('')
    setAgentSteps([])
    setPreview(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDatasetId])

  // Fetch preview and suggestions when dataset is ready
  useEffect(() => {
    if (!canAskQuestions || !selectedDatasetId) {
      setPreview(null)
      setSuggestions([])
      return
    }
    setPreviewLoading(true)
    daApi.getPreview(selectedDatasetId, 10)
      .then(setPreview)
      .catch(() => setPreview(null))
      .finally(() => setPreviewLoading(false))
    
    daApi.getSuggestions(selectedDatasetId)
      .then(res => setSuggestions(res.suggestions || []))
      .catch(() => setSuggestions([]))
  }, [canAskQuestions, selectedDatasetId])

  useEffect(() => {
    if (!datasetDetails?.last_run_id) return
    if (!runId || runId !== datasetDetails.last_run_id) {
      setRunId(datasetDetails.last_run_id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetDetails?.last_run_id])

  useEffect(() => {
    if (!runId) return
    let active = true
    const tick = async () => {
      try {
        const status = await daApi.getRun(runId)
        if (!active) return
        setRunStatus(status)
      } catch (e: any) {
        if (!active) return
        setError(e?.message || 'Failed to fetch run status')
      }
    }
    tick()
    const i = setInterval(tick, 3000)
    return () => {
      active = false
      clearInterval(i)
    }
  }, [runId])

  useEffect(() => {
    if (!runId) return
    setPipelineEvents([])
    setPipelineConnected(false)
    setPipelineError('')

    const url = api.getStreamUrl(`/api/apps/data-analysis/runs/${runId}/events?since_id=0`)
    const es = new EventSource(url, { withCredentials: true })
    es.onopen = () => setPipelineConnected(true)
    es.addEventListener('init', () => setPipelineConnected(true))
    es.addEventListener('event', (evt: any) => {
      try {
        const data = JSON.parse(evt.data || '{}') as PipelineEvent
        setPipelineEvents(prev => {
          if (!data?.id) return prev
          if (prev.some(p => p.id === data.id)) return prev
          return [...prev, data].sort((a, b) => a.id - b.id)
        })
      } catch {
        // ignore
      }
    })
    es.addEventListener('error', () => {
      setPipelineConnected(false)
    })

    return () => {
      es.close()
      setPipelineConnected(false)
    }
  }, [runId])

  useEffect(() => {
    if (!runId) return
    let active = true
    const tick = async () => {
      try {
        const res = await api.request(`/api/apps/data-analysis/runs/${runId}/history`)
        const payload = await res.json()
        const events = (payload?.events || []) as PipelineEvent[]
        if (!active) return
        setPipelineEvents(prev => {
          const existing = new Set(prev.map(p => p.id))
          const merged = [...prev, ...events.filter(e => !existing.has(e.id))].sort((a, b) => a.id - b.id)
          return merged
        })
      } catch (e: any) {
        if (active) setPipelineError(e?.message || 'Pipeline history unavailable')
      }
    }
    tick()
    const i = setInterval(tick, 3000)
    return () => {
      active = false
      clearInterval(i)
    }
  }, [runId])

  const handleCreateDataset = async () => {
    setError('')
    try {
      if (!datasetName.trim()) throw new Error('Dataset name is required')

      if (sourceMode === 'upload') {
        if (!uploadFile) throw new Error('Select a file to upload')
        const form = new FormData()
        form.append('file', uploadFile)
        form.append('name', datasetName.trim())
        const res = await daApi.uploadDataset(form)
        await refreshDatasets()
        setSelectedDatasetId(res.dataset_id)
        if (res.run_id) setRunId(res.run_id)
        return
      }

      if (sourceMode === 'sample') {
        if (!selectedSample) throw new Error('Select a sample dataset')
        const sample = SAMPLE_DATASETS.find(s => s.file === selectedSample)
        if (!sample) throw new Error('Invalid sample dataset')
        const response = await fetch(`/sample_datasets/${sample.file}`)
        if (!response.ok) throw new Error('Failed to fetch sample dataset')
        const blob = await response.blob()
        const file = new File([blob], sample.file, { type: 'text/csv' })
        const form = new FormData()
        form.append('file', file)
        form.append('name', datasetName.trim())
        const res = await daApi.uploadDataset(form)
        await refreshDatasets()
        setSelectedDatasetId(res.dataset_id)
        if (res.run_id) setRunId(res.run_id)
        return
      }

      if (sourceMode === 's3') {
        if (!s3Uri.trim().startsWith('s3://') && !s3Uri.trim().startsWith('gs://')) throw new Error('Provide a valid storage URI (s3://... or gs://...)')
        const res = await daApi.createS3Dataset({ name: datasetName.trim(), s3_uri: s3Uri.trim() })
        await refreshDatasets()
        setSelectedDatasetId(res.dataset_id)
        if (res.run_id) setRunId(res.run_id)
        return
      }

      if (sourceMode === 'postgres') {
        if (!pgTable.trim() && !pgQuery.trim()) throw new Error('Provide a Postgres table or query')
        const res = await daApi.createPostgresDataset({
          name: datasetName.trim(),
          schema: pgSchema.trim() || 'public',
          table: pgTable.trim() || 'table_from_query',
          query: pgQuery.trim() || undefined,
        })
        await refreshDatasets()
        setSelectedDatasetId(res.dataset_id)
        if (res.run_id) setRunId(res.run_id)
        return
      }
    } catch (e: any) {
      setError(e?.message || 'Create failed')
    }
  }

  const handleStartPipeline = async () => {
    if (!selectedDatasetId) return
    setIsStarting(true)
    setError('')
    try {
      const res = await daApi.startRun({ dataset_id: selectedDatasetId })
      setRunId(res.run_id)
      await refreshDatasetDetails(selectedDatasetId)
    } catch (e: any) {
      setError(e?.message || 'Failed to start pipeline')
    } finally {
      setIsStarting(false)
    }
  }

  const handleChat = async () => {
    if (!selectedDatasetId) return
    if (!canAskQuestions) return
    const msg = chatInput.trim()
    if (!msg) return
    setChatInput('')
    setError('')
    setAgentSteps([])
    setChartData(null)
    setIsAsking(true)
    setChatLog(prev => [...prev, { role: 'user', content: msg }])
    try {
      const res: ChatResponse = await daApi.chat({ message: msg, dataset_id: selectedDatasetId, model: selectedModel })
      if (res.sql) setLastSql(res.sql)
      if (res.agent_steps) setAgentSteps(res.agent_steps)
      if (res.chart_data) setChartData(res.chart_data)
      setChatLog(prev => [...prev, { role: 'assistant', content: res.response || res.error || '' }])
    } catch (e: any) {
      setChatLog(prev => [...prev, { role: 'assistant', content: e?.message || 'Chat failed' }])
    } finally {
      setIsAsking(false)
    }
  }

  const handleExport = async () => {
    if (!selectedDatasetId || !lastSql) return
    try {
      const blob = await daApi.exportQuery(selectedDatasetId, lastSql)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${selectedDataset?.name || 'export'}_results.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e: any) {
      setError(e?.message || 'Export failed')
    }
  }

  if (loading) return <div>Loading...</div>

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white' }}>
      <AppHeader
        appName="Agentic Data Analysis"
        showModelSelector={true}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
      />

      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px' }}>
        {error && (
          <div style={{ marginBottom: '16px', padding: '12px', border: '1px solid #7f1d1d', background: '#450a0a', borderRadius: '8px', color: '#fecaca' }}>
            {error}
          </div>
        )}

        {/* Row 1: Create Dataset | Datasets | Live Pipeline */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px 1fr', gap: '16px', marginBottom: '16px' }}>
          {/* Create Dataset */}
          <Card padding="lg">
            <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '10px' }}>Create Dataset</h2>
            <div style={{ display: 'flex', gap: '6px', marginBottom: '10px', flexWrap: 'wrap' }}>
              <Button size="sm" variant={sourceMode === 'sample' ? 'primary' : 'secondary'} onClick={() => setSourceMode('sample')}>Sample</Button>
              <Button size="sm" variant={sourceMode === 'upload' ? 'primary' : 'secondary'} onClick={() => setSourceMode('upload')}>Upload</Button>
              <Button size="sm" variant={sourceMode === 's3' ? 'primary' : 'secondary'} onClick={() => setSourceMode('s3')}>Cloud Storage</Button>
              <Button size="sm" variant={sourceMode === 'postgres' ? 'primary' : 'secondary'} onClick={() => setSourceMode('postgres')}>Postgres</Button>
            </div>

            <div style={{ marginBottom: '8px' }}>
              <input
                value={datasetName}
                onChange={e => setDatasetName(e.target.value)}
                placeholder="Dataset Name"
                style={{ width: '100%', padding: '8px', background: '#0b1220', border: '1px solid #334155', borderRadius: '6px', color: 'white', fontSize: '0.9rem' }}
              />
            </div>

            {sourceMode === 'sample' && (
              <div style={{ marginBottom: '8px' }}>
                <select
                  value={selectedSample}
                  onChange={e => { setSelectedSample(e.target.value); if (!datasetName) setDatasetName(SAMPLE_DATASETS.find(s => s.file === e.target.value)?.name || '') }}
                  style={{ width: '100%', padding: '8px', background: '#0b1220', border: '1px solid #334155', borderRadius: '6px', color: 'white', fontSize: '0.9rem' }}
                >
                  <option value="">Select sample dataset...</option>
                  {SAMPLE_DATASETS.map(s => (
                    <option key={s.file} value={s.file}>{s.name} - {s.description}</option>
                  ))}
                </select>
              </div>
            )}

            {sourceMode === 'upload' && (
              <div style={{ marginBottom: '8px' }}>
                <input type="file" onChange={e => setUploadFile(e.target.files?.[0] || null)} style={{ fontSize: '0.85rem' }} />
              </div>
            )}

            {sourceMode === 's3' && (
              <div style={{ marginBottom: '8px' }}>
                <input
                  value={s3Uri}
                  onChange={e => setS3Uri(e.target.value)}
                  placeholder="s3://bucket/path/file.csv or gs://bucket/path/file.csv"
                  style={{ width: '100%', padding: '8px', background: '#0b1220', border: '1px solid #334155', borderRadius: '6px', color: 'white', fontSize: '0.9rem' }}
                />
              </div>
            )}

            {sourceMode === 'postgres' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', marginBottom: '8px' }}>
                <input value={pgSchema} onChange={e => setPgSchema(e.target.value)} placeholder="Schema" style={{ padding: '8px', background: '#0b1220', border: '1px solid #334155', borderRadius: '6px', color: 'white', fontSize: '0.9rem' }} />
                <input value={pgTable} onChange={e => setPgTable(e.target.value)} placeholder="Table" style={{ padding: '8px', background: '#0b1220', border: '1px solid #334155', borderRadius: '6px', color: 'white', fontSize: '0.9rem' }} />
              </div>
            )}

            <div style={{ marginTop: '8px' }}>
              <Button onClick={handleCreateDataset}>Create</Button>
            </div>
          </Card>

          {/* Datasets List */}
          <Card padding="lg">
            <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '10px' }}>Datasets</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '200px', overflowY: 'auto' }}>
              {datasets.map(d => (
                <button
                  key={d.id}
                  onClick={() => { setSelectedDatasetId(d.id); setRunId(null); setRunStatus(null) }}
                  style={{
                    textAlign: 'left',
                    padding: '8px',
                    borderRadius: '6px',
                    border: d.id === selectedDatasetId ? '1px solid #14b8a6' : '1px solid #334155',
                    background: d.id === selectedDatasetId ? 'rgba(20,184,166,0.12)' : '#0b1220',
                    color: 'white',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{d.name}</div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{d.source_type} • {d.status}</div>
                </button>
              ))}
              {!datasets.length && <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>No datasets yet.</div>}
            </div>
          </Card>

          {/* Live Pipeline */}
          <Card padding="lg">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <h2 style={{ fontSize: '1rem', fontWeight: 700 }}>Pipeline</h2>
              <div style={{ fontSize: '0.75rem', color: pipelineConnected ? '#34d399' : '#94a3b8' }}>
                {pipelineConnected ? '● Live' : '○ Polling'}
              </div>
            </div>
            {!selectedDatasetId ? (
              <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Select a dataset</div>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
                {PIPELINE_STEPS.map((step, idx) => {
                  const live = pipelineStepLive.find(s => s.key === step.key)
                  const st = STATUS_STYLE[live?.status || 'pending']
                  return (
                    <div key={step.key} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <div style={{ padding: '6px 10px', borderRadius: '6px', border: `1px solid ${st.border}`, background: st.bg, fontSize: '0.8rem' }}>
                        <span style={{ color: st.color }}>{step.label}</span>
                      </div>
                      {idx < PIPELINE_STEPS.length - 1 && <span style={{ color: '#64748b' }}>→</span>}
                    </div>
                  )
                })}
              </div>
            )}
            <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                size="sm"
                variant="secondary"
                onClick={handleStartPipeline}
                disabled={!selectedDatasetId || isStarting || (runStatus?.execution_status || '').toUpperCase() === 'RUNNING'}
              >
                {isStarting ? 'Starting…' : 'Re-run'}
              </Button>
            </div>
          </Card>
        </div>

        {/* Row 2: Dataset Preview */}
        {selectedDatasetId && (
          <div style={{ marginBottom: '16px' }}>
            <Card padding="lg">
              <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '12px' }}>
                Dataset Preview {selectedDataset ? <span style={{ fontWeight: 400, color: '#94a3b8' }}>({selectedDataset.name})</span> : ''}
              </h2>
              {previewLoading ? (
                <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Loading preview...</div>
              ) : preview ? (
                <div style={{ overflowX: 'auto', maxHeight: '200px', overflowY: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                    <thead>
                      <tr style={{ background: '#1e293b' }}>
                        {preview.columns.map((col, i) => (
                          <th key={i} style={{ padding: '8px', textAlign: 'left', borderBottom: '1px solid #334155', color: '#94a3b8', whiteSpace: 'nowrap' }}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.rows.map((row, i) => (
                        <tr key={i} style={{ background: i % 2 === 0 ? '#0b1220' : '#0f172a' }}>
                          {row.map((cell, j) => (
                            <td key={j} style={{ padding: '8px', borderBottom: '1px solid #334155', whiteSpace: 'nowrap' }}>{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : canAskQuestions ? (
                <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>No preview available</div>
              ) : (
                <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Preview available after pipeline completes</div>
              )}
            </Card>
          </div>
        )}

        {/* Row 3: Live Status (left) | Ask Questions (right) */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          {/* Live Status */}
          <Card padding="lg">
            <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '12px' }}>Live Status</h2>
            {!selectedDatasetId ? (
              <div style={{ color: '#94a3b8' }}>Select a dataset to view status.</div>
            ) : (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: '8px', fontSize: '0.85rem', marginBottom: '12px' }}>
                  <div style={{ color: '#94a3b8' }}>Dataset</div>
                  <div>{selectedDataset?.name || datasetDetails?.name || '—'}</div>
                  <div style={{ color: '#94a3b8' }}>Status</div>
                  <div>{datasetDetails?.status || '—'}</div>
                  <div style={{ color: '#94a3b8' }}>Data Table</div>
                  <div style={{ fontSize: '0.8rem' }}>{datasetDetails?.glue_database ? `${datasetDetails.glue_database}.${datasetDetails.glue_table || ''}` : '—'}</div>
                  <div style={{ color: '#94a3b8' }}>Run ID</div>
                  <div>{runId || '—'}</div>
                  <div style={{ color: '#94a3b8' }}>Execution</div>
                  <div>{runStatus?.execution_status || runStatus?.status || '—'}</div>
                  <div style={{ color: '#94a3b8' }}>Current Step</div>
                  <div>{currentPipelineStep ? `${currentPipelineStep.label} • ${STATUS_STYLE[currentPipelineStep.status].label}` : '—'}</div>
                </div>

                {(datasetDetails?.last_error || pipelineError) && (
                  <div style={{ marginBottom: '12px', padding: '8px', borderRadius: '6px', border: '1px solid #7f1d1d', background: '#450a0a', color: '#fecaca', fontSize: '0.85rem' }}>
                    {datasetDetails?.last_error || pipelineError}
                  </div>
                )}

                <div style={{ borderTop: '1px solid #334155', paddingTop: '12px' }}>
                  <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '8px' }}>Step Details</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '200px', overflowY: 'auto' }}>
                    {pipelineStepLive.map(step => {
                      const st = STATUS_STYLE[step.status]
                      return (
                        <div key={step.key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px', borderRadius: '6px', border: '1px solid #334155', background: '#0b1220' }}>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{step.label}</div>
                            {step.startedAt && <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{step.startedAt}</div>}
                          </div>
                          <div style={{ padding: '3px 8px', borderRadius: '999px', border: `1px solid ${st.border}`, color: st.color, background: st.bg, fontSize: '0.75rem', fontWeight: 600 }}>
                            {st.label}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                <div style={{ marginTop: '12px', borderTop: '1px solid #334155', paddingTop: '12px' }}>
                  <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>Recent Events</div>
                  <div style={{ maxHeight: '120px', overflowY: 'auto' }}>
                    {pipelineEvents.length ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {pipelineEvents.slice(-6).map(e => (
                          <div key={e.id} style={{ fontSize: '0.8rem', color: '#cbd5e1', display: 'flex', justifyContent: 'space-between' }}>
                            <span>{e.state_name || e.type}</span>
                            <span style={{ color: '#94a3b8' }}>{e.timestamp?.split('T')[1]?.slice(0, 8) || ''}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ color: '#94a3b8', fontSize: '0.8rem' }}>Waiting for events…</div>
                    )}
                  </div>
                </div>
              </>
            )}
          </Card>

          {/* Ask Questions */}
          <Card padding="lg">
            <h2 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '12px' }}>Ask Questions</h2>
            {!canAskQuestions && (
              <div style={{ marginBottom: '10px', padding: '8px', borderRadius: '6px', border: '1px solid #334155', background: '#0b1220', color: '#94a3b8', fontSize: '0.85rem' }}>
                {selectedDatasetId
                  ? `Waiting for pipeline. Status: ${(runStatus?.execution_status || datasetDetails?.status || '—').toString().toUpperCase()}`
                  : 'Select a dataset first.'}
              </div>
            )}

            {/* Suggested Questions */}
            {suggestions.length > 0 && (
              <div style={{ marginBottom: '10px' }}>
                <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '6px' }}>Suggested questions:</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {suggestions.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => setChatInput(q)}
                      style={{ padding: '4px 10px', borderRadius: '12px', border: '1px solid #334155', background: '#1e293b', color: '#94a3b8', fontSize: '0.75rem', cursor: 'pointer' }}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              <input
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !isAsking) handleChat() }}
                disabled={!canAskQuestions || isAsking}
                placeholder={canAskQuestions ? 'e.g. top 10 customers by revenue' : 'Pipeline not ready'}
                style={{ flex: 1, padding: '8px', background: '#0b1220', border: '1px solid #334155', borderRadius: '6px', color: 'white', fontSize: '0.9rem' }}
              />
              <Button onClick={handleChat} disabled={!canAskQuestions || isAsking}>{isAsking ? 'Thinking...' : 'Send'}</Button>
            </div>

            {/* Agent Steps Pipeline */}
            {(isAsking || agentSteps.length > 0) && (
              <div style={{ marginBottom: '12px', padding: '10px', borderRadius: '6px', border: '1px solid #334155', background: '#0b1220' }}>
                <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '8px' }}>Agent Flow</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
                  {agentSteps.map((step, idx) => (
                    <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <div style={{ 
                        padding: '4px 8px', 
                        borderRadius: '4px', 
                        background: step.status === 'completed' ? 'rgba(16,185,129,0.12)' : 'rgba(245,158,11,0.12)',
                        border: `1px solid ${step.status === 'completed' ? '#10b981' : '#f59e0b'}`,
                        fontSize: '0.75rem'
                      }}>
                        <span style={{ color: step.status === 'completed' ? '#34d399' : '#fbbf24' }}>
                          {step.tool === 'get_schema' ? '📋 Schema' : 
                           step.tool === 'run_sql' ? '🔍 SQL' : 
                           step.tool === 'sample_data' ? '📊 Sample' : 
                           step.tool === 'answer' ? '✅ Answer' : step.tool}
                        </span>
                      </div>
                      {idx < agentSteps.length - 1 && <span style={{ color: '#64748b' }}>→</span>}
                    </div>
                  ))}
                  {isAsking && <span style={{ color: '#fbbf24', fontSize: '0.75rem' }}>⏳ Thinking...</span>}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '200px', overflowY: 'auto' }}>
              {chatLog.map((m, idx) => (
                <div key={idx} style={{ padding: '8px', borderRadius: '6px', border: '1px solid #334155', background: m.role === 'user' ? '#0b1220' : '#0b1a17' }}>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>{m.role === 'user' ? 'You' : 'Assistant'}</div>
                  <div style={{ whiteSpace: 'pre-wrap', fontSize: '0.9rem' }}>{m.content}</div>
                </div>
              ))}
              {!chatLog.length && (
                <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>
                  {canAskQuestions ? 'Ask a question to analyze your data.' : 'Waiting for pipeline to complete.'}
                </div>
              )}
            </div>

            {/* Chart Visualization */}
            {chartData && (
              <div style={{ marginTop: '12px', padding: '12px', borderRadius: '6px', border: '1px solid #334155', background: '#0b1220' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '8px' }}>{chartData.title}</div>
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: '4px', height: '120px' }}>
                  {chartData.values.map((val, i) => {
                    const maxVal = Math.max(...chartData.values)
                    const height = maxVal > 0 ? (val / maxVal) * 100 : 0
                    return (
                      <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                        <div style={{ 
                          width: '100%', 
                          height: `${height}%`, 
                          background: chartData.type === 'bar' ? '#14b8a6' : '#3b82f6',
                          borderRadius: '2px 2px 0 0',
                          minHeight: '4px'
                        }} />
                        <div style={{ fontSize: '0.65rem', color: '#94a3b8', textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '60px' }}>
                          {chartData.labels[i]}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {lastSql && (
              <div style={{ marginTop: '12px', borderTop: '1px solid #334155', paddingTop: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Last SQL</div>
                  <button
                    onClick={handleExport}
                    style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #334155', background: '#1e293b', color: '#94a3b8', fontSize: '0.7rem', cursor: 'pointer' }}
                  >
                    📥 Export CSV
                  </button>
                </div>
                <pre style={{ padding: '8px', background: '#0b1220', border: '1px solid #334155', borderRadius: '6px', color: '#e2e8f0', fontSize: '0.75rem', overflow: 'auto', maxHeight: '80px' }}>{lastSql}</pre>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
