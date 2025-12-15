'use client'

import { useEffect, useMemo, useState } from 'react'
import AppHeader from '@/app/components/AppHeader'
import Card from '@/app/components/Card'
import Button from '@/app/components/Button'
import { useAuth } from '@/app/hooks/useAuth'
import { DEFAULT_MODEL } from '@/app/config/models'
import { daApi, type DatasetDetails, type DatasetListItem, type RunStatus, type ChatResponse } from './api'

type SourceMode = 'upload' | 's3' | 'postgres'
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
  { key: 'choose', label: 'Route Job', description: 'Choose S3 vs Postgres processing', stateNames: ['ChooseJob'] },
  { key: 'glue', label: 'Glue ETL', description: 'Convert → Parquet + transforms + PII handling', stateNames: ['GlueETLS3', 'GlueETLPostgres'] },
  { key: 'catalog', label: 'Catalog', description: 'Create/Update Glue table for Athena', stateNames: ['Catalog'] },
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

  const [selectedModel, setSelectedModel] = useState(DEFAULT_MODEL)
  const [datasets, setDatasets] = useState<DatasetListItem[]>([])
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null)
  const [datasetDetails, setDatasetDetails] = useState<DatasetDetails | null>(null)

  const [sourceMode, setSourceMode] = useState<SourceMode>('upload')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
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
  const [lastQueryPreview, setLastQueryPreview] = useState<string>('')
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
    setLastQueryPreview('')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDatasetId])

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

    const url = `/api/apps/data-analysis/runs/${runId}/events?since_id=0`
    const es = new EventSource(url)
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
        const res = await fetch(`/api/apps/data-analysis/runs/${runId}/history`, { credentials: 'include' })
        if (!res.ok) {
          const errPayload = await res.json().catch(() => ({}))
          const detail = (errPayload as any)?.detail
          if (active && detail) setPipelineError(String(detail))
          return
        }
        const payload = await res.json()
        const events = (payload?.events || []) as PipelineEvent[]
        if (!active) return
        setPipelineEvents(prev => {
          const existing = new Set(prev.map(p => p.id))
          const merged = [...prev, ...events.filter(e => !existing.has(e.id))].sort((a, b) => a.id - b.id)
          return merged
        })
      } catch {
        // ignore; SSE may still work
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

      if (sourceMode === 's3') {
        if (!s3Uri.trim().startsWith('s3://')) throw new Error('Provide a valid S3 URI (s3://...)')
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
    setChatLog(prev => [...prev, { role: 'user', content: msg }])
    try {
      const res: ChatResponse = await daApi.chat({ message: msg, dataset_id: selectedDatasetId, model: selectedModel })
      if (res.sql) setLastSql(res.sql)
      if (res.query_result?.columns?.length) {
        const preview = [res.query_result.columns.join(' | '), ...(res.query_result.rows || []).slice(0, 5).map(r => r.join(' | '))].join('\n')
        setLastQueryPreview(preview)
      }
      setChatLog(prev => [...prev, { role: 'assistant', content: res.response || res.error || '' }])
    } catch (e: any) {
      setChatLog(prev => [...prev, { role: 'assistant', content: e?.message || 'Chat failed' }])
    }
  }

  if (loading) return <div>Loading...</div>

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white' }}>
      <AppHeader
        appName="Data Analysis"
        showModelSelector={true}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
      />

      <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px' }}>
        {error && (
          <div style={{ marginBottom: '16px', padding: '12px', border: '1px solid #7f1d1d', background: '#450a0a', borderRadius: '8px', color: '#fecaca' }}>
            {error}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: '16px' }}>
          <Card padding="lg">
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '10px' }}>1) Create Dataset</h2>
            <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              <Button variant={sourceMode === 'upload' ? 'primary' : 'secondary'} onClick={() => setSourceMode('upload')}>Upload</Button>
              <Button variant={sourceMode === 's3' ? 'primary' : 'secondary'} onClick={() => setSourceMode('s3')}>S3 URI</Button>
              <Button variant={sourceMode === 'postgres' ? 'primary' : 'secondary'} onClick={() => setSourceMode('postgres')}>Postgres</Button>
            </div>

            <div style={{ marginBottom: '10px' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>Dataset Name</label>
              <input
                value={datasetName}
                onChange={e => setDatasetName(e.target.value)}
                placeholder="e.g. Sales Orders"
                style={{ width: '100%', padding: '10px', background: '#0b1220', border: '1px solid #334155', borderRadius: '8px', color: 'white' }}
              />
            </div>

            {sourceMode === 'upload' && (
              <div style={{ marginBottom: '10px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>File</label>
                <input type="file" onChange={e => setUploadFile(e.target.files?.[0] || null)} />
              </div>
            )}

            {sourceMode === 's3' && (
              <div style={{ marginBottom: '10px' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>S3 URI</label>
                <input
                  value={s3Uri}
                  onChange={e => setS3Uri(e.target.value)}
                  placeholder="s3://bucket/path/to/file.csv"
                  style={{ width: '100%', padding: '10px', background: '#0b1220', border: '1px solid #334155', borderRadius: '8px', color: 'white' }}
                />
              </div>
            )}

            {sourceMode === 'postgres' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>Schema</label>
                  <input
                    value={pgSchema}
                    onChange={e => setPgSchema(e.target.value)}
                    style={{ width: '100%', padding: '10px', background: '#0b1220', border: '1px solid #334155', borderRadius: '8px', color: 'white' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>Table</label>
                  <input
                    value={pgTable}
                    onChange={e => setPgTable(e.target.value)}
                    placeholder="e.g. orders"
                    style={{ width: '100%', padding: '10px', background: '#0b1220', border: '1px solid #334155', borderRadius: '8px', color: 'white' }}
                  />
                </div>
                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>Optional Query</label>
                  <textarea
                    value={pgQuery}
                    onChange={e => setPgQuery(e.target.value)}
                    placeholder="SELECT * FROM public.orders WHERE created_at >= current_date - interval '30 days'"
                    style={{ width: '100%', minHeight: '80px', padding: '10px', background: '#0b1220', border: '1px solid #334155', borderRadius: '8px', color: 'white' }}
                  />
                </div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button onClick={handleCreateDataset}>Create</Button>
            </div>
          </Card>

          <Card padding="lg">
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '10px' }}>Datasets</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {datasets.map(d => (
                <button
                  key={d.id}
                  onClick={() => { setSelectedDatasetId(d.id); setRunId(null); setRunStatus(null) }}
                  style={{
                    textAlign: 'left',
                    padding: '10px',
                    borderRadius: '8px',
                    border: d.id === selectedDatasetId ? '1px solid #14b8a6' : '1px solid #334155',
                    background: d.id === selectedDatasetId ? 'rgba(20,184,166,0.12)' : '#0b1220',
                    color: 'white',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ fontWeight: 700 }}>{d.name}</div>
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{d.source_type} • {d.status}</div>
                </button>
              ))}
              {!datasets.length && <div style={{ color: '#94a3b8' }}>No datasets yet.</div>}
            </div>
          </Card>
        </div>

        <div style={{ marginTop: '16px' }}>
          <Card padding="lg">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Live Pipeline</h2>
              <div style={{ fontSize: '0.85rem', color: pipelineConnected ? '#34d399' : '#94a3b8' }}>
                Updates: {pipelineConnected ? 'Live' : 'Polling'}
              </div>
            </div>

            {!selectedDatasetId ? (
              <div style={{ color: '#94a3b8' }}>Create or select a dataset to start the pipeline.</div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div>
	                  <div style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px' }}>Pipeline Flow</div>
	                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
	                    {PIPELINE_STEPS.map((step, idx) => {
	                      const live = pipelineStepLive.find(s => s.key === step.key)
	                      const st = STATUS_STYLE[live?.status || 'pending']
	                      return (
	                        <div key={step.key} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
	                          <div style={{ minWidth: '220px', padding: '12px', borderRadius: '10px', border: `1px solid ${st.border}`, background: '#0b1220' }}>
	                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
	                              <div style={{ fontWeight: 800, fontSize: '0.95rem' }}>{idx + 1}. {step.label}</div>
	                              <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: st.color, flex: '0 0 auto' }} />
	                            </div>
	                            <div style={{ marginTop: '6px', fontSize: '0.85rem', color: '#94a3b8', lineHeight: 1.4 }}>
	                              {step.description}
	                            </div>
	                          </div>
	                          {idx < PIPELINE_STEPS.length - 1 && (
	                            <div style={{ color: '#64748b', fontSize: '1.25rem', padding: '0 2px' }}>→</div>
	                          )}
	                        </div>
	                      )
	                    })}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px' }}>Live Status</div>

                  <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: '10px', fontSize: '0.9rem' }}>
                    <div style={{ color: '#94a3b8' }}>Dataset</div>
                    <div>{selectedDataset?.name || datasetDetails?.name || '—'}</div>

                    <div style={{ color: '#94a3b8' }}>Dataset Status</div>
                    <div>{datasetDetails?.status || '—'}</div>

                    <div style={{ color: '#94a3b8' }}>Glue Table</div>
                    <div>{datasetDetails?.glue_database ? `${datasetDetails.glue_database}.${datasetDetails.glue_table || ''}` : '—'}</div>

                    <div style={{ color: '#94a3b8' }}>Run ID</div>
                    <div>{runId || '—'}</div>

                    <div style={{ color: '#94a3b8' }}>Execution</div>
                    <div style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{runStatus?.execution_arn || '—'}</div>

                    <div style={{ color: '#94a3b8' }}>Execution Status</div>
                    <div>{runStatus?.execution_status || runStatus?.status || (datasetDetails?.status ? datasetDetails.status.toUpperCase() : '—')}</div>

                    <div style={{ color: '#94a3b8' }}>Current Step</div>
                    <div>
                      {currentPipelineStep
                        ? `${currentPipelineStep.label} • ${STATUS_STYLE[currentPipelineStep.status].label}`
                        : '—'}
                    </div>
                  </div>

                  {datasetDetails?.last_error && (
                    <div style={{ marginTop: '12px', padding: '10px', borderRadius: '8px', border: '1px solid #7f1d1d', background: '#450a0a', color: '#fecaca' }}>
                      {datasetDetails.last_error}
                    </div>
                  )}

                  {pipelineError && (
                    <div style={{ marginTop: '12px', padding: '10px', borderRadius: '8px', border: '1px solid #7f1d1d', background: '#450a0a', color: '#fecaca' }}>
                      {pipelineError}
                    </div>
                  )}

                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '12px' }}>
                    <Button
                      variant="secondary"
                      onClick={handleStartPipeline}
                      disabled={!selectedDatasetId || isStarting || (runStatus?.execution_status || '').toUpperCase() === 'RUNNING'}
                    >
                      {isStarting ? 'Starting…' : (runStatus?.execution_status || '').toUpperCase() === 'RUNNING' ? 'Running…' : 'Re-run Pipeline'}
                    </Button>
                  </div>

                  <div style={{ marginTop: '12px', borderTop: '1px solid #334155', paddingTop: '12px' }}>
                    <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '8px' }}>Step Status</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {pipelineStepLive.map(step => {
                        const st = STATUS_STYLE[step.status]
                        const glueSuffix = step.label === 'Glue ETL' && step.stateName ? (step.stateName === 'GlueETLS3' ? ' (S3)' : ' (Postgres)') : ''
                        return (
                          <div key={step.key} style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '10px', padding: '10px', borderRadius: '8px', border: '1px solid #334155', background: '#0b1220' }}>
                            <div>
                              <div style={{ fontWeight: 700 }}>{step.label}{glueSuffix}</div>
                              <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                                {step.startedAt ? `Start: ${step.startedAt}` : 'Start: —'}{step.endedAt ? ` • End: ${step.endedAt}` : ''}
                              </div>
                              {(step.error || step.cause) && (
                                <div style={{ marginTop: '6px', fontSize: '0.8rem', color: '#fecaca' }}>
                                  {step.error || 'Error'}{step.cause ? `: ${step.cause}` : ''}
                                </div>
                              )}
                            </div>
                            <div style={{ alignSelf: 'start', padding: '4px 8px', borderRadius: '999px', border: `1px solid ${st.border}`, color: st.color, background: st.bg, fontSize: '0.8rem', fontWeight: 700 }}>
                              {st.label}
                            </div>
                          </div>
                        )
                      })}
                    </div>

                    <div style={{ marginTop: '12px' }}>
                      <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>Recent Events</div>
                      {pipelineEvents.length ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          {pipelineEvents.slice(-8).map(e => (
                            <div key={e.id} style={{ fontSize: '0.85rem', color: '#cbd5e1', display: 'flex', justifyContent: 'space-between', gap: '10px' }}>
                              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{e.state_name || e.type}</div>
                              <div style={{ color: '#94a3b8', whiteSpace: 'nowrap' }}>{e.timestamp}</div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div style={{ color: '#94a3b8' }}>Waiting for updates…</div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </Card>
        </div>

        <div style={{ marginTop: '16px' }}>
          <Card padding="lg">
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '10px' }}>Ask Questions</h2>
            {!canAskQuestions && (
              <div style={{ marginBottom: '12px', padding: '10px', borderRadius: '8px', border: '1px solid #334155', background: '#0b1220', color: '#94a3b8' }}>
                {selectedDatasetId
                  ? `Waiting for the pipeline to finish. Execution status: ${(runStatus?.execution_status || datasetDetails?.status || '—').toString().toUpperCase()}`
                  : 'Select a dataset first.'}
              </div>
            )}

            <div style={{ display: 'flex', gap: '10px', marginBottom: '12px' }}>
              <input
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleChat() }}
                disabled={!canAskQuestions}
                placeholder={canAskQuestions ? 'Ask about the data (e.g. top 10 customers by revenue)' : 'Pipeline not ready yet'}
                style={{ flex: 1, padding: '10px', background: '#0b1220', border: '1px solid #334155', borderRadius: '8px', color: 'white' }}
              />
              <Button onClick={handleChat} disabled={!canAskQuestions}>Send</Button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {chatLog.map((m, idx) => (
                <div key={idx} style={{ padding: '10px', borderRadius: '8px', border: '1px solid #334155', background: m.role === 'user' ? '#0b1220' : '#0b1a17' }}>
                  <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '6px' }}>{m.role === 'user' ? 'You' : 'Assistant'}</div>
                  <div style={{ whiteSpace: 'pre-wrap' }}>{m.content}</div>
                </div>
              ))}
              {!chatLog.length && (
                <div style={{ color: '#94a3b8' }}>
                  {canAskQuestions ? 'Ask a question to analyze your data.' : 'Pipeline is running (or not started yet). Once it succeeds, ask questions here.'}
                </div>
              )}
            </div>

            {(lastSql || lastQueryPreview) && (
              <div style={{ marginTop: '14px' }}>
                {lastSql && (
                  <>
                    <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '6px' }}>Last SQL</div>
                    <pre style={{ padding: '12px', background: '#0b1220', border: '1px solid #334155', borderRadius: '8px', color: '#e2e8f0', fontSize: '0.8rem', overflow: 'auto' }}>
{lastSql}
                    </pre>
                  </>
                )}
                {lastQueryPreview && (
                  <>
                    <div style={{ fontSize: '0.85rem', color: '#94a3b8', margin: '10px 0 6px' }}>Result Preview</div>
                    <pre style={{ padding: '12px', background: '#0b1220', border: '1px solid #334155', borderRadius: '8px', color: '#e2e8f0', fontSize: '0.8rem', overflow: 'auto' }}>
{lastQueryPreview}
                    </pre>
                  </>
                )}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
