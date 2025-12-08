'use client'

import { useAuth } from '@/app/hooks/useAuth'
import AppHeader from '@/app/components/AppHeader'
import Card from '@/app/components/Card'
import { useState, useEffect, useRef } from 'react'
import { DEFAULT_MODEL } from '@/app/config/models'
import { api } from '@/app/services/api'

interface Dataset {
  id: number
  name: string
  description: string
  rows: number
  columns: number
  column_names: string[]
}

interface AlgorithmResult {
  algorithm: string
  display_name: string
  metrics: Record<string, number>
  training_time: string
  rank: number
}

interface PredictionResult {
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

interface ProgressUpdate {
  status: string
  step: string
  message: string
  data?: any
}

export default function MLPredictor() {
  const { user, loading } = useAuth(true)
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null)
  const [problemDescription, setProblemDescription] = useState('')
  const [selectedModel, setSelectedModel] = useState(DEFAULT_MODEL)
  const [results, setResults] = useState<PredictionResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [progressLog, setProgressLog] = useState<ProgressUpdate[]>([])
  const logEndRef = useRef<HTMLDivElement>(null)
  
  // Upload States
  const [uploadMode, setUploadMode] = useState<'none' | 'file' | 'text'>('none')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [pasteText, setPasteText] = useState('')
  const [datasetName, setDatasetName] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    analysis: true,
    dataset: false,
    selection: false,
    results: true,
    features: false,
    predict: true
  })

  useEffect(() => {
    if (user) {
      loadSampleDatasets()
      loadUserDatasets()
    }
  }, [user])

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [progressLog])

  const loadSampleDatasets = async () => {
    try {
      const data = await api.get<{ datasets: Dataset[] }>('/api/apps/ml-predictor/sample-datasets')
      setDatasets(prev => {
        const currentIds = new Set(prev.map(p => p.id))
        const newD = data.datasets.filter(d => !currentIds.has(d.id))
        return [...prev, ...newD]
      })
    } catch (err) {
      console.error('Error loading sample datasets:', err)
    }
  }

  const loadUserDatasets = async () => {
    try {
      const data = await api.get<{ datasets: Dataset[] }>('/api/apps/ml-predictor/datasets')
      setDatasets(prev => {
        const currentIds = new Set(prev.map(p => p.id))
        const newD = data.datasets.filter(d => !currentIds.has(d.id))
        return [...prev, ...newD]
      })
    } catch (err) {
      console.error('Error loading user datasets:', err)
    }
  }

  const handleFileUpload = async () => {
    if (!uploadFile || !datasetName) {
      setError('Please select a file and provide a name')
      return
    }
    
    setIsUploading(true)
    setError('')
    
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('name', datasetName)
      
      const response = await fetch('/api/apps/ml-predictor/upload-dataset', {
        method: 'POST',
        headers: api.getAuthHeaders(),
        body: formData
      })
      
      if (!response.ok) throw new Error('Upload failed')
      
      const newDataset = await response.json()
      setDatasets(prev => [...prev, newDataset])
      setSelectedDataset(newDataset)
      setUploadMode('none')
      setUploadFile(null)
      setDatasetName('')
      
    } catch (err: any) {
      setError(err.message || 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const handleTextUpload = async () => {
    if (!pasteText || !datasetName) {
      setError('Please provide text and a name')
      return
    }
    
    setIsUploading(true)
    setError('')
    
    try {
      const newDataset = await api.post<Dataset>('/api/apps/ml-predictor/upload-text', {
        text: pasteText,
        name: datasetName
      })
      
      setDatasets(prev => [...prev, newDataset])
      setSelectedDataset(newDataset)
      setUploadMode('none')
      setPasteText('')
      setDatasetName('')
      
    } catch (err: any) {
      setError(err.message || 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

// Single Prediction Component
function SinglePrediction({ projectId, featureNames, problemType }: { projectId: number, featureNames: string[], problemType: string }) {
  const [features, setFeatures] = useState<Record<string, string>>({})
  const [prediction, setPrediction] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handlePredict = async () => {
    setLoading(true)
    setError('')
    setPrediction(null)
    
    try {
      // Convert string values to numbers where possible
      const processedFeatures: Record<string, any> = {}
      for (const [key, value] of Object.entries(features)) {
        const num = parseFloat(value)
        processedFeatures[key] = isNaN(num) ? value : num
      }
      
      const response = await fetch('/api/apps/ml-predictor/predict/single', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          project_id: projectId,
          features: processedFeatures
        })
      })
      
      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || 'Prediction failed')
      }
      
      const result = await response.json()
      setPrediction(result)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '0 8px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginBottom: '16px' }}>
        {featureNames.map((feature) => (
          <div key={feature}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '4px' }}>{feature}</label>
            <input
              type="text"
              value={features[feature] || ''}
              onChange={(e) => setFeatures(prev => ({ ...prev, [feature]: e.target.value }))}
              placeholder={`Enter ${feature}`}
              style={{ width: '100%', padding: '8px', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: 'white', fontSize: '0.9rem' }}
            />
          </div>
        ))}
      </div>
      
      <button
        onClick={handlePredict}
        disabled={loading || Object.keys(features).length === 0}
        style={{ width: '100%', padding: '12px', background: loading ? '#475569' : '#10b981', border: 'none', borderRadius: '8px', color: 'white', fontWeight: 'bold', cursor: loading ? 'not-allowed' : 'pointer', marginBottom: '12px' }}
      >
        {loading ? '⏳ Predicting...' : '🎯 Predict'}
      </button>
      
      {error && (
        <div style={{ padding: '12px', background: '#7f1d1d', borderRadius: '8px', color: '#fca5a5', marginBottom: '12px' }}>{error}</div>
      )}
      
      {prediction && (
        <div style={{ padding: '16px', background: '#0f172a', borderRadius: '8px', textAlign: 'center' }}>
          <div style={{ fontSize: '0.9rem', color: '#94a3b8', marginBottom: '8px' }}>Predicted {problemType === 'regression' ? 'Value' : 'Class'}</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#6366f1' }}>
            {typeof prediction.prediction === 'number' 
              ? prediction.prediction.toLocaleString(undefined, { maximumFractionDigits: 2 })
              : prediction.prediction}
          </div>
          {prediction.confidence && (
            <div style={{ fontSize: '0.9rem', color: '#10b981', marginTop: '8px' }}>
              Confidence: {prediction.confidence.toFixed(1)}%
            </div>
          )}
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '8px' }}>
            Model: {prediction.model_used}
          </div>
        </div>
      )}
    </div>
  )
}

  const handlePredict = async () => {
    if (!selectedDataset || !problemDescription.trim()) {
      setError('Please select a dataset and describe the problem')
      return
    }

    setIsLoading(true)
    setError('')
    setResults(null)
    setProgressLog([])

    try {
      const response = await fetch(api.getStreamUrl('/api/apps/ml-predictor/predict/stream'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...api.getAuthHeaders()
        },
        body: JSON.stringify({
          dataset_id: selectedDataset.id,
          problem_description: problemDescription,
          model: selectedModel
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(errorData.detail || `Failed to start prediction: ${response.status} ${response.statusText}`)
      }

      if (!response.body) throw new Error('No response body')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let completeMessages = []

      const processBuffer = () => {
        // Split buffer into potential JSON messages
        const parts = buffer.split('\n')
        let newBuffer = ''
        
        for (let i = 0; i < parts.length; i++) {
          const part = parts[i].trim()
          if (!part) continue
          
          try {
            // Try to parse as JSON
            const update = JSON.parse(part)
            completeMessages.push(update)
          } catch (e) {
            // If parsing fails, this might be a partial message
            // Keep it in buffer for next iteration
            if (i === parts.length - 1) {
              // Last part might be incomplete
              newBuffer = part
            } else {
              // Middle parts should be complete, log the error
              console.error('Error parsing part:', part, 'Error:', e)
            }
          }
        }
        
        return newBuffer
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        buffer += chunk
        
        // Process any complete messages in the buffer
        buffer = processBuffer()
      }
      
      // Process any remaining messages after stream ends
      if (buffer.trim()) {
        try {
          const update = JSON.parse(buffer)
          completeMessages.push(update)
        } catch (e) {
          console.error('Error parsing final buffer:', buffer, 'Error:', e)
        }
      }
      
      // Process all complete messages
      for (const update of completeMessages) {
        if (update.status === 'error') {
          throw new Error(update.message)
        }
        
        if (update.status === 'saved') {
          setResults(update.data)
          setExpandedSections({ analysis: true, dataset: true, selection: true, results: true, features: true })
        } else {
          setProgressLog(prev => [...prev, update])
        }
      }

    } catch (err: any) {
      console.error('Error running prediction:', err)
      setError(err.message || 'Error running prediction')
    } finally {
      setIsLoading(false)
    }
  }

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        Loading...
      </div>
    )
  }

  const SectionHeader = ({ title, icon, section }: { title: string, icon: string, section: string }) => (
    <div 
      onClick={() => toggleSection(section)}
      style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        cursor: 'pointer',
        padding: '12px 16px',
        background: '#1e293b',
        borderRadius: '8px',
        marginBottom: expandedSections[section] ? '12px' : '0'
      }}
    >
      <span style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>{icon} {title}</span>
      <span style={{ color: '#64748b' }}>{expandedSections[section] ? '▼' : '▶'}</span>
    </div>
  )

  return (
    <div style={{ minHeight: '100vh', background: '#0f172a', color: 'white' }}>
      <AppHeader 
        appName="ML Predictor" 
        showModelSelector={true}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
      />
      
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: (results || isLoading) ? '400px 1fr' : '1fr', gap: '24px' }}>
          {/* Left Panel - Input */}
          <Card padding="lg">
            <h2 style={{ fontSize: '1.5rem', marginBottom: '24px' }}>🤖 ML Prediction</h2>
            
            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Select Dataset</label>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                <select
                  value={selectedDataset?.id || ''}
                  onChange={(e) => {
                    const ds = datasets.find(d => d.id === parseInt(e.target.value))
                    setSelectedDataset(ds || null)
                  }}
                  style={{ flex: 1, padding: '12px', background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', color: 'white' }}
                >
                  <option value="">Choose a dataset...</option>
                  {datasets.map(d => (
                    <option key={d.id} value={d.id}>{d.name} ({d.rows} rows)</option>
                  ))}
                </select>
                <button 
                  onClick={() => setUploadMode(m => m === 'none' ? 'file' : 'none')}
                  style={{ padding: '0 12px', background: '#334155', border: 'none', borderRadius: '8px', color: 'white', cursor: 'pointer' }}
                  title="Upload New"
                >
                  +
                </button>
              </div>
              
              {/* Upload Interface */}
              {uploadMode !== 'none' && (
                <div style={{ padding: '12px', background: '#1e293b', borderRadius: '8px', marginBottom: '12px', animation: 'fadeIn 0.3s' }}>
                   <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                     <button 
                       onClick={() => setUploadMode('file')}
                       style={{ flex: 1, padding: '8px', background: uploadMode === 'file' ? '#6366f1' : '#334155', border: 'none', borderRadius: '4px', color: 'white', cursor: 'pointer' }}
                     >
                       File
                     </button>
                     <button 
                       onClick={() => setUploadMode('text')}
                       style={{ flex: 1, padding: '8px', background: uploadMode === 'text' ? '#6366f1' : '#334155', border: 'none', borderRadius: '4px', color: 'white', cursor: 'pointer' }}
                     >
                       Paste
                     </button>
                   </div>
                   
                   <input 
                     type="text" 
                     placeholder="Dataset Name" 
                     value={datasetName}
                     onChange={e => setDatasetName(e.target.value)}
                     style={{ width: '100%', padding: '8px', marginBottom: '8px', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: 'white' }}
                   />
                   
                   {uploadMode === 'file' ? (
                     <input 
                       type="file" 
                       accept=".csv,.xlsx,.xls,.pdf,.docx,.doc"
                       onChange={e => setUploadFile(e.target.files?.[0] || null)}
                       style={{ width: '100%', marginBottom: '8px', color: '#94a3b8' }}
                     />
                   ) : (
                     <textarea 
                        placeholder="Paste your CSV data here..."
                        value={pasteText}
                        onChange={e => setPasteText(e.target.value)}
                        style={{ width: '100%', height: '100px', padding: '8px', marginBottom: '8px', background: '#0f172a', border: '1px solid #334155', borderRadius: '4px', color: 'white', fontFamily: 'monospace' }}
                     />
                   )}
                   
                   <button
                     onClick={uploadMode === 'file' ? handleFileUpload : handleTextUpload}
                     disabled={isUploading}
                     style={{ width: '100%', padding: '8px', background: isUploading ? '#475569' : '#10b981', border: 'none', borderRadius: '4px', color: 'white', cursor: isUploading ? 'not-allowed' : 'pointer' }}
                   >
                     {isUploading ? 'Uploading...' : 'Save Dataset'}
                   </button>
                </div>
              )}
              
              {selectedDataset && (
                <div style={{ marginTop: '8px', padding: '10px', background: '#1e293b', borderRadius: '6px', fontSize: '0.85rem' }}>
                  <div style={{ color: '#94a3b8', marginBottom: '8px' }}>
                    {selectedDataset.rows} rows × {selectedDataset.columns} columns
                  </div>
                  {selectedDataset.column_names && (
                    <div style={{ marginBottom: '8px' }}>
                      <div style={{ color: '#64748b', fontSize: '0.75rem', marginBottom: '4px' }}>Columns:</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {selectedDataset.column_names.slice(0, 8).map((col, i) => (
                          <span key={i} style={{ padding: '2px 6px', background: '#334155', borderRadius: '4px', fontSize: '0.75rem' }}>{col}</span>
                        ))}
                        {selectedDataset.column_names.length > 8 && (
                          <span style={{ padding: '2px 6px', color: '#64748b', fontSize: '0.75rem' }}>+{selectedDataset.column_names.length - 8} more</span>
                        )}
                      </div>
                    </div>
                  )}
                  <div style={{ color: '#64748b', fontSize: '0.75rem' }}>
                    💡 Tip: Describe what you want to predict (e.g., "predict {selectedDataset.column_names?.[selectedDataset.column_names.length - 1] || 'target'}")
                  </div>
                </div>
              )}
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>Describe Problem</label>
              <textarea
                value={problemDescription}
                onChange={(e) => setProblemDescription(e.target.value)}
                placeholder="e.g., Predict house prices, Classify iris flowers by species..."
                style={{ width: '100%', height: '100px', padding: '12px', background: '#0f172a', border: '1px solid #334155', borderRadius: '8px', color: 'white', resize: 'vertical' }}
              />
            </div>

            {error && (
              <div style={{ marginBottom: '16px', padding: '12px', background: '#7f1d1d', borderRadius: '8px', color: '#fca5a5' }}>{error}</div>
            )}

            <button
              onClick={handlePredict}
              disabled={isLoading}
              style={{ width: '100%', padding: '14px', background: isLoading ? '#475569' : '#6366f1', border: 'none', borderRadius: '8px', color: 'white', fontWeight: 'bold', cursor: isLoading ? 'not-allowed' : 'pointer' }}
            >
              {isLoading ? '⏳ Processing...' : '🚀 Run Prediction'}
            </button>
          </Card>

          {/* Right Panel - Loading State or Results */}
          {(isLoading || results) && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              
              {/* Progress Dashboard (Visible during loading) */}
              {isLoading && (
                <Card padding="lg">
                  <h3 style={{ marginBottom: '16px', fontSize: '1.2rem', color: '#6366f1' }}>🔄 Processing Pipeline</h3>
                  <div style={{ 
                    background: '#0f172a', 
                    padding: '16px', 
                    borderRadius: '8px', 
                    height: '300px', 
                    overflowY: 'auto',
                    fontFamily: 'monospace',
                    fontSize: '0.9rem'
                  }}>
                    {progressLog.map((log, i) => (
                      <div key={i} style={{ marginBottom: '8px', borderLeft: '2px solid #6366f1', paddingLeft: '10px' }}>
                        <span style={{ color: '#64748b', fontSize: '0.8rem' }}>[{log.step.toUpperCase()}]</span>{' '}
                        <span style={{ color: '#e2e8f0' }}>{log.message}</span>
                        {log.data && (
                          <div style={{ marginTop: '4px', padding: '8px', background: '#1e293b', borderRadius: '4px', fontSize: '0.8rem', color: '#94a3b8' }}>
                            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(log.data, null, 2)}</pre>
                          </div>
                        )}
                      </div>
                    ))}
                    <div ref={logEndRef} />
                  </div>
                </Card>
              )}

              {/* Results (Visible when done) */}
              {results && (
                <>
                  {/* Winner Banner */}
                  <Card padding="lg">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                      <div style={{ fontSize: '3rem' }}>🏆</div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Best Performing Algorithm</div>
                        <div style={{ fontSize: '1.8rem', fontWeight: 'bold', color: '#6366f1' }}>{results.winner.display_name}</div>
                        <div style={{ fontSize: '0.9rem', color: '#10b981' }}>{results.winner.reason}</div>
                        <div style={{ fontSize: '0.85rem', color: '#64748b' }}>{results.winner.margin}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        {Object.entries(results.winner.metrics).slice(0, 2).map(([key, value]) => {
                          const keyLower = key.toLowerCase();
                          const isPercentMetric = ['accuracy', 'precision', 'recall', 'f1', 'r2', 'r2_score', 'silhouette'].some(m => keyLower.includes(m));
                          const isErrorMetric = ['rmse', 'mae', 'mse', 'error'].some(m => keyLower.includes(m));
                          
                          let displayValue;
                          if (typeof value === 'number') {
                            if (isPercentMetric && value <= 1) {
                              displayValue = `${(value * 100).toFixed(1)}%`;
                            } else if (isErrorMetric) {
                              displayValue = value.toLocaleString(undefined, { maximumFractionDigits: 2 });
                            } else if (value < 1 && value > 0) {
                              displayValue = `${(value * 100).toFixed(1)}%`;
                            } else {
                              displayValue = value.toLocaleString(undefined, { maximumFractionDigits: 2 });
                            }
                          } else {
                            displayValue = value;
                          }
                          
                          return (
                            <div key={key} style={{ marginBottom: '4px' }}>
                              <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{key.replace(/_/g, ' ').toUpperCase()}: </span>
                              <span style={{ color: '#6366f1', fontWeight: 'bold' }}>{displayValue}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </Card>

                  {/* Insights Summary */}
                  <Card padding="lg">
                    <h3 style={{ marginBottom: '12px', fontSize: '1.1rem' }}>💡 Key Insights</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {results.insights.filter(i => i).map((insight, i) => (
                        <div key={i} style={{ padding: '8px 12px', background: '#0f172a', borderRadius: '6px', fontSize: '0.9rem' }}>
                          {insight}
                        </div>
                      ))}
                    </div>
                  </Card>

                  {/* Problem Analysis */}
                  <Card padding="lg">
                    <SectionHeader title="Problem Analysis" icon="🎯" section="analysis" />
                    {expandedSections.analysis && (
                      <div style={{ padding: '0 8px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                          <div style={{ padding: '12px', background: '#0f172a', borderRadius: '8px' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Problem Type</div>
                            <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: results.analysis.problem_type === 'classification' ? '#6366f1' : '#10b981' }}>
                              {results.analysis.problem_type.toUpperCase()}
                            </div>
                          </div>
                          <div style={{ padding: '12px', background: '#0f172a', borderRadius: '8px' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Target Variable</div>
                            <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{results.analysis.target_variable}</div>
                          </div>
                        </div>
                        <div style={{ marginTop: '12px', padding: '12px', background: '#0f172a', borderRadius: '8px' }}>
                          <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '4px' }}>Reasoning</div>
                          <div style={{ fontSize: '0.9rem' }}>{results.analysis.reasoning}</div>
                        </div>
                      </div>
                    )}
                  </Card>

                  {/* Dataset Info */}
                  <Card padding="lg">
                    <SectionHeader title="Dataset Information" icon="📊" section="dataset" />
                    {expandedSections.dataset && (
                      <div style={{ padding: '0 8px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '12px' }}>
                          <div style={{ padding: '12px', background: '#0f172a', borderRadius: '8px', textAlign: 'center' }}>
                            <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#6366f1' }}>{results.dataset_info.total_rows}</div>
                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Total Rows</div>
                          </div>
                          <div style={{ padding: '12px', background: '#0f172a', borderRadius: '8px', textAlign: 'center' }}>
                            <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#10b981' }}>{results.dataset_info.train_rows}</div>
                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Training ({results.dataset_info.train_percentage}%)</div>
                          </div>
                          <div style={{ padding: '12px', background: '#0f172a', borderRadius: '8px', textAlign: 'center' }}>
                            <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#f59e0b' }}>{results.dataset_info.test_rows}</div>
                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Testing ({results.dataset_info.test_percentage}%)</div>
                          </div>
                          <div style={{ padding: '12px', background: '#0f172a', borderRadius: '8px', textAlign: 'center' }}>
                            <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#ec4899' }}>{results.dataset_info.features}</div>
                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Features</div>
                          </div>
                        </div>
                        <div style={{ padding: '12px', background: '#0f172a', borderRadius: '8px' }}>
                          <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '4px' }}>Features Used</div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                            {results.dataset_info.feature_names.map((f, i) => (
                              <span key={i} style={{ padding: '4px 8px', background: '#334155', borderRadius: '4px', fontSize: '0.85rem' }}>{f}</span>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </Card>

                  {/* Algorithm Selection */}
                  <Card padding="lg">
                    <SectionHeader title="Algorithm Selection" icon="🧠" section="selection" />
                    {expandedSections.selection && (
                      <div style={{ padding: '0 8px' }}>
                        <div style={{ padding: '12px', background: '#0f172a', borderRadius: '8px', marginBottom: '12px' }}>
                          <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '4px' }}>Why These Algorithms?</div>
                          <div style={{ fontSize: '0.9rem' }}>{results.algorithm_selection.reasoning}</div>
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                          {results.algorithm_selection.selection_criteria.map((c, i) => (
                            <span key={i} style={{ padding: '6px 12px', background: '#334155', borderRadius: '6px', fontSize: '0.85rem' }}>✓ {c}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </Card>

                  {/* All Algorithm Results */}
                  <Card padding="lg">
                    <SectionHeader title="Algorithm Comparison" icon="📈" section="results" />
                    {expandedSections.results && (
                      <div style={{ padding: '0 8px' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                          <thead>
                            <tr style={{ borderBottom: '1px solid #334155' }}>
                              <th style={{ padding: '12px', textAlign: 'left', color: '#94a3b8' }}>Rank</th>
                              <th style={{ padding: '12px', textAlign: 'left', color: '#94a3b8' }}>Algorithm</th>
                              <th style={{ padding: '12px', textAlign: 'left', color: '#94a3b8' }}>Metrics</th>
                              <th style={{ padding: '12px', textAlign: 'right', color: '#94a3b8' }}>Time</th>
                            </tr>
                          </thead>
                          <tbody>
                            {results.all_results.map((r, i) => (
                              <tr key={i} style={{ borderBottom: '1px solid #1e293b', background: i === 0 ? 'rgba(99, 102, 241, 0.1)' : 'transparent' }}>
                                <td style={{ padding: '12px' }}>
                                  {i === 0 ? '🥇' : i === 1 ? '🥈' : '🥉'} #{r.rank}
                                </td>
                                <td style={{ padding: '12px', fontWeight: i === 0 ? 'bold' : 'normal' }}>
                                  {r.display_name}
                                </td>
                                <td style={{ padding: '12px' }}>
                                  <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                                    {Object.entries(r.metrics).map(([key, value]) => {
                                      const keyLower = key.toLowerCase();
                                      const isPercentMetric = ['accuracy', 'precision', 'recall', 'f1', 'r2', 'r2_score', 'silhouette'].some(m => keyLower.includes(m));
                                      const isErrorMetric = ['rmse', 'mae', 'mse', 'error'].some(m => keyLower.includes(m));
                                      
                                      let displayValue;
                                      if (typeof value === 'number') {
                                        if (isPercentMetric && value <= 1) {
                                          displayValue = `${(value * 100).toFixed(1)}%`;
                                        } else if (isErrorMetric) {
                                          displayValue = value.toLocaleString(undefined, { maximumFractionDigits: 2 });
                                        } else if (value < 1 && value > 0) {
                                          displayValue = `${(value * 100).toFixed(1)}%`;
                                        } else {
                                          displayValue = value.toLocaleString(undefined, { maximumFractionDigits: 2 });
                                        }
                                      } else {
                                        displayValue = value;
                                      }
                                      
                                      return (
                                        <span key={key} style={{ fontSize: '0.85rem' }}>
                                          <span style={{ color: '#64748b' }}>{key.replace(/_/g, ' ').toUpperCase()}: </span>
                                          <span style={{ color: i === 0 ? '#6366f1' : '#94a3b8', fontWeight: i === 0 ? 'bold' : 'normal' }}>
                                            {displayValue}
                                          </span>
                                        </span>
                                      );
                                    })}
                                  </div>
                                </td>
                                <td style={{ padding: '12px', textAlign: 'right', color: '#64748b' }}>{r.training_time}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </Card>

                  {/* Feature Importance */}
                  {Object.keys(results.feature_importance).length > 0 && (
                    <Card padding="lg">
                      <SectionHeader title="Feature Importance" icon="🔍" section="features" />
                      {expandedSections.features && (
                        <div style={{ padding: '0 8px' }}>
                          {Object.entries(results.feature_importance).map(([feature, importance], i) => (
                            <div key={i} style={{ marginBottom: '12px' }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                <span style={{ fontSize: '0.9rem' }}>{feature}</span>
                                <span style={{ color: '#6366f1', fontWeight: 'bold' }}>{(importance * 100).toFixed(1)}%</span>
                              </div>
                              <div style={{ height: '8px', background: '#1e293b', borderRadius: '4px', overflow: 'hidden' }}>
                                <div style={{ 
                                  height: '100%', 
                                  width: `${importance * 100}%`, 
                                  background: i === 0 ? '#6366f1' : i === 1 ? '#8b5cf6' : '#a78bfa',
                                  borderRadius: '4px',
                                  transition: 'width 0.5s ease'
                                }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </Card>
                  )}

                  {/* Single Prediction */}
                  <Card padding="lg">
                    <SectionHeader title="Make a Prediction" icon="🎯" section="predict" />
                    {expandedSections.predict && (
                      <SinglePrediction 
                        projectId={results.project_id}
                        featureNames={results.dataset_info.feature_names}
                        problemType={results.analysis.problem_type}
                      />
                    )}
                  </Card>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
