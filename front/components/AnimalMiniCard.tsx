'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

interface AnimalData {
  name: string
  species: string | null
  race:    string | null
  age:     number | null
  sex:     string | null
  refuge:  string | null
  images:  string[]
}

const SPECIES_EMOJI: Record<string, string> = { chien: '🐕', chat: '🐈', lapin: '🐇' }

export default function AnimalMiniCard({ href, label }: { href: string; label: string }) {
  const [animal, setAnimal] = useState<AnimalData | null>(null)

  const animalId = href.match(/^\/animals\/([^/]+)$/)?.[1] ?? null

  useEffect(() => {
    if (!animalId) return
    fetch(`/api/animals/${animalId}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(setAnimal)
      .catch(() => {})
  }, [animalId])

  // Tant que les données ne sont pas là, lien simple
  if (!animal) {
    return (
      <Link
        href={href}
        className="underline font-semibold hover:opacity-80 transition-opacity"
        style={{ color: 'var(--accent)' }}
      >
        {label}
      </Link>
    )
  }

  const emoji = SPECIES_EMOJI[animal.species ?? ''] ?? '🐾'
  const image = animal.images?.[0]
  const meta  = [
    animal.species,
    animal.age != null ? `${animal.age} an${animal.age > 1 ? 's' : ''}` : null,
    animal.sex,
  ].filter(Boolean).join(' · ')

  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-xl p-2.5 my-1.5 hover:shadow-md hover:-translate-y-0.5 transition-all active:scale-[0.99]"
      style={{
        background:    'var(--card)',
        border:        '1px solid var(--border)',
        textDecoration: 'none',
      }}
    >
      {image ? (
        <img
          src={image}
          alt={animal.name}
          className="w-14 h-14 rounded-lg object-cover flex-shrink-0"
        />
      ) : (
        <div
          className="w-14 h-14 rounded-lg flex items-center justify-center text-2xl flex-shrink-0"
          style={{ background: 'var(--surface)' }}
        >
          {emoji}
        </div>
      )}

      <div className="flex-1 min-w-0">
        <div className="font-semibold text-sm" style={{ color: 'var(--accent)' }}>
          {animal.name}
        </div>
        {meta && (
          <div className="text-xs mt-0.5 capitalize" style={{ color: 'var(--text-muted)' }}>
            {meta}
          </div>
        )}
        {animal.refuge && (
          <div className="text-xs mt-0.5 truncate" style={{ color: 'var(--text-muted)' }}>
            📍 {animal.refuge}
          </div>
        )}
      </div>

      <span
        className="text-xs font-semibold flex-shrink-0 px-2.5 py-1 rounded-lg"
        style={{ background: 'var(--surface)', color: 'var(--text-muted)' }}
      >
        Voir →
      </span>
    </Link>
  )
}
