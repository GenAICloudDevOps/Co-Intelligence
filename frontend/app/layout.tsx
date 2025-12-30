import type { Metadata } from 'next'
import { Providers } from './providers'

export const metadata: Metadata = {
  title: 'Co-Intelligence - Where Human Meets AI Intelligence',
  description: 'Where Human Meets AI Intelligence',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet" />
      </head>
      <body style={{ 
        margin: 0, 
        fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
        background: 'linear-gradient(135deg, #0a0f1e 0%, #1a1042 100%)',
        minHeight: '100vh'
      }}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
