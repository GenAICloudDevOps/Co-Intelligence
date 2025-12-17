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
    return api.post<Dataset>('/api/apps/ml-predictor/upload-dataset', formData)
  },

  async uploadText(payload: { text: string; name: string }): Promise<Dataset> {
    return api.post<Dataset>('/api/apps/ml-predictor/upload-text', payload)
  },

  async getAlgorithms(): Promise<AlgorithmInfo[]> {
    const res = await api.get<{ algorithms: AlgorithmInfo[] }>('/api/apps/ml-predictor/algorithms')
    return res.algorithms || []
  },

  startPredictionStream(body: PredictStreamRequest): Promise<Response> {
    return api.request('/api/apps/ml-predictor/predict/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    })
  }
}
