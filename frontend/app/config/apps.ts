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
    requiresAuth: false
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
  }
]
