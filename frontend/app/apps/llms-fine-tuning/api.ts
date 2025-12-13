import { api } from '@/app/services/api'

export type JobStatus = 'idle' | 'queued' | 'running' | 'success' | 'failed'

export interface JobRunView {
  run_id: string
  job_key: string
  status: JobStatus
  start_time: string | null
  end_time: string | null
  exit_code: number | null
  output: string[]
  error?: string | null
}

export interface JobDefinition {
  key: string
  description: string
  working_dir: string
  command: string[]
}

export interface DatasetDefinition {
  id: string
  name: string
  path: string
  description: string
  recommended_for: string[]
  built_in: boolean
  rows: number
  size_bytes: number
}

export const fineTuningApi = {
  async listJobs(): Promise<{ jobs: JobDefinition[] }> {
    return api.get(`/api/apps/llms-fine-tuning/jobs`)
  },
  async listDatasets(): Promise<{ datasets: DatasetDefinition[] }> {
    return api.get(`/api/apps/llms-fine-tuning/datasets`)
  },
  async uploadDataset(file: File): Promise<{ dataset: DatasetDefinition }> {
    const data = new FormData()
    data.append('file', file)
    return api.post(`/api/apps/llms-fine-tuning/datasets/upload`, data)
  },
  async startJob(
    jobKey: string,
    opts?: { sampleInput?: string; datasetPath?: string; modelName?: string }
  ): Promise<JobRunView> {
    return api.post(`/api/apps/llms-fine-tuning/jobs/start`, {
      job_key: jobKey,
      sample_input: opts?.sampleInput,
      dataset_path: opts?.datasetPath,
      model_name: opts?.modelName
    })
  },
  async getRun(runId: string, tail = 200): Promise<JobRunView> {
    return api.get(`/api/apps/llms-fine-tuning/jobs/${runId}?tail=${tail}`)
  }
}
