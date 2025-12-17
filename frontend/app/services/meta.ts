import { api } from './api'

export type MetaApp = {
  id: string
  name: string
  description: string[]
  icon: string
  color: string
  route: string
  status: 'active' | 'soon'
  requiresAuth: boolean
}

export type MetaAppsResponse = {
  apps: MetaApp[]
  cloudProvider: string
}

export type MetaModel = {
  id: string
  name: string
  provider: string
  enabled: boolean
}

export type MetaModelsResponse = {
  defaultModel: string
  models: MetaModel[]
  tiers: Record<string, string>
  providers: Record<string, string>
  cloudProvider: string
}

export const metaApi = {
  getApps(includeHidden: boolean = false): Promise<MetaAppsResponse> {
    return api.get<MetaAppsResponse>(`/api/meta/apps?include_hidden=${includeHidden ? 'true' : 'false'}`)
  },

  getModels(): Promise<MetaModelsResponse> {
    return api.get<MetaModelsResponse>('/api/meta/models')
  },
}

