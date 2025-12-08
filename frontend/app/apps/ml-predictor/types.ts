export interface Dataset {
  id: number
  name: string
  description?: string
  rows: number
  columns: number
  column_names: string[]
}

export interface AlgorithmResult {
  algorithm: string
  display_name: string
  metrics: Record<string, number>
  training_time: string
  rank: number
}

export interface PredictionResult {
  project_id: number
  analysis: {
    problem_type: string
    target_variable: string
    reasoning: string
    analysis_method: string
  }
  dataset_info: {
    name: string
    total_rows: number
    train_rows: number
    test_rows: number
    train_percentage: number
    test_percentage: number
    features: number
    feature_names: string[]
    target_column: string
  }
  algorithm_selection: {
    selected_algorithms: string[]
    reasoning: string
    selection_criteria: string[]
  }
  all_results: AlgorithmResult[]
  winner: {
    algorithm: string
    display_name: string
    metrics: Record<string, number>
    training_time: string
    reason: string
    margin: string
  }
  feature_importance: Record<string, number>
  insights: string[]
}

export interface ProgressUpdate {
  status: string
  step: string
  message: string
  data?: any
}

export interface DatasetPreview {
  id: number
  name: string
  rows: number
  columns: number
  column_names: string[]
  data_types: Record<string, string>
  preview: Record<string, any>[]
  statistics: Record<string, any>
}

export interface AlgorithmInfo {
  name: string
  display_name: string
  type: string
  description: string
  best_for: string[]
  not_good_for: string[]
}
