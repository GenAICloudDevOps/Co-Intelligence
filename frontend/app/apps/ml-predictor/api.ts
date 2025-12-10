import { api } from '@/app/services/api'
import { Dataset, DatasetPreview, AlgorithmInfo } from './types'

export interface PredictStreamRequest {
  dataset_id: number
  problem_description: string
  model: string
}

export const mlApi = {
  async getSampleDatasets(): Promise<Dataset[]> {
    const res = await api.get<{ datasets: Dataset[] }>('/api/apps/ml-predictor/sample-datasets')
    return res.datasets || []
  },

  async getUserDatasets(): Promise<Dataset[]> {
    const res = await api.get<{ datasets: Dataset[] }>('/api/apps/ml-predictor/datasets')
    return res.datasets || []
  },

  async getDatasetPreview(datasetId: number): Promise<DatasetPreview> {
    return api.get<DatasetPreview>(`/api/apps/ml-predictor/datasets/${datasetId}/preview`)
  },

  async uploadDataset(formData: FormData): Promise<Dataset> {
    const response = await fetch('/api/apps/ml-predictor/upload-dataset', {
      method: 'POST',
      credentials: 'include',
      body: formData
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({}))
      throw new Error(err.detail || 'Upload failed')
    }
    return response.json()
  },

  async uploadText(payload: { text: string; name: string }): Promise<Dataset> {
    return api.post<Dataset>('/api/apps/ml-predictor/upload-text', payload)
  },

  async getAlgorithms(): Promise<AlgorithmInfo[]> {
    const res = await api.get<{ algorithms: AlgorithmInfo[] }>('/api/apps/ml-predictor/algorithms')
    return res.algorithms || []
  },

  startPredictionStream(body: PredictStreamRequest): Promise<Response> {
    return fetch(api.getStreamUrl('/api/apps/ml-predictor/predict/stream'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      credentials: 'include',
      body: JSON.stringify(body)
    })
  }
}
