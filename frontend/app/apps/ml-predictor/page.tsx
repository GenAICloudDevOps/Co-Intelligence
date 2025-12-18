'use client'

import { useAuth } from '@/app/hooks/useAuth'
import AppHeader from '@/app/components/AppHeader'
import Card from '@/app/components/Card'
import { useState, useEffect, useRef } from 'react'
import { useModel } from '@/app/components/ModelProvider'
import { mlApi } from './api'
import { Dataset, DatasetPreview, PredictionResult, ProgressUpdate, AlgorithmInfo } from './types'
import { api } from '@/app/services/api'
import { consumeNdjson } from '@/app/services/stream'

export default function MLPredictor() {
  const { user, loading } = useAuth(true)
  const { selectedModel, setSelectedModel } = useModel()
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null)
  const [problemDescription, setProblemDescription] = useState('')
  const [results, setResults] = useState<PredictionResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [progressLog, setProgressLog] = useState<ProgressUpdate[]>([])
  const [progressStatus, setProgressStatus] = useState<string>('idle')
  const [progressPercent, setProgressPercent] = useState<number>(0)
  const logEndRef = useRef<HTMLDivElement>(null)
  const [datasetPreview, setDatasetPreview] = useState<DatasetPreview | null>(null)
  const [algorithms, setAlgorithms] = useState<AlgorithmInfo[]>([])
  const [showPipeline, setShowPipeline] = useState<boolean>(false)
  
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
    visuals: true,
    features: false,
    predict: true
  })

  useEffect(() => {
    if (user) {
      loadSampleDatasets()
      loadUserDatasets()
      loadAlgorithms()
    }
  }, [user])

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [progressLog])

  const loadSampleDatasets = async () => {
    try {
      const data = await mlApi.getSampleDatasets()
      setDatasets(prev => {
        const currentIds = new Set(prev.map(p => p.id))
        const newD = data.filter(d => !currentIds.has(d.id))
        return [...prev, ...newD]
      })
    } catch (err) {
      console.error('Error loading sample datasets:', err)
    }
  }

  const loadAlgorithms = async () => {
    try {
      const data = await mlApi.getAlgorithms()
      setAlgorithms(data || [])
    } catch (err) {
      console.error('Error loading algorithms:', err)
    }
  }

  const loadUserDatasets = async () => {
    try {
      const data = await mlApi.getUserDatasets()
      setDatasets(prev => {
        const currentIds = new Set(prev.map(p => p.id))
        const newD = data.filter(d => !currentIds.has(d.id))
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

      const newDataset = await mlApi.uploadDataset(formData)
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

  const fetchDatasetPreview = async (datasetId: number) => {
    try {
      const data = await mlApi.getDatasetPreview(datasetId)
      setDatasetPreview(data)
    } catch (err) {
      console.error('Error loading dataset preview:', err)
      setDatasetPreview(null)
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
      const newDataset = await mlApi.uploadText({
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
      
      const result = await api.post<any>('/api/apps/ml-predictor/predict/single', {
        project_id: projectId,
        features: processedFeatures
      })
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
    setProgressPercent(5)
    setProgressStatus('started')
    setShowPipeline(true)

    try {
      const response = await mlApi.startPredictionStream({
        dataset_id: selectedDataset.id,
        problem_description: problemDescription,
        model: selectedModel
      })
      let streamError = ''

      const statusToProgress: Record<string, number> = {
        started: 5,
        analyzing: 20,
        training_start: 40,
        training: 70,
        evaluating: 85,
        saved: 100,
        completed: 100
      }

      const handleUpdate = (update: any) => {
        const pct = statusToProgress[update.status]
        if (pct !== undefined) {
          setProgressPercent(pct)
          setProgressStatus(update.status)
        }

        if (update.status === 'error') {
          streamError = update.message || 'Pipeline error'
          return
        }

        if (update.status === 'saved') {
          setResults(update.data)
          setExpandedSections({ analysis: true, dataset: true, selection: true, results: true, features: true, predict: true })
          return
        }

        setProgressLog(prev => [...prev, update])
      }
      await consumeNdjson(response, handleUpdate)

      if (streamError) {
        throw new Error(streamError)
      }

    } catch (err: any) {
      console.error('Error running prediction:', err)
      setError(err.message || 'Error running prediction')
    } finally {
      setIsLoading(false)
      setProgressStatus('idle')
    }
  }

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  const formatMetricValue = (key: string, value: number) => {
    const keyLower = key.toLowerCase()
    const isPercentMetric = ['accuracy', 'precision', 'recall', 'f1', 'r2', 'r2_score', 'silhouette'].some(m => keyLower.includes(m))
    const isErrorMetric = ['rmse', 'mae', 'mse', 'error'].some(m => keyLower.includes(m))
    if (isPercentMetric && value <= 1) return `${(value * 100).toFixed(1)}%`
    if (isErrorMetric) return value.toLocaleString(undefined, { maximumFractionDigits: 2 })
    if (value < 1 && value > 0) return `${(value * 100).toFixed(1)}%`
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 })
  }

  const renderMetricBars = (metrics: Record<string, number>) => {
    const entries = Object.entries(metrics || {}).slice(0, 4)
    if (!entries.length) return null
    const maxVal = Math.max(...entries.map(([, v]) => Math.abs(v || 0)), 1)
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {entries.map(([key, val], idx) => {
          const normalized = Math.min(Math.abs(val) / maxVal, 1)
          const color = ['#6366f1', '#8b5cf6', '#22c55e', '#f59e0b'][idx % 4]
          return (
            <div key={key}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: '#e2e8f0' }}>
                <span>{key.replace(/_/g, ' ')}</span>
                <span style={{ color }}>{formatMetricValue(key, val)}</span>
              </div>
              <div style={{ height: '8px', background: '#1e293b', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ width: `${normalized * 100}%`, height: '100%', background: color, transition: 'width 0.3s ease' }} />
              </div>
            </div>
          )
        })}
      </div>
    )
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
                    if (ds?.id) {
                      fetchDatasetPreview(ds.id)
                    } else {
                      setDatasetPreview(null)
                    }
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
              
              {datasetPreview && (
                <div style={{ marginTop: '8px', padding: '12px', background: '#0f172a', borderRadius: '8px', border: '1px solid #1e293b' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Dataset Preview</div>
                      <div style={{ fontSize: '1rem', fontWeight: 'bold' }}>{datasetPreview.name}</div>
                    </div>
                    <div style={{ display: 'flex', gap: '12px', fontSize: '0.85rem', color: '#94a3b8' }}>
                      <span>Rows: <strong>{datasetPreview.rows}</strong></span>
                      <span>Columns: <strong>{datasetPreview.columns}</strong></span>
                    </div>
                  </div>
                  <div style={{ overflowX: 'auto', marginBottom: '8px' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                      <thead>
                        <tr>
                          {datasetPreview.column_names.slice(0, 6).map((col) => (
                            <th key={col} style={{ padding: '6px', textAlign: 'left', color: '#94a3b8', borderBottom: '1px solid #1e293b' }}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {datasetPreview.preview.slice(0, 3).map((row, idx) => (
                          <tr key={idx} style={{ borderBottom: '1px solid #1e293b' }}>
                            {datasetPreview.column_names.slice(0, 6).map((col) => (
                              <td key={col} style={{ padding: '6px', color: '#e2e8f0', maxWidth: '200px', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                                {String((row as any)[col] ?? '')}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {datasetPreview.column_names.slice(0, 8).map((col) => (
                      <span key={col} style={{ padding: '6px 10px', background: '#1e293b', borderRadius: '6px', fontSize: '0.85rem', color: '#cbd5e1' }}>
                        {col} <span style={{ color: '#64748b' }}>({datasetPreview.data_types?.[col] || 'unknown'})</span>
                      </span>
                    ))}
                    {datasetPreview.column_names.length > 8 && (
                      <span style={{ padding: '6px 10px', color: '#64748b', fontSize: '0.85rem' }}>+{datasetPreview.column_names.length - 8} more</span>
                    )}
                  </div>
                  <div style={{ color: '#64748b', fontSize: '0.8rem', marginTop: '8px' }}>
                    💡 Tip: Describe what you want to predict (e.g., "predict {datasetPreview.column_names?.[datasetPreview.column_names.length - 1] || 'target'}")
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

            {algorithms.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '0.9rem', color: '#94a3b8', marginBottom: '6px' }}>Available algorithms</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '8px' }}>
                  {algorithms.slice(0, 9).map(algo => (
                    <div key={algo.name} style={{ padding: '10px', background: '#0f172a', borderRadius: '8px', border: '1px solid #1e293b' }}>
                      <div style={{ fontWeight: 'bold', color: '#e2e8f0', marginBottom: '4px' }}>{algo.display_name}</div>
                      <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '4px' }}>{algo.type}</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {algo.best_for.slice(0, 2).map((tag: string) => (
                          <span key={tag} style={{ padding: '2px 6px', background: '#1e293b', borderRadius: '4px', fontSize: '0.75rem', color: '#cbd5e1' }}>{tag}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

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
              {(isLoading || (showPipeline && progressLog.length > 0)) && (
                <Card padding="lg">
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <h3 style={{ margin: 0, fontSize: '1.2rem', color: '#6366f1' }}>🔄 Processing Pipeline</h3>
                    {results && (
                      <button
                        onClick={() => setShowPipeline(v => !v)}
                        style={{ background: '#1e293b', color: '#e2e8f0', border: '1px solid #334155', borderRadius: '6px', padding: '6px 10px', cursor: 'pointer', fontSize: '0.85rem' }}
                      >
                        {showPipeline ? 'Hide details' : 'Show details'}
                      </button>
                    )}
                  </div>
                  {(isLoading || showPipeline) && (
                    <>
                      <div style={{ marginBottom: '12px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: '#94a3b8' }}>
                          <span>Status: {progressStatus}</span>
                          <span>{progressPercent}%</span>
                        </div>
                        <div style={{ height: '8px', background: '#1e293b', borderRadius: '6px', overflow: 'hidden', marginTop: '6px' }}>
                          <div style={{ width: `${progressPercent}%`, background: '#6366f1', height: '100%', transition: 'width 0.3s ease' }} />
                        </div>
                      </div>
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
                            <span style={{ color: '#64748b', fontSize: '0.8rem' }}>[{(log.step || log.status || 'status').toUpperCase()}]</span>{' '}
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
                    </>
                  )}
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

                  {/* Prediction Visuals */}
                  <Card padding="lg">
                    <SectionHeader title="Prediction Visuals" icon="📊" section="visuals" />
                    {expandedSections.visuals && (
                      <>
                        {renderMetricBars(results.winner.metrics)}
                        <div style={{ marginTop: '12px', fontSize: '0.85rem', color: '#94a3b8' }}>
                          Visualizing top metrics for the winning model. Batch predictions will render tables below; single predictions can be run in the form at the bottom.
                        </div>
                      </>
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
