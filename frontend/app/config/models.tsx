export const AI_MODELS = [
  { id: 'gemini-3-flash-preview', name: 'Gemini 3 Flash', provider: 'Google' },
  { id: 'gemini-2.5-flash-lite', name: 'Gemini 2.5 Flash Lite', provider: 'Google' },
  { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash', provider: 'Google' },
  { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro', provider: 'Google' },
  { id: 'groq/compound', name: 'Groq Compound', provider: 'Groq' },
  { id: 'meta-llama/llama-4-scout-17b-16e-instruct', name: 'Llama 4 Scout', provider: 'Groq' },
  { id: 'amazon.nova-lite-v1:0', name: 'Nova Lite', provider: 'AWS Bedrock' },
  { id: 'amazon.nova-pro-v1:0', name: 'Nova Pro', provider: 'AWS Bedrock' },
]

export const DEFAULT_MODEL = 'gemini-3-flash-preview'

export type ModelId = typeof AI_MODELS[number]['id']

export type ModelOption = {
  id: string
  name: string
  provider: string
  enabled?: boolean
}

export function ModelSelector({
  value,
  onChange,
  style,
  models,
}: {
  value: string
  onChange: (v: string) => void
  style?: React.CSSProperties
  models?: ModelOption[]
}) {
  const options = (models && models.length ? models : AI_MODELS) as ModelOption[]
  const grouped = options.reduce<Record<string, ModelOption[]>>((acc, model) => {
    const provider = model.provider || 'Models'
    acc[provider] = acc[provider] || []
    acc[provider].push(model)
    return acc
  }, {})

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{ padding: '10px', background: '#1f2937', border: '1px solid #374151', borderRadius: '6px', color: 'white', cursor: 'pointer', ...style }}
    >
      {Object.entries(grouped).map(([provider, items]) => (
        <optgroup key={provider} label={provider}>
          {items.map((model) => (
            <option key={model.id} value={model.id} disabled={model.enabled === false}>
              {model.name}
              {model.enabled === false ? ' (not configured)' : ''}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  )
}
