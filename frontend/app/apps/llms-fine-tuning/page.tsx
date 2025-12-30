'use client'

import { useEffect, useRef, useState } from 'react'
import Card from '@/app/design-system/components/Card'
import AppHeader from '@/app/design-system/components/AppHeader'
import { useAuth } from '@/app/hooks/useAuth'
import { DatasetDefinition, fineTuningApi, JobRunView, JobStatus } from './api'

type StepDefinition = {
  id: string
  title: string
  description: string
  jobKey: string
  note?: string
  usesSampleInput?: boolean
}

type MiniAppDefinition = {
  id: string
  title: string
  subtitle: string
  accent: string
  explanation: string
  recommendedDatasetIds: string[]
  defaultModelName: string
  steps: StepDefinition[]
  hint?: string
}

const MINI_APPS: MiniAppDefinition[] = [
  {
    id: 'multilingual',
    title: 'Multilingual Classification',
    subtitle: 'Generate → Train → Sample on your distilled language classifier',
    accent: '#22c55e',
    hint: 'Runs in test-tinker; keep the order for clean runs.',
    explanation:
      'Supervised fine-tuning (SFT) on multilingual text → 2-letter language labels. This is a small end-to-end reference workflow (data → LoRA training → sampling).',
    recommendedDatasetIds: ['prompt_distillation_lang'],
    defaultModelName: 'meta-llama/Llama-3.2-1B',
    steps: [
      {
        id: 'multilingual-generate',
        title: '1) Generate Data',
        description: 'Create the distilled dataset via ./scripts/generate_data.sh',
        jobKey: 'multilingual-generate',
        note: 'Working dir: test-tinker'
      },
      {
        id: 'multilingual-train',
        title: '2) Train',
        description: 'Fine-tune the multilingual classifier via ./scripts/train.sh',
        jobKey: 'multilingual-train',
        note: 'Ensure data is present before running.'
      },
      {
        id: 'multilingual-sample',
        title: '3) Sample / Predictions',
        description: 'Run python sample.py --log-path ./runs/prompt-distillation with your selected question',
        jobKey: 'multilingual-sample',
        note: 'Pick a default question or type your own, then inspect predictions from the latest checkpoint.',
        usesSampleInput: true
      }
    ]
  },
  {
    id: 'sft',
    title: 'Instruction Tuning (Supervised Fine-Tuning / SFT)',
    subtitle: 'Validate → Supervised Fine-Tune → Ask questions (fine-tuned checkpoint)',
    accent: '#38bdf8',
    hint: 'Use the built-in AWS EKS starter dataset or upload your own messages[].',
    explanation:
      'Supervised Fine-Tuning (SFT) trains the model on prompt → ideal answer pairs using cross-entropy. Best for tone/style, runbooks, structured outputs, and domain-specific Q&A.',
    recommendedDatasetIds: ['instruction_tuning_aws_eks'],
    defaultModelName: 'meta-llama/Llama-3.2-1B',
    steps: [
      {
        id: 'sft-validate',
        title: '1) Validate Dataset',
        description: 'Validate that each JSONL row contains messages[] with role/content.',
        jobKey: 'sft-validate',
        note: 'Run this after uploading a dataset to catch schema issues early.'
      },
      {
        id: 'sft-train',
        title: '2) Supervised Fine-Tune (cross-entropy)',
        description: 'Train LoRA adapters via supervised learning (cross-entropy) with tinker_cookbook.recipes.chat_sl.train.',
        jobKey: 'sft-train',
        note: 'Uses Dataset + Base model selections above.'
      },
      {
        id: 'sft-sample',
        title: '3) Ask / Sample',
        description: 'Ask a question and sample from the latest fine-tuned checkpoint.',
        jobKey: 'sft-sample',
        note: 'Uses SAMPLE_INPUT and runs/instruction-tuning checkpoints.',
        usesSampleInput: true
      }
    ]
  },
  {
    id: 'rl',
    title: 'RL Mini-App (Importance Sampling)',
    subtitle: 'Validate → Reinforcement Learning → Sample (rewarded behavior)',
    accent: '#a78bfa',
    hint: 'Start with objective rewards: parseable JSON + required keys.',
    explanation:
      'Reinforcement Learning (RL) fine-tunes the model to maximize a reward signal rather than imitate labels. This mini-app uses importance sampling to reward outputs that are valid JSON and include required keys (great for enforcing formatting constraints).',
    recommendedDatasetIds: ['rl_json_formatting_prompts'],
    defaultModelName: 'meta-llama/Llama-3.2-1B',
    steps: [
      {
        id: 'rl-validate',
        title: '1) Validate RL Prompt Set',
        description: "Validate JSONL rows with 'prompt' and 'required_keys[]'.",
        jobKey: 'rl-validate'
      },
      {
        id: 'rl-train',
        title: '2) Train (importance_sampling)',
        description: 'Sample multiple outputs, score them with a reward, compute advantages, and optimize with loss_fn=importance_sampling.',
        jobKey: 'rl-train',
        note: 'Writes checkpoints to runs/rl-json.'
      },
      {
        id: 'rl-sample',
        title: '3) Sample',
        description: 'Try a strict-JSON prompt and inspect the output.',
        jobKey: 'rl-sample',
        usesSampleInput: true
      }
    ]
  }
]

const SAMPLE_DEFAULTS = [
  'Hello, how are you?',
  'Bonjour, comment allez-vous?',
  '你好，这周末有空吗？',
  'مرحبا كيف حالك اليوم؟',
  'Guten Tag, ich heiße Anna.',
  'Xin chào, hôm nay bạn ổn chứ?',
  '¿Dónde está la biblioteca?'
]

const statusMeta: Record<JobStatus, { label: string; color: string; background: string }> = {
  idle: { label: 'Idle', color: '#94a3b8', background: 'rgba(148,163,184,0.15)' },
  queued: { label: 'Queued', color: '#38bdf8', background: 'rgba(56,189,248,0.12)' },
  running: { label: 'Running', color: '#f97316', background: 'rgba(249,115,22,0.12)' },
  success: { label: 'Success', color: '#22c55e', background: 'rgba(34,197,94,0.12)' },
  failed: { label: 'Failed', color: '#ef4444', background: 'rgba(239,68,68,0.12)' }
}

function StatusBadge({ status }: { status: JobStatus }) {
  const meta = statusMeta[status]
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 10px',
        borderRadius: '999px',
        background: meta.background,
        color: meta.color,
        fontSize: '12px',
        fontWeight: 700,
        letterSpacing: '0.01em'
      }}
    >
      <span style={{ width: 8, height: 8, borderRadius: '50%', background: meta.color, display: 'inline-block' }} />
      {meta.label}
    </span>
  )
}

export default function FineTuningApp() {
  const { user, initializing } = useAuth(true)
  const [runs, setRuns] = useState<Record<string, JobRunView | null>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState<Record<string, boolean>>({})
  const [jobInventory, setJobInventory] = useState<Set<string>>(new Set())
  const [inventoryError, setInventoryError] = useState<string | null>(null)
  const [datasets, setDatasets] = useState<DatasetDefinition[]>([])
  const [datasetsError, setDatasetsError] = useState<string | null>(null)
  const [selectedDatasetPath, setSelectedDatasetPath] = useState<Record<string, string>>({})
  const [modelNames, setModelNames] = useState<Record<string, string>>(() => {
    const defaults: Record<string, string> = {}
    for (const app of MINI_APPS) defaults[app.id] = app.defaultModelName
    return defaults
  })
  const [sampleInputs, setSampleInputs] = useState<Record<string, string>>({
    multilingual: SAMPLE_DEFAULTS[0],
    sft: 'How do I enable IRSA (IAM Roles for Service Accounts) in EKS?',
    rl: 'Return VALID JSON with keys: task, steps. steps must be an array of strings. No extra text. task=Update kubeconfig for EKS cluster'
  })
  const [uploadBusy, setUploadBusy] = useState<Record<string, boolean>>({})
  const pollers = useRef<Record<string, NodeJS.Timeout>>({})

  useEffect(() => {
    fineTuningApi
      .listJobs()
      .then((resp) => {
        setJobInventory(new Set(resp.jobs.map((j) => j.key)))
        setInventoryError(null)
      })
      .catch((err: any) => {
        setInventoryError(err?.message || 'Unable to load job list')
      })
  }, [])

  useEffect(() => {
    fineTuningApi
      .listDatasets()
      .then((resp) => {
        setDatasets(resp.datasets)
        setDatasetsError(null)
        setSelectedDatasetPath((prev) => {
          const next = { ...prev }
          for (const app of MINI_APPS) {
            if (next[app.id]) continue
            const preferred = resp.datasets.find((d) => app.recommendedDatasetIds.includes(d.id))
            if (preferred) next[app.id] = preferred.path
          }
          return next
        })
      })
      .catch((err: any) => {
        setDatasetsError(err?.message || 'Unable to load dataset list')
      })
  }, [])

  useEffect(() => {
    return () => {
      Object.values(pollers.current).forEach((p) => clearInterval(p))
    }
  }, [])

  const setRunState = (jobKey: string, value: JobRunView | null) => {
    setRuns((prev) => ({ ...prev, [jobKey]: value }))
  }

  const setBusyState = (jobKey: string, value: boolean) => {
    setBusy((prev) => ({ ...prev, [jobKey]: value }))
  }

  const setErrorState = (jobKey: string, value: string) => {
    setErrors((prev) => ({ ...prev, [jobKey]: value }))
  }

  const clearPoller = (jobKey: string) => {
    const poller = pollers.current[jobKey]
    if (poller) {
      clearInterval(poller)
      delete pollers.current[jobKey]
    }
  }

  const refreshDatasets = async () => {
    const resp = await fineTuningApi.listDatasets()
    setDatasets(resp.datasets)
    setDatasetsError(null)
    return resp.datasets
  }

  const handleUpload = async (appId: string, file: File) => {
    setUploadBusy((prev) => ({ ...prev, [appId]: true }))
    try {
      const resp = await fineTuningApi.uploadDataset(file)
      const next = await refreshDatasets()
      const uploaded = next.find((d) => d.path === resp.dataset.path) || resp.dataset
      setSelectedDatasetPath((prev) => ({ ...prev, [appId]: uploaded.path }))
    } catch (err: any) {
      setDatasetsError(err?.message || 'Upload failed')
    } finally {
      setUploadBusy((prev) => ({ ...prev, [appId]: false }))
    }
  }

  const startPolling = (jobKey: string, runId: string) => {
    clearPoller(jobKey)
    pollers.current[jobKey] = setInterval(async () => {
      try {
        const view = await fineTuningApi.getRun(runId, 250)
        setRunState(jobKey, view)
        if (view.status === 'success' || view.status === 'failed') {
          clearPoller(jobKey)
          setBusyState(jobKey, false)
        }
      } catch (err: any) {
        setErrorState(jobKey, err?.message || 'Failed to fetch run status')
        clearPoller(jobKey)
        setBusyState(jobKey, false)
      }
    }, 1800)
  }

  const handleStart = async (
    jobKey: string,
    opts?: { sampleInput?: string; datasetPath?: string; modelName?: string }
  ) => {
    setBusyState(jobKey, true)
    setErrorState(jobKey, '')
    try {
      const view = await fineTuningApi.startJob(jobKey, opts)
      setRunState(jobKey, view)
      if (view.status === 'running' || view.status === 'queued') {
        startPolling(jobKey, view.run_id)
      } else {
        setBusyState(jobKey, false)
      }
    } catch (err: any) {
      setErrorState(jobKey, err?.message || 'Failed to start job')
      setBusyState(jobKey, false)
    }
  }

  const formatTime = (iso: string | null) => {
    if (!iso) return '—'
    const date = new Date(iso)
    if (Number.isNaN(date.getTime())) return '—'
    return date.toLocaleString()
  }

  const logContent = (run: JobRunView | null) => {
    if (!run) return 'No runs yet.'
    if (run.output && run.output.length) return run.output.join('\n')
    return run.status === 'running' ? 'Running... waiting for output.' : 'No output captured.'
  }

  const jobMissing = (jobKey: string) => jobInventory.size > 0 && !jobInventory.has(jobKey)
  const datasetByPath = (path: string | undefined) => datasets.find((d) => d.path === path) || null

  if (initializing || !user) {
    return (
      <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ fontSize: '16px', color: '#cbd5e1' }}>Loading workspace...</div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #0a0f1e 0%, #1a1042 100%)', color: 'white', paddingBottom: '64px' }}>
      <AppHeader appName="LLMs Fine-Tuning" />

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '32px 24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <Card padding="lg">
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ maxWidth: 800 }}>
              <div style={{ fontSize: '18px', fontWeight: 700, marginBottom: 6 }}>LLM tuning control surface</div>
              <div style={{ color: '#cbd5e1', fontSize: '14px', lineHeight: 1.6 }}>
                Run step-by-step jobs with live logs. Each step starts a background process and tails output so you can keep the flow interactive.
              </div>
              {datasetsError && (
                <div style={{ marginTop: 10, padding: '10px 12px', borderRadius: 10, background: 'rgba(239,68,68,0.12)', color: '#fecdd3', fontSize: 13 }}>
                  Dataset registry check failed: {datasetsError}
                </div>
              )}
              {inventoryError && (
                <div style={{ marginTop: 10, padding: '10px 12px', borderRadius: 10, background: 'rgba(239,68,68,0.12)', color: '#fecdd3', fontSize: 13 }}>
                  Job registry check failed: {inventoryError}
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', padding: '10px 14px', background: '#111827', borderRadius: 12, border: '1px solid #1f2937' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />
              <span style={{ color: '#cbd5e1', fontSize: 13 }}>Authenticated as {user.username || user.email}</span>
            </div>
          </div>
        </Card>

        {MINI_APPS.map((app) => (
          <Card key={app.id} padding="lg" hover>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: app.accent }} />
                  <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800 }}>{app.title}</h2>
                </div>
                <div style={{ color: '#cbd5e1', fontSize: 14 }}>{app.subtitle}</div>
                {app.hint && <div style={{ color: '#94a3b8', fontSize: 13, marginTop: 6 }}>{app.hint}</div>}
              </div>
              <div style={{ color: '#94a3b8', fontSize: 12, background: '#0f172a', padding: '8px 12px', borderRadius: 10, border: '1px solid #1f2937' }}>Live tail · Safe commands only</div>
            </div>

            <div style={{ marginBottom: 14, padding: '12px 14px', borderRadius: 12, border: '1px solid #1f2937', background: 'rgba(15,23,42,0.55)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
                <div style={{ maxWidth: 780 }}>
                  <div style={{ fontSize: 13, fontWeight: 800, color: '#e2e8f0', marginBottom: 6 }}>Explanation</div>
                  <div style={{ color: '#cbd5e1', fontSize: 13, lineHeight: 1.55 }}>{app.explanation}</div>
                </div>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 320 }}>
                    <label style={{ color: '#cbd5e1', fontWeight: 700, fontSize: 12 }}>Dataset (built-in or uploaded)</label>
                    <select
                      value={selectedDatasetPath[app.id] || ''}
                      onChange={(e) => setSelectedDatasetPath((prev) => ({ ...prev, [app.id]: e.target.value }))}
                      style={{ background: '#0b1220', color: 'white', border: '1px solid #1f2937', borderRadius: 8, padding: '8px 10px' }}
                    >
                      <option value="" disabled>
                        Select a dataset...
                      </option>
                      {datasets.map((d) => (
                        <option key={d.id} value={d.path}>
                          {d.built_in ? 'Built-in: ' : 'Uploaded: '}
                          {d.name} ({d.rows} rows)
                        </option>
                      ))}
                    </select>
                    {selectedDatasetPath[app.id] && datasetByPath(selectedDatasetPath[app.id]) && (
                      <div style={{ color: '#94a3b8', fontSize: 12 }}>{datasetByPath(selectedDatasetPath[app.id])?.description}</div>
                    )}
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 260 }}>
                    <label style={{ color: '#cbd5e1', fontWeight: 700, fontSize: 12 }}>Base model</label>
                    <input
                      value={modelNames[app.id] ?? app.defaultModelName}
                      onChange={(e) => setModelNames((prev) => ({ ...prev, [app.id]: e.target.value }))}
                      placeholder={app.defaultModelName}
                      style={{ background: '#0b1220', color: 'white', border: '1px solid #1f2937', borderRadius: 8, padding: '8px 10px' }}
                    />
                    <div style={{ color: '#94a3b8', fontSize: 12 }}>Applied to training steps (LoRA).</div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 240 }}>
                    <label style={{ color: '#cbd5e1', fontWeight: 700, fontSize: 12 }}>Upload new dataset (.jsonl)</label>
                    <input
                      type="file"
                      accept=".jsonl"
                      disabled={!!uploadBusy[app.id]}
                      onChange={(e) => {
                        const f = e.target.files?.[0]
                        if (f) void handleUpload(app.id, f)
                        e.currentTarget.value = ''
                      }}
                      style={{ background: '#0b1220', color: 'white', border: '1px solid #1f2937', borderRadius: 8, padding: '8px 10px' }}
                    />
                    <div style={{ color: '#94a3b8', fontSize: 12 }}>{uploadBusy[app.id] ? 'Uploading…' : 'Stored under test-tinker/data/uploads'}</div>
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {app.steps.map((step) => {
                const run = runs[step.jobKey] || null
                const status: JobStatus = run?.status || 'idle'
                const isBusy = busy[step.jobKey] || false
                const error = errors[step.jobKey]
                const isSampleStep = !!step.usesSampleInput
                const sampleInput = sampleInputs[app.id] || ''
                return (
                  <div key={step.id} style={{ padding: '14px 16px', borderRadius: 12, border: '1px solid #1f2937', background: '#0f172a', display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                      <div style={{ maxWidth: 760 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <div style={{ fontWeight: 700 }}>{step.title}</div>
                          <StatusBadge status={status} />
                          {jobMissing(step.jobKey) && <span style={{ fontSize: 12, color: '#fbbf24' }}>Job key not in backend registry</span>}
                        </div>
                        <div style={{ color: '#cbd5e1', fontSize: 13, lineHeight: 1.5 }}>{step.description}</div>
                        {step.note && <div style={{ color: '#94a3b8', fontSize: 12, marginTop: 4 }}>{step.note}</div>}
                        <div style={{ marginTop: 6, color: '#94a3b8', fontSize: 12 }}>
                          Last run: {run ? formatTime(run.start_time) : '—'} • Exit code: {run?.exit_code ?? '—'}
                        </div>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 200 }}>
                        {isSampleStep && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, color: '#cbd5e1', fontSize: 13 }}>
                            <label style={{ color: '#cbd5e1', fontWeight: 600 }}>Sample question</label>
                            {app.id === 'multilingual' && (
                              <select
                                value={sampleInput}
                                onChange={(e) => setSampleInputs((prev) => ({ ...prev, [app.id]: e.target.value }))}
                                style={{ background: '#0b1220', color: 'white', border: '1px solid #1f2937', borderRadius: 8, padding: '8px 10px' }}
                              >
                                {SAMPLE_DEFAULTS.map((q) => (
                                  <option key={q} value={q}>
                                    {q}
                                  </option>
                                ))}
                              </select>
                            )}
                            <input
                              value={sampleInput}
                              onChange={(e) => setSampleInputs((prev) => ({ ...prev, [app.id]: e.target.value }))}
                              placeholder="Or type your own question"
                              style={{ background: '#0b1220', color: 'white', border: '1px solid #1f2937', borderRadius: 8, padding: '8px 10px' }}
                            />
                            <div style={{ color: '#94a3b8', fontSize: 12 }}>
                              The input is passed as SAMPLE_INPUT so you can see output in the live log.
                            </div>
                          </div>
                        )}
                        <button
                          onClick={() =>
                            handleStart(step.jobKey, {
                              sampleInput: isSampleStep ? sampleInput : undefined,
                              datasetPath: selectedDatasetPath[app.id],
                              modelName: modelNames[app.id] || app.defaultModelName
                            })
                          }
                          disabled={isBusy}
                          style={{
                            padding: '10px 16px',
                            borderRadius: 10,
                            border: '1px solid #1f2937',
                            background: isBusy ? '#1f2937' : app.accent,
                            color: 'white',
                            cursor: isBusy ? 'not-allowed' : 'pointer',
                            minWidth: 140,
                            fontWeight: 700
                          }}
                        >
                          {isBusy ? 'Running...' : isSampleStep ? 'Run Sample' : 'Run Step'}
                        </button>
                      </div>
                    </div>

                    {error && (
                      <div style={{ padding: '8px 10px', borderRadius: 10, background: 'rgba(239,68,68,0.12)', color: '#fecdd3', fontSize: 13 }}>
                        {error}
                      </div>
                    )}

                    <div style={{ background: '#0b1220', borderRadius: 10, border: '1px solid #1f2937', padding: '10px 12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                        <span style={{ fontSize: 12, color: '#94a3b8' }}>Live log (tail)</span>
                        <span style={{ fontSize: 11, color: '#64748b' }}>{run?.output?.length || 0} lines</span>
                      </div>
                      <pre
                        style={{
                          margin: 0,
                          whiteSpace: 'pre-wrap',
                          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                          fontSize: 12,
                          color: '#e2e8f0',
                          lineHeight: 1.5,
                          maxHeight: 220,
                          overflow: 'auto'
                        }}
                      >
                        {logContent(run)}
                      </pre>
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>
        ))}

      </div>
    </div>
  )
}
