'use client'

import { useState, useEffect, useRef } from 'react'
import AnimalCard, { Animal } from '../../components/AnimalCard'

type AnimalsResponse = {
  total: number
  page: number
  limit: number
  items: Animal[]
}

const SPECIES = [
  { value: '', label: 'Toutes' },
  { value: 'chien', label: '🐶 Chien' },
  { value: 'chat', label: '🐱 Chat' },
  { value: 'lapin', label: '🐰 Lapin' },
]

const SEXES = [
  { value: '', label: 'Tous' },
  { value: 'mâle', label: 'Mâle' },
  { value: 'femelle', label: 'Femelle' },
]

const SOURCES = [
  { value: '', label: 'Toutes' },
  { value: 'la-spa', label: 'La SPA' },
  { value: 'secondechance', label: 'Seconde Chance' },
]

const PER_PAGE = [12, 25, 50]

function FilterPill({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className="px-3 py-1 rounded-full text-sm font-semibold tracking-wide border transition-all duration-150"
      style={
        active
          ? { background: 'var(--primary)', borderColor: 'var(--primary)', color: 'white' }
          : { background: 'var(--card)', borderColor: 'var(--border)', color: 'var(--text-muted)' }
      }
    >
      {children}
    </button>
  )
}

function SkeletonCard() {
  return (
    <div
      className="rounded-2xl overflow-hidden border animate-pulse"
      style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
    >
      <div className="h-52" style={{ background: 'var(--surface)' }} />
      <div className="p-5 space-y-3">
        <div className="h-7 w-2/3 rounded" style={{ background: 'var(--surface)' }} />
        <div className="flex gap-2">
          <div className="h-5 w-16 rounded-full" style={{ background: 'var(--surface)' }} />
          <div className="h-5 w-12 rounded-full" style={{ background: 'var(--surface)' }} />
        </div>
        <div className="h-4 w-3/4 rounded" style={{ background: 'var(--surface)' }} />
        <div className="h-10 w-full rounded-lg mt-2" style={{ background: 'var(--surface)' }} />
      </div>
    </div>
  )
}

function Pagination({
  page,
  totalPages,
  onChange,
}: {
  page: number
  totalPages: number
  onChange: (p: number) => void
}) {
  if (totalPages <= 1) return null

  const pages: (number | '...')[] = []
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i)
  } else {
    pages.push(1)
    if (page > 3) pages.push('...')
    for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) pages.push(i)
    if (page < totalPages - 2) pages.push('...')
    pages.push(totalPages)
  }

  const btnBase =
    'w-9 h-9 rounded-lg font-semibold text-sm transition-all duration-150 flex items-center justify-center'

  return (
    <div className="flex items-center justify-center gap-1.5 mt-12">
      <button
        onClick={() => onChange(page - 1)}
        disabled={page === 1}
        className={`${btnBase} px-4 w-auto disabled:opacity-30`}
        style={{ border: '1px solid var(--border)', color: 'var(--text-muted)' }}
      >
        ← Préc
      </button>

      {pages.map((p, i) =>
        p === '...' ? (
          <span key={`d${i}`} className="w-9 text-center" style={{ color: 'var(--text-muted)' }}>
            …
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onChange(p as number)}
            className={btnBase}
            style={
              p === page
                ? { background: 'var(--primary)', color: 'white' }
                : { color: 'var(--text-muted)' }
            }
          >
            {p}
          </button>
        )
      )}

      <button
        onClick={() => onChange(page + 1)}
        disabled={page === totalPages}
        className={`${btnBase} px-4 w-auto disabled:opacity-30`}
        style={{ border: '1px solid var(--border)', color: 'var(--text-muted)' }}
      >
        Suiv →
      </button>
    </div>
  )
}

export default function AnimalsPage() {
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [species, setSpecies] = useState('')
  const [sex, setSex] = useState('')
  const [source, setSource] = useState('')
  const [page, setPage] = useState(1)
  const [limit, setLimit] = useState(25)
  const [data, setData] = useState<AnimalsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [showTop, setShowTop] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Debounce search → reset page
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(search)
      setPage(1)
    }, 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [search])

  // Scroll-to-top button visibility
  useEffect(() => {
    const fn = () => setShowTop(window.scrollY > 400)
    window.addEventListener('scroll', fn, { passive: true })
    return () => window.removeEventListener('scroll', fn)
  }, [])

  // Fetch
  useEffect(() => {
    const params = new URLSearchParams()
    if (debouncedSearch) params.set('search', debouncedSearch)
    if (species) params.set('species', species)
    if (sex) params.set('sex', sex)
    if (source) params.set('source', source)
    params.set('page', String(page))
    params.set('limit', String(limit))

    setLoading(true)
    fetch(`/api/animals?${params}`)
      .then(r => r.json())
      .then(d => setData(d))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [debouncedSearch, species, sex, source, page, limit])

  const setFilterAndReset =
    (setter: (v: string) => void) => (v: string) => {
      setter(v)
      setPage(1)
    }

  const hasFilters = search || species || sex || source

  const clearAll = () => {
    setSearch('')
    setSpecies('')
    setSex('')
    setSource('')
    setPage(1)
  }

  const totalPages = data ? Math.ceil(data.total / limit) : 0

  const scrollTop = () => window.scrollTo({ top: 0, behavior: 'smooth' })

  return (
    <main className="max-w-6xl mx-auto px-6 py-10">

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <div className="mb-8">
        <h1
          className="text-6xl uppercase tracking-wider"
          style={{ fontFamily: 'var(--font-bebas), Impact, sans-serif', color: 'var(--primary)' }}
        >
          Animaux disponibles
        </h1>
        <p className="mt-2 text-base" style={{ color: 'var(--text-muted)', minHeight: '1.5rem' }}>
          {!loading && data
            ? data.total > 0
              ? `${data.total} animal${data.total > 1 ? 'ux' : ''} trouvé${data.total > 1 ? 's' : ''}`
              : 'Aucun résultat pour cette recherche.'
            : ' '}
        </p>
      </div>

      {/* ── Barre de recherche + par page ────────────────────────────────── */}
      <div className="flex gap-3 mb-5">
        <div className="relative flex-1">
          <span
            className="absolute left-3.5 top-1/2 -translate-y-1/2 text-base pointer-events-none"
            style={{ color: 'var(--text-muted)' }}
          >
            🔍
          </span>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Rechercher par nom, race, description…"
            className="w-full pl-10 pr-9 py-2.5 rounded-xl text-sm border outline-none transition"
            style={{
              background: 'var(--card)',
              borderColor: 'var(--border)',
              color: 'var(--text)',
            }}
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-xl leading-none"
              style={{ color: 'var(--text-muted)' }}
            >
              ×
            </button>
          )}
        </div>

        <select
          value={limit}
          onChange={e => {
            setLimit(Number(e.target.value))
            setPage(1)
          }}
          className="px-3 py-2.5 rounded-xl text-sm border outline-none cursor-pointer"
          style={{ background: 'var(--card)', borderColor: 'var(--border)', color: 'var(--text)' }}
        >
          {PER_PAGE.map(n => (
            <option key={n} value={n}>
              {n} / page
            </option>
          ))}
        </select>
      </div>

      {/* ── Filtres ──────────────────────────────────────────────────────── */}
      <div
        className="flex flex-wrap gap-x-8 gap-y-3 mb-6 pb-5 border-b"
        style={{ borderColor: 'var(--border)' }}
      >
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className="text-xs uppercase tracking-widest font-semibold"
            style={{ color: 'var(--text-muted)' }}
          >
            Espèce
          </span>
          {SPECIES.map(s => (
            <FilterPill
              key={s.value}
              active={species === s.value}
              onClick={() => setFilterAndReset(setSpecies)(s.value)}
            >
              {s.label}
            </FilterPill>
          ))}
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span
            className="text-xs uppercase tracking-widest font-semibold"
            style={{ color: 'var(--text-muted)' }}
          >
            Sexe
          </span>
          {SEXES.map(s => (
            <FilterPill
              key={s.value}
              active={sex === s.value}
              onClick={() => setFilterAndReset(setSex)(s.value)}
            >
              {s.label}
            </FilterPill>
          ))}
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span
            className="text-xs uppercase tracking-widest font-semibold"
            style={{ color: 'var(--text-muted)' }}
          >
            Source
          </span>
          {SOURCES.map(s => (
            <FilterPill
              key={s.value}
              active={source === s.value}
              onClick={() => setFilterAndReset(setSource)(s.value)}
            >
              {s.label}
            </FilterPill>
          ))}
        </div>

        {hasFilters && (
          <button
            onClick={clearAll}
            className="ml-auto text-xs font-semibold underline underline-offset-2 transition-opacity hover:opacity-70"
            style={{ color: 'var(--accent)' }}
          >
            Effacer les filtres
          </button>
        )}
      </div>

      {/* ── Grille ───────────────────────────────────────────────────────── */}
      {loading ? (
        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-6">
          {Array.from({ length: Math.min(limit, 12) }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : !data || data.items.length === 0 ? (
        <div
          className="rounded-2xl p-12 text-center border"
          style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
        >
          <p className="text-4xl mb-4">🐾</p>
          <p style={{ color: 'var(--text-muted)' }}>
            Aucun animal ne correspond à ces critères.
          </p>
          {hasFilters && (
            <button
              onClick={clearAll}
              className="mt-4 text-sm font-semibold underline"
              style={{ color: 'var(--primary)' }}
            >
              Réinitialiser les filtres
            </button>
          )}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-6">
          {data.items.map(a => (
            <AnimalCard key={a.id} animal={a} />
          ))}
        </div>
      )}

      {/* ── Pagination ───────────────────────────────────────────────────── */}
      {!loading && (
        <Pagination
          page={page}
          totalPages={totalPages}
          onChange={p => {
            setPage(p)
            scrollTop()
          }}
        />
      )}

      {/* ── Bouton retour en haut ─────────────────────────────────────────── */}
      {showTop && (
        <button
          onClick={scrollTop}
          className="fixed bottom-6 left-6 z-40 w-12 h-12 rounded-full flex items-center justify-center shadow-lg transition-all duration-200 hover:scale-110 active:scale-95 text-white text-lg font-bold"
          style={{ background: 'var(--primary)' }}
          aria-label="Retour en haut"
        >
          ↑
        </button>
      )}
    </main>
  )
}
