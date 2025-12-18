'use client'

import { useEffect, useMemo, useState } from 'react'
import { AI_MODELS } from '../config/models'
import { metaApi, type MetaModelsResponse, type MetaModel } from '../services/meta'

let cachedCatalog: MetaModelsResponse | null = null
let inFlight: Promise<MetaModelsResponse> | null = null

const fallbackModels: MetaModel[] = AI_MODELS.map((m) => ({ ...m, enabled: true }))

export function useModelCatalog() {
  const [catalog, setCatalog] = useState<MetaModelsResponse | null>(cachedCatalog)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (cachedCatalog) return
    if (!inFlight) {
      inFlight = metaApi.getModels()
    }

    inFlight
      .then((data) => {
        cachedCatalog = data
        setCatalog(data)
        setError(null)
      })
      .catch((err: any) => {
        setError(err?.message || 'Failed to load models')
      })
      .finally(() => {
        inFlight = null
      })
  }, [])

  return useMemo(() => {
    const models = catalog?.models?.length ? catalog.models : fallbackModels
    const defaultModel = catalog?.defaultModel || AI_MODELS[0]?.id || ''
    return {
      loading: !catalog && !error,
      error,
      models,
      enabledModels: models.filter((m) => m.enabled),
      defaultModel,
      tiers: catalog?.tiers || {},
      providers: catalog?.providers || {},
      cloudProvider: catalog?.cloudProvider,
    }
  }, [catalog, error])
}
