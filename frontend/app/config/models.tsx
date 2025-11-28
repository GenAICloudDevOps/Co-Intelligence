export const AI_MODELS = [
  { value: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash Lite', group: 'Gemini' },
  { value: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', group: 'Gemini' },
  { value: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro', group: 'Gemini' },
  { value: 'groq/compound', label: 'Groq Compound', group: 'Groq' },
  { value: 'meta-llama/llama-4-scout-17b-16e-instruct', label: 'Llama 4 Scout', group: 'Groq' },
  { value: 'amazon.nova-lite-v1:0', label: 'Amazon Nova Lite', group: 'AWS Bedrock' },
  { value: 'amazon.nova-pro-v1:0', label: 'Amazon Nova Pro', group: 'AWS Bedrock' },
]

export const DEFAULT_MODEL = 'gemini-2.5-flash-lite'

export const MODEL_GROUPS = ['Gemini', 'Groq', 'AWS Bedrock']

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
