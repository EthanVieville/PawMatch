'use client'

import { useEffect, useState } from 'react'
import dynamic from 'next/dynamic'
import type { Refuge } from '../../components/MapClient'

const MapClient = dynamic(() => import('../../components/MapClient'), { ssr: false })

export default function MapPage() {
  const [refuges, setRefuges] = useState<Refuge[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    const load = (attempt = 1) => {
      fetch('/api/refuges')
        .then(r => r.json())
        .then((d: Refuge[]) => {
          if (cancelled) return
          if (d.length === 0 && attempt < 4) {
            // Retry si le backend répond vide (démarrage froid)
            setTimeout(() => load(attempt + 1), 1500 * attempt)
          } else {
            setRefuges(d)
            setLoading(false)
          }
        })
        .catch(() => { if (!cancelled) setLoading(false) })
    }
    load()
    return () => { cancelled = true }
  }, [])

  const totalAnimals = refuges.reduce((s, r) => s + r.animal_count, 0)

  return (
    <main>

      {/* ── Header centré ───────────────────────────────────────────────── */}
      <div className="text-center pt-10 pb-5 max-w-6xl mx-auto px-6">
        <h1
          className="text-6xl uppercase tracking-wider"
          style={{ fontFamily: 'var(--font-bebas), Impact, sans-serif', color: 'var(--primary)' }}
        >
          Carte des refuges
        </h1>

        <div className="mt-3 flex justify-center gap-3 flex-wrap min-h-[28px]">
          {!loading && (
            <>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold"
                style={{ background: 'var(--surface)', color: 'var(--text-muted)' }}>
                📍 {refuges.length} refuge{refuges.length > 1 ? 's' : ''}
              </span>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold"
                style={{ background: 'var(--surface)', color: 'var(--text-muted)' }}>
                🐾 {totalAnimals} animal{totalAnimals > 1 ? 'ux' : ''} disponible{totalAnimals > 1 ? 's' : ''}
              </span>
            </>
          )}
        </div>
      </div>

      {/* ── Carte sur parchemin ──────────────────────────────────────────── */}
      <div className="flex justify-center px-4 pb-2">
        {/* maxWidth contraint la taille pour que tout rentre dans l'écran */}
        <div style={{ width: '100%', maxWidth: 860 }}>
        <div
          style={{
            position: 'relative',
            filter: 'drop-shadow(0 12px 40px rgba(60,35,10,0.5))',
          }}
        >
          <img
            src="/parchemin.png"
            alt=""
            draggable={false}
            style={{ width: '100%', display: 'block', userSelect: 'none', pointerEvents: 'none' }}
          />

          {/* La carte positionnée dans la zone papier du parchemin */}
          <div
            style={{
              position: 'absolute',
              top: '8%',
              left: '7%',
              right: '6%',
              bottom: '8%',
              borderRadius: 2,
              overflow: 'hidden',
            }}
          >
            {loading ? (
              <div className="w-full h-full flex items-center justify-center"
                style={{ background: 'rgba(210,185,140,0.25)' }}>
                <span style={{ color: '#8B6140', fontStyle: 'italic', fontSize: 14 }}>
                  Chargement de la carte…
                </span>
              </div>
            ) : (
              <MapClient refuges={refuges} />
            )}
          </div>
        </div>
        </div>
      </div>

      {/* ── Légende centrée ─────────────────────────────────────────────── */}
      <div className="text-center py-5">
        <p className="text-sm italic" style={{ color: 'var(--text-muted)' }}>
          Cliquez sur une patte 🐾 pour voir les animaux disponibles dans ce refuge.
        </p>
      </div>

    </main>
  )
}
