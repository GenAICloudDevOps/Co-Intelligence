import { api } from '@/app/services/api'

export type DatasetListItem = {
  id: number
  name: string
  source_type: string
  status: string
  glue_database?: string | null
  glue_table?: string | null
  last_run_id?: number | null
  created_at: string
}

export type DatasetDetails = {
  id: number
  name: string
  description?: string | null
  source_type: string
  source_config: any
  raw_s3_uri?: string | null
  curated_s3_uri?: string | null
  glue_database?: string | null
  glue_table?: string | null
  status: string
  last_error?: string | null
  last_run_id?: number | null
  created_at: string
}

export type RunResponse = { run_id: number; execution_arn: string }
export type RunStatus = {
  id: number
  dataset_id: number
  status: string
  execution_arn?: string | null
  execution_status?: string
  execution_start?: string | null
  execution_stop?: string | null
  created_at: string
  updated_at: string
}

export type ChatResponse = {
  intent?: string
  sql?: string
  query_result?: { query_execution_id: string; columns: string[]; rows: string[][] }
  response: string
  error?: string
}

export const daApi = {
  async listDatasets(): Promise<DatasetListItem[]> {
    const res = await api.get<{ datasets: DatasetListItem[] }>('/api/apps/data-analysis/datasets')
    return res.datasets || []
  },

  async getDataset(datasetId: number): Promise<DatasetDetails> {
    return api.get<DatasetDetails>(`/api/apps/data-analysis/datasets/${datasetId}`)
  },

  async uploadDataset(formData: FormData): Promise<{ dataset_id: number; raw_s3_uri: string; run_id?: number; execution_arn?: string }> {
    return api.post<{ dataset_id: number; raw_s3_uri: string; run_id?: number; execution_arn?: string }>('/api/apps/data-analysis/sources/upload?auto_run=true', formData)
  },

  async createS3Dataset(payload: { name: string; s3_uri: string; format?: string }): Promise<{ dataset_id: number; run_id?: number; execution_arn?: string }> {
    return api.post<{ dataset_id: number; run_id?: number; execution_arn?: string }>('/api/apps/data-analysis/sources/s3?auto_run=true', payload)
  },

  async createPostgresDataset(payload: { name: string; schema?: string; table: string; query?: string }): Promise<{ dataset_id: number; run_id?: number; execution_arn?: string }> {
    return api.post<{ dataset_id: number; run_id?: number; execution_arn?: string }>('/api/apps/data-analysis/sources/postgres?auto_run=true', payload)
  },

  async startRun(payload: { dataset_id: number; message?: string; transformation_spec?: any }): Promise<RunResponse> {
    return api.post<RunResponse>('/api/apps/data-analysis/runs', payload)
  },

  async getRun(runId: number): Promise<RunStatus> {
    return api.get<RunStatus>(`/api/apps/data-analysis/runs/${runId}`)
  },

  async chat(payload: { message: string; dataset_id: number; model?: string }): Promise<ChatResponse> {
    return api.post<ChatResponse>('/api/apps/data-analysis/chat', payload)
  },
}
