'use client'

import { useEffect, useState, useMemo, useRef } from 'react'
import dynamic from 'next/dynamic'
import type { Refuge, MapFilters } from '../../components/MapClient'

const MapClient = dynamic(() => import('../../components/MapClient'), { ssr: false })

const SPECIES = [
  { value: '', label: 'Toutes' },
  { value: 'chien', label: '🐶 Chien' },
  { value: 'chat', label: '🐱 Chat' },
  { value: 'lapin', label: '🐰 Lapin' },
]

const SEXES = [
  { value: '', label: 'Tous' },
  { value: 'male', label: 'Mâle' },
  { value: 'femelle', label: 'Femelle' },
]

const SOURCES = [
  { value: '', label: 'Toutes' },
  { value: 'la-spa', label: 'La SPA' },
  { value: 'secondechance', label: 'Seconde Chance' },
]

function FilterSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 20 }}>
      <p style={{
        fontSize: 10, fontWeight: 700, letterSpacing: 2, color: 'rgba(255,255,255,0.5)',
        margin: '0 0 10px', textTransform: 'uppercase',
      }}>
        {label}
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {children}
      </div>
    </div>
  )
}

function CheckRow({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: 10,
        background: 'none', border: 'none', cursor: 'pointer', padding: '2px 0', textAlign: 'left',
      }}
    >
      <div style={{
        width: 16, height: 16, borderRadius: 4, flexShrink: 0,
        background: active ? 'var(--accent)' : 'rgba(255,255,255,0.12)',
        border: active ? 'none' : '1px solid rgba(255,255,255,0.25)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        transition: 'background 0.15s',
      }}>
        {active && <span style={{ fontSize: 10, color: 'white', lineHeight: 1 }}>✓</span>}
      </div>
      <span style={{ fontSize: 14, color: active ? '#F0EAD6' : 'rgba(255,255,255,0.55)', fontWeight: 600, transition: 'color 0.15s' }}>
        {label}
      </span>
    </button>
  )
}

export default function MapPage() {
  const [refuges, setRefuges] = useState<Refuge[]>([])
  const [loading, setLoading] = useState(true)
  const [species, setSpecies] = useState('')
  const [sex, setSex] = useState('')
  const [source, setSource] = useState('')
  const [search, setSearch] = useState('')
  const isFirstLoad = useRef(true)

  // Fetch avec filtres — retry au démarrage froid uniquement sur le premier chargement
  useEffect(() => {
    let cancelled = false
    const params = new URLSearchParams()
    if (species) params.set('species', species)
    if (sex) params.set('sex', sex)
    if (source) params.set('source', source)

    const load = (attempt = 1) => {
      fetch(`/api/refuges?${params}`)
        .then(r => r.json())
        .then((d: Refuge[]) => {
          if (cancelled) return
          if (d.length === 0 && attempt < 4 && isFirstLoad.current) {
            setTimeout(() => load(attempt + 1), 1500 * attempt)
          } else {
            setRefuges(d)
            setLoading(false)
            isFirstLoad.current = false
          }
        })
        .catch(() => { if (!cancelled) setLoading(false) })
    }
    load()
    return () => { cancelled = true }
  }, [species, sex, source])

  const filteredRefuges = useMemo(() => {
    if (!search) return refuges
    const q = search.toLowerCase()
    return refuges.filter(r => r.name.toLowerCase().includes(q))
  }, [refuges, search])

  const totalAnimals = filteredRefuges.reduce((s, r) => s + r.animal_count, 0)
  const filters: MapFilters = { species, sex, source }
  const hasFilters = !!(species || sex || source)

  const sidebarStyle: React.CSSProperties = {
    width: 260,
    minWidth: 260,
    backgroundImage: 'url(/camo_kaki.jpg)',
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    display: 'flex',
    flexDirection: 'column',
    overflowY: 'auto',
  }

  return (
    <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

      {/* ── Sidebar ────────────────────────────────────────────────────────── */}
      <aside style={sidebarStyle}>

        {/* Overlay semi-transparent pour la lisibilité */}
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, background: 'rgba(25,33,15,0.55)' }}>

          {/* Header + stats */}
          <div style={{ padding: '20px 16px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
            <p style={{
              fontFamily: 'var(--font-bebas), Impact, sans-serif',
              fontSize: 22, letterSpacing: 2, color: '#F0EAD6',
              margin: '0 0 14px',
            }}>
              Carte des refuges
            </p>
            {loading ? (
              <div style={{ height: 64, display: 'flex', alignItems: 'center' }}>
                <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', fontStyle: 'italic' }}>Chargement…</span>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <div style={{ background: 'rgba(255,255,255,0.07)', borderRadius: 8, padding: '10px 12px' }}>
                  <p style={{
                    fontFamily: 'var(--font-bebas), Impact, sans-serif',
                    fontSize: 28, color: 'var(--accent)', margin: 0, lineHeight: 1,
                  }}>
                    {filteredRefuges.length}
                  </p>
                  <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)', margin: '4px 0 0', fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase' }}>
                    Refuges
                  </p>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.07)', borderRadius: 8, padding: '10px 12px' }}>
                  <p style={{
                    fontFamily: 'var(--font-bebas), Impact, sans-serif',
                    fontSize: 28, color: 'var(--accent)', margin: 0, lineHeight: 1,
                  }}>
                    {totalAnimals}
                  </p>
                  <p style={{ fontSize: 10, color: 'rgba(255,255,255,0.5)', margin: '4px 0 0', fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase' }}>
                    Animaux
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Recherche refuge */}
          <div style={{ padding: '14px 16px 4px' }}>
            <div style={{
              background: 'rgba(255,255,255,0.1)', borderRadius: 8,
              padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <span style={{ fontSize: 13, flexShrink: 0 }}>🔍</span>
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Filtrer les refuges…"
                style={{
                  background: 'transparent', border: 'none', outline: 'none',
                  color: '#F0EAD6', fontSize: 13, width: '100%',
                }}
              />
              {search && (
                <button
                  onClick={() => setSearch('')}
                  style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', fontSize: 18, lineHeight: 1, padding: 0 }}
                >
                  ×
                </button>
              )}
            </div>
            {search && !loading && (
              <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', margin: '6px 2px 0' }}>
                {filteredRefuges.length} refuge{filteredRefuges.length !== 1 ? 's' : ''} affiché{filteredRefuges.length !== 1 ? 's' : ''}
              </p>
            )}
          </div>

          {/* Filtres */}
          <div style={{ padding: '16px', flex: 1 }}>

            <FilterSection label="Espèce">
              {SPECIES.map(s => (
                <CheckRow
                  key={s.value}
                  label={s.label}
                  active={species === s.value}
                  onClick={() => setSpecies(s.value)}
                />
              ))}
            </FilterSection>

            <FilterSection label="Sexe">
              <div style={{ display: 'flex', gap: 6 }}>
                {SEXES.map(s => (
                  <button
                    key={s.value}
                    onClick={() => setSex(s.value)}
                    style={{
                      flex: 1, borderRadius: 6, padding: '7px 0', textAlign: 'center',
                      fontSize: 12, fontWeight: 700, cursor: 'pointer', border: 'none',
                      background: sex === s.value ? 'var(--accent)' : 'rgba(255,255,255,0.07)',
                      color: sex === s.value ? 'white' : 'rgba(255,255,255,0.55)',
                      transition: 'background 0.15s, color 0.15s',
                    }}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </FilterSection>

            <FilterSection label="Source">
              {SOURCES.map(s => (
                <CheckRow
                  key={s.value}
                  label={s.label}
                  active={source === s.value}
                  onClick={() => setSource(s.value)}
                />
              ))}
            </FilterSection>

          </div>

          {/* Réinitialiser */}
          {hasFilters && (
            <div style={{ padding: '0 16px 12px' }}>
              <button
                onClick={() => { setSpecies(''); setSex(''); setSource('') }}
                style={{
                  width: '100%', background: 'rgba(255,255,255,0.07)', borderRadius: 8,
                  padding: '10px', textAlign: 'center', cursor: 'pointer', border: '1px solid rgba(255,255,255,0.15)',
                  fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,0.6)', letterSpacing: 1,
                  textTransform: 'uppercase',
                }}
              >
                ↺ Réinitialiser
              </button>
            </div>
          )}

          {/* Mention */}
          <div style={{ padding: '12px 16px 16px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
            <p style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', margin: 0, lineHeight: 1.5, fontStyle: 'italic' }}>
              Tous les refuges ne sont pas géolocalisés. Pour voir l'intégralité des animaux disponibles, consultez la{' '}
              <a href="/animals" style={{ color: 'rgba(255,255,255,0.55)', textDecoration: 'underline' }}>page animaux</a>.
            </p>
          </div>

        </div>
      </aside>

      {/* ── Carte ─────────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
        {loading ? (
          <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}>
            <span style={{ color: '#8B6140', fontStyle: 'italic', fontSize: 14 }}>Chargement de la carte…</span>
          </div>
        ) : (
          <MapClient refuges={filteredRefuges} filters={filters} />
        )}
      </div>
    </div>
  )
}
