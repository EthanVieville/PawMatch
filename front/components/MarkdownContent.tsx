'use client'

import { type ReactNode } from 'react'
import Link from 'next/link'
import AnimalMiniCard from './AnimalMiniCard'

// Passe 1 : bold / italic seulement (sur les segments sans lien)
function renderBoldItalic(text: string, key: string): ReactNode[] {
  const regex = /\*\*([^*]+)\*\*|\*([^*]+)\*/g
  const nodes: ReactNode[] = []
  let last = 0
  let m: RegExpExecArray | null
  let idx = 0

  while ((m = regex.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index))
    if (m[1] !== undefined) {
      nodes.push(<strong key={`${key}-b${idx++}`} className="font-semibold">{m[1]}</strong>)
    } else {
      nodes.push(<em key={`${key}-i${idx++}`}>{m[2]}</em>)
    }
    last = m.index + m[0].length
  }
  if (last < text.length) nodes.push(text.slice(last))
  return nodes
}

// Passe 2 : split sur les liens [texte](url), puis bold/italic dans les segments restants
function renderInline(text: string, key: string): ReactNode[] {
  // Le groupe capturant inclut le séparateur dans le tableau résultant
  const parts = text.split(/(\[[^\]]+\]\([^)]+\))/g)
  const nodes: ReactNode[] = []

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i]
    if (!part) continue

    const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/)
    if (link) {
      const label = link[1]
      const href  = link[2]
      if (href.startsWith('/animals/')) {
        nodes.push(<AnimalMiniCard key={`${key}-card-${i}`} href={href} label={label} />)
      } else {
        nodes.push(
          <Link
            key={`${key}-link-${i}`}
            href={href}
            className="underline font-semibold hover:opacity-80 transition-opacity"
            style={{ color: 'var(--accent)' }}
          >
            {label}
          </Link>
        )
      }
    } else {
      nodes.push(...renderBoldItalic(part, `${key}-t${i}`))
    }
  }

  return nodes
}

export default function MarkdownContent({ text, className = '' }: { text: string; className?: string }): ReactNode {
  const lines = text.split('\n')
  const nodes: ReactNode[] = []

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const k = `line-${i}`

    if (/^---+$/.test(line.trim())) {
      nodes.push(<hr key={k} className="my-3" style={{ borderColor: 'var(--border)' }} />)
    } else if (line.startsWith('### ')) {
      nodes.push(
        <div key={k} className="font-bold text-sm mt-4 mb-0.5" style={{ color: 'var(--text)' }}>
          {renderInline(line.slice(4), k)}
        </div>
      )
    } else if (line.startsWith('## ')) {
      nodes.push(
        <div key={k} className="font-bold text-base mt-4 mb-1" style={{ color: 'var(--text)' }}>
          {renderInline(line.slice(3), k)}
        </div>
      )
    } else if (line.startsWith('# ')) {
      nodes.push(
        <div key={k} className="font-bold text-lg mt-4 mb-1" style={{ color: 'var(--text)' }}>
          {renderInline(line.slice(2), k)}
        </div>
      )
    } else if (line.trim() === '') {
      nodes.push(<div key={k} style={{ height: '6px' }} />)
    } else {
      nodes.push(
        <div key={k} className="leading-relaxed mb-0.5">
          {renderInline(line, k)}
        </div>
      )
    }
  }

  return <div className={`text-sm ${className}`}>{nodes}</div>
}
