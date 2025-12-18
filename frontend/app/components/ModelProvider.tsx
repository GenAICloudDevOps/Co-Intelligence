'use client'

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { MetaModel } from '../services/meta'
import { useModelCatalog } from '../hooks/useModelCatalog'

type ModelContextValue = {
  models: MetaModel[]
  enabledModels: MetaModel[]
  defaultModel: string
  selectedModel: string
  setSelectedModel: (modelId: string) => void
  clearSelectedModel: () => void
  hasOverride: boolean
  loading: boolean
  error: string | null
}

const ModelContext = createContext<ModelContextValue | null>(null)

const STORAGE_KEY = 'coi_model_override'

function readLegacyOverride(): string | null {
  try {
    return (
      window.localStorage.getItem('lms_model') ||
      window.localStorage.getItem('insurance_ai_model') ||
      null
    )
  } catch {
    return null
  }
}

export function ModelProvider({ children }: { children: React.ReactNode }) {
  const catalog = useModelCatalog()
  const [modelOverride, setModelOverride] = useState<string | null>(null)
  const [overrideLoaded, setOverrideLoaded] = useState(false)

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY)
      if (saved) {
        setModelOverride(saved)
      } else {
        const legacy = readLegacyOverride()
        if (legacy) setModelOverride(legacy)
      }
    } catch {
      // ignore
    } finally {
      setOverrideLoaded(true)
    }
  }, [])

  const enabledIds = useMemo(() => new Set((catalog.enabledModels || []).map((m) => m.id)), [catalog.enabledModels])
  const effectiveOverride = modelOverride && enabledIds.has(modelOverride) ? modelOverride : null

  useEffect(() => {
    if (!overrideLoaded) return
    if (!modelOverride) return
    if (effectiveOverride) return
    if (!catalog.models?.length) return
    try {
      window.localStorage.removeItem(STORAGE_KEY)
    } catch {
      // ignore
    }
    setModelOverride(null)
  }, [catalog.models?.length, effectiveOverride, modelOverride, overrideLoaded])

  const selectedModel = useMemo(() => {
    if (effectiveOverride) return effectiveOverride
    if (catalog.defaultModel && enabledIds.has(catalog.defaultModel)) return catalog.defaultModel
    if (catalog.enabledModels?.length) return catalog.enabledModels[0].id
    if (catalog.defaultModel) return catalog.defaultModel
    if (catalog.models?.length) return catalog.models[0].id
    return ''
  }, [catalog.defaultModel, catalog.enabledModels, catalog.models, effectiveOverride, enabledIds])

  const setSelectedModel = useCallback((modelId: string) => {
    setModelOverride(modelId)
    try {
      window.localStorage.setItem(STORAGE_KEY, modelId)
    } catch {
      // ignore
    }
  }, [])

  const clearSelectedModel = useCallback(() => {
    setModelOverride(null)
    try {
      window.localStorage.removeItem(STORAGE_KEY)
    } catch {
      // ignore
    }
  }, [])

  const value = useMemo<ModelContextValue>(
    () => ({
      models: catalog.models,
      enabledModels: catalog.enabledModels,
      defaultModel: catalog.defaultModel,
      selectedModel,
      setSelectedModel,
      clearSelectedModel,
      hasOverride: Boolean(effectiveOverride),
      loading: catalog.loading || !overrideLoaded,
      error: catalog.error,
    }),
    [catalog.defaultModel, catalog.enabledModels, catalog.error, catalog.loading, catalog.models, effectiveOverride, overrideLoaded, selectedModel, setSelectedModel, clearSelectedModel],
  )

  return <ModelContext.Provider value={value}>{children}</ModelContext.Provider>
}

export function useModel() {
  const value = useContext(ModelContext)
  if (!value) throw new Error('useModel must be used within <ModelProvider />')
  return value
}

