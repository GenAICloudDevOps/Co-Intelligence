import React from 'react'

export default function ArchitectureDiagram() {
  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <svg
        viewBox="0 0 1200 440"
        role="img"
        aria-labelledby="archTitle archDesc"
        style={{ width: '100%', minWidth: '900px', height: 'auto', display: 'block' }}
      >
        <title id="archTitle">Platform architecture</title>
        <desc id="archDesc">
          High-level flow from users to Next.js frontend, FastAPI backend, evaluation and guardrails, and managed
          infrastructure services.
        </desc>

        <defs>
          <linearGradient id="card" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#1e293b" />
            <stop offset="100%" stopColor="#0f172a" />
          </linearGradient>
          <linearGradient id="accent" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="100%" stopColor="#8b5cf6" />
          </linearGradient>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b" />
          </marker>
          <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="10" stdDeviation="10" floodColor="#000000" floodOpacity="0.35" />
          </filter>
        </defs>

        <rect x="20" y="20" width="1160" height="400" rx="18" fill="url(#card)" stroke="#334155" />
        <rect x="20" y="20" width="1160" height="56" rx="18" fill="transparent" />
        <rect x="20" y="20" width="1160" height="56" rx="18" fill="url(#accent)" opacity="0.18" />
        <text x="48" y="56" fill="#e2e8f0" fontSize="18" fontWeight="700">
          High-level architecture (UI → API → Evals/Guardrails → Infrastructure)
        </text>

        {/* Users */}
        <g filter="url(#shadow)">
          <rect x="70" y="140" width="200" height="120" rx="14" fill="#0b1220" stroke="#1e293b" />
          <text x="170" y="178" textAnchor="middle" fill="#e2e8f0" fontSize="16" fontWeight="700">
            Users
          </text>
          <text x="170" y="204" textAnchor="middle" fill="#94a3b8" fontSize="13">
            Browser / Team
          </text>
          <text x="170" y="226" textAnchor="middle" fill="#94a3b8" fontSize="13">
            App launches
          </text>
        </g>

        {/* Frontend */}
        <g filter="url(#shadow)">
          <rect x="340" y="120" width="260" height="160" rx="14" fill="#0f172a" stroke="#334155" />
          <text x="470" y="156" textAnchor="middle" fill="#e2e8f0" fontSize="16" fontWeight="700">
            Next.js Frontend
          </text>
          <text x="470" y="182" textAnchor="middle" fill="#94a3b8" fontSize="13">
            Landing + Apps
          </text>
          <text x="470" y="204" textAnchor="middle" fill="#94a3b8" fontSize="13">
            Auth (cookies)
          </text>
          <text x="470" y="226" textAnchor="middle" fill="#94a3b8" fontSize="13">
            Streaming UX
          </text>
        </g>

        {/* Backend */}
        <g filter="url(#shadow)">
          <rect x="660" y="120" width="260" height="160" rx="14" fill="#0f172a" stroke="#334155" />
          <text x="790" y="156" textAnchor="middle" fill="#e2e8f0" fontSize="16" fontWeight="700">
            FastAPI Backend
          </text>
          <text x="790" y="182" textAnchor="middle" fill="#94a3b8" fontSize="13">
            REST APIs
          </text>
          <text x="790" y="204" textAnchor="middle" fill="#94a3b8" fontSize="13">
            RBAC + sessions
          </text>
          <text x="790" y="226" textAnchor="middle" fill="#94a3b8" fontSize="13">
            Orchestration
          </text>
        </g>

        {/* External + Managed Services */}
        <g filter="url(#shadow)">
          <rect x="980" y="92" width="160" height="216" rx="14" fill="#0b1220" stroke="#1e293b" />
          <text x="1060" y="128" textAnchor="middle" fill="#e2e8f0" fontSize="16" fontWeight="700">
            Services
          </text>
          <text x="1060" y="156" textAnchor="middle" fill="#94a3b8" fontSize="13">
            AI providers
          </text>
          <text x="1060" y="178" textAnchor="middle" fill="#94a3b8" fontSize="13">
            Gemini / Groq
          </text>
          <text x="1060" y="200" textAnchor="middle" fill="#94a3b8" fontSize="13">
            Bedrock
          </text>
          <text x="1060" y="230" textAnchor="middle" fill="#94a3b8" fontSize="13">
            PostgreSQL
          </text>
          <text x="1060" y="252" textAnchor="middle" fill="#94a3b8" fontSize="13">
            Object storage (S3)
          </text>
          <text x="1060" y="274" textAnchor="middle" fill="#94a3b8" fontSize="13">
            Code exec (Lambda)
          </text>
        </g>

        {/* Evals / Guardrails (backend services) */}
        <g filter="url(#shadow)">
          <rect x="500" y="310" width="360" height="88" rx="14" fill="#0f172a" stroke="#334155" />
          <text x="680" y="346" textAnchor="middle" fill="#e2e8f0" fontSize="16" fontWeight="700">
            Evaluation + Guardrails (backend)
          </text>
          <text x="680" y="370" textAnchor="middle" fill="#94a3b8" fontSize="13">
            Quality metrics • Top issues • Safety blocks
          </text>
        </g>

        {/* Infra / Runtime */}
        <g filter="url(#shadow)">
          <rect x="70" y="310" width="380" height="88" rx="14" fill="#0b1220" stroke="#1e293b" />
          <text x="260" y="346" textAnchor="middle" fill="#e2e8f0" fontSize="16" fontWeight="700">
            Deploy & Runtime
          </text>
          <text x="260" y="370" textAnchor="middle" fill="#94a3b8" fontSize="13">
            Docker-compose (local) • Kubernetes (AWS / GCP / Azure)
          </text>
        </g>

        {/* Arrows */}
        <path d="M 270 200 L 340 200" stroke="#64748b" strokeWidth="3" fill="none" markerEnd="url(#arrow)" />
        <path d="M 600 200 L 660 200" stroke="#64748b" strokeWidth="3" fill="none" markerEnd="url(#arrow)" />
        <path d="M 920 200 L 980 200" stroke="#64748b" strokeWidth="3" fill="none" markerEnd="url(#arrow)" />
        <path d="M 790 280 L 760 310" stroke="#64748b" strokeWidth="3" fill="none" markerEnd="url(#arrow)" />
        <path d="M 470 280 L 540 310" stroke="#64748b" strokeWidth="3" fill="none" markerEnd="url(#arrow)" />
        <path d="M 470 200 L 450 310" stroke="#334155" strokeWidth="2" fill="none" opacity="0.5" />
        <path d="M 340 354 L 500 354" stroke="#64748b" strokeWidth="3" fill="none" markerEnd="url(#arrow)" />
      </svg>
    </div>
  )
}
