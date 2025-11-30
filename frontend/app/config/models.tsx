export const AI_MODELS = [
  { id: 'gemini-2.5-flash-lite', name: 'Gemini 2.5 Flash Lite', provider: 'Google' },
  { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash', provider: 'Google' },
  { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro', provider: 'Google' },
  { id: 'groq/compound', name: 'Groq Compound', provider: 'Groq' },
  { id: 'meta-llama/llama-4-scout-17b-16e-instruct', name: 'Llama 4 Scout', provider: 'Groq' },
  { id: 'amazon.nova-lite-v1:0', name: 'Nova Lite', provider: 'AWS Bedrock' },
  { id: 'amazon.nova-pro-v1:0', name: 'Nova Pro', provider: 'AWS Bedrock' },
]

export const DEFAULT_MODEL = 'gemini-2.5-flash-lite'

export type ModelId = typeof AI_MODELS[number]['id']

export function ModelSelector({ value, onChange, style }: { value: string, onChange: (v: string) => void, style?: React.CSSProperties }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{ padding: '10px', background: '#1f2937', border: '1px solid #374151', borderRadius: '6px', color: 'white', cursor: 'pointer', ...style }}
    >
      <optgroup label="Gemini">
        <option value="gemini-2.5-flash-lite">Gemini 2.5 Flash Lite</option>
        <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
        <option value="gemini-2.5-pro">Gemini 2.5 Pro</option>
      </optgroup>
      <optgroup label="Groq">
        <option value="groq/compound">Groq Compound</option>
        <option value="meta-llama/llama-4-scout-17b-16e-instruct">Llama 4 Scout</option>
      </optgroup>
      <optgroup label="AWS Bedrock">
        <option value="amazon.nova-lite-v1:0">Amazon Nova Lite</option>
        <option value="amazon.nova-pro-v1:0">Amazon Nova Pro</option>
      </optgroup>
    </select>
  )
}
