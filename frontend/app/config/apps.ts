export interface AppConfig {
  id: string
  name: string
  description: string[]
  icon: string
  color: string
  route: string
  status: 'active' | 'soon'
  requiresAuth: boolean
}

export const apps: AppConfig[] = [
  {
    id: 'ai-chat',
    name: 'Chat',
    description: [
      'AI Chat',
      'Document Analysis',
      'Web Search',
      'Code Execution'
    ],
    icon: '💬',
    color: '#6366f1',
    route: '/apps/ai-chat',
    status: 'active',
    requiresAuth: true
  },
  {
    id: 'agentic-barista',
    name: 'Agentic Barista',
    description: [
      'Natural Language Ordering',
      'Menu Discovery',
      'Smart Cart Management',
      'Order Confirmation'
    ],
    icon: '☕',
    color: '#f97316',
    route: '/apps/agentic-barista',
    status: 'active',
    requiresAuth: false
  },
  {
    id: 'insurance-claims',
    name: 'Insurance Claims',
    description: [
      'Role-Based Workflow',
      'Policy Management',
      'Claims Processing',
      'Status Tracking'
    ],
    icon: '🚗',
    color: '#06b6d4',
    route: '/apps/insurance-claims',
    status: 'active',
    requiresAuth: true
  },
  {
    id: 'agentic-lms',
    name: 'Agentic LMS',
    description: [
      'AI Course Discovery',
      'Natural Language Enrollment',
      'Progress Tracking',
      'LangGraph Agents'
    ],
    icon: '🎓',
    color: '#8b5cf6',
    route: '/apps/agentic-lms',
    status: 'active',
    requiresAuth: true
  },
  {
    id: 'agentic-tutor',
    name: 'Agentic Tutor',
    description: [
      'Interactive Learning',
      'Practice Assessments',
      'Multi-Agent System',
      'Progress Tracking'
    ],
    icon: '👨‍🏫',
    color: '#f59e0b',
    route: '/apps/agentic-tutor',
    status: 'active',
    requiresAuth: true
  },
  {
    id: 'ml-predictor',
    name: 'ML Predictor',
    description: [
      'Multi-Algorithm ML System',
      'Automatic Algorithm Selection',
      'Classification & Regression',
      'Comprehensive Metrics'
    ],
    icon: '🤖',
    color: '#8b5cf6',
    route: '/apps/ml-predictor',
    status: 'active',
    requiresAuth: true
  },
  {
    id: 'llms-fine-tuning',
    name: 'LLMs Fine-Tuning',
    description: [
      'Tinker API',
      'LoRA fine-tuning',
      'Scripted job runner',
      'Live logs + checkpoint sampling'
    ],
    icon: '🧪',
    color: '#22c55e',
    route: '/apps/llms-fine-tuning',
    status: 'active',
    requiresAuth: true
  },
  {
    id: 'data-analysis',
    name: 'Agentic Data Analysis',
    description: [
      'Multi-Source Ingestion',
      'Automated ETL Pipeline',
      'Agentic Q&A',
      'Self-Healing Queries'
    ],
    icon: '📊',
    color: '#14b8a6',
    route: '/apps/data-analysis',
    status: 'active',
    requiresAuth: true
  },
  {
    id: 'terminal',
    name: 'Terminal',
    description: [
      'Ubuntu 22.04 shell',
      'Full internet access',
      'Isolated container per session',
      'No access to other apps'
    ],
    icon: '🖥️',
    color: '#0ea5e9',
    route: '/apps/terminal',
    status: 'active',
    requiresAuth: true
  },
  {
    id: 'ai-agent',
    name: 'AI Agent',
    description: [
      'General Purpose AI',
      'Code Execution',
      'Build & Deploy',
      'Live URL Serving'
    ],
    icon: '🦾',
    color: '#ec4899',
    route: '/apps/ai-agent',
    status: 'active',
    requiresAuth: true
  }
]
