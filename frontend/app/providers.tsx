'use client'

import React from 'react'
import { ModelProvider } from './components/ModelProvider'

export function Providers({ children }: { children: React.ReactNode }) {
  return <ModelProvider>{children}</ModelProvider>
}

