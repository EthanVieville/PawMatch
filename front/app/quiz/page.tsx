'use client'

import { useState, useRef } from 'react'
import Link from 'next/link'
import MarkdownContent from '../../components/MarkdownContent'

interface Option {
  value: string
  label: string
  icon: string
  desc: string
}

interface Question {
  id: string
  question: string
  options: Option[]
}

const QUESTIONS: Question[] = [
  {
    id: 'species',
    question: 'Quel animal souhaitez-vous adopter ?',
    options: [
      { value: 'chien',  label: 'Chien',        icon: '🐕', desc: 'Fidèle compagnon' },
      { value: 'chat',   label: 'Chat',          icon: '🐈', desc: 'Indépendant & câlin' },
      { value: 'lapin',  label: 'Lapin',         icon: '🐇', desc: 'Doux & discret' },
      { value: 'any',    label: 'Peu importe',   icon: '🐾', desc: 'Je suis ouvert(e)' },
    ],
  },
  {
    id: 'housing',
    question: 'Où habitez-vous ?',
    options: [
      { value: 'apartment', label: 'Appartement',          icon: '🏢', desc: 'En ville, sans extérieur' },
      { value: 'house',     label: 'Maison avec jardin',   icon: '🏡', desc: 'Avec un espace extérieur' },
    ],
  },
  {
    id: 'activity',
    question: 'Quel est votre rythme de vie ?',
    options: [
      { value: 'low',    label: 'Calme',     icon: '🛋️', desc: 'Plutôt sédentaire' },
      { value: 'medium', label: 'Modéré',    icon: '🚶', desc: 'Promenades régulières' },
      { value: 'high',   label: 'Sportif',   icon: '🏃', desc: 'Très actif au quotidien' },
    ],
  },
  {
    id: 'family',
    question: 'Votre situation familiale ?',
    options: [
      { value: 'alone',      label: 'Seul(e)',              icon: '🧍', desc: '' },
      { value: 'couple',     label: 'En couple',            icon: '👫', desc: 'Sans enfants' },
      { value: 'kids_young', label: 'Enfants < 8 ans',      icon: '👶', desc: 'Jeunes enfants' },
      { value: 'kids_old',   label: 'Enfants > 8 ans',      icon: '🧒', desc: 'Enfants plus grands' },
    ],
  },
  {
    id: 'other_pets',
    question: 'Avez-vous déjà des animaux ?',
    options: [
      { value: 'none',     label: 'Aucun',       icon: '✨', desc: 'Premier animal dans le foyer' },
      { value: 'has_dog',  label: 'Un chien',    icon: '🐕', desc: "J'ai déjà un chien" },
      { value: 'has_cat',  label: 'Un chat',     icon: '🐈', desc: "J'ai déjà un chat" },
    ],
  },
  {
    id: 'experience',
    question: 'Votre expérience avec les animaux ?',
    options: [
      { value: 'first',       label: 'Première fois',    icon: '🌱', desc: 'Je découvre' },
      { value: 'experienced', label: 'Expérimenté(e)',   icon: '⭐', desc: "J'en ai déjà eu" },
    ],
  },
]

function buildMessage(answers: Record<string, string>): string {
  const lines: string[] = []

  const species = answers.species
  if (species === 'chien')      lines.push('je souhaite adopter un chien')
  else if (species === 'chat')  lines.push('je souhaite adopter un chat')
  else if (species === 'lapin') lines.push('je souhaite adopter un lapin')
  else                          lines.push("je suis ouvert(e) à toute espèce")

  if (answers.housing === 'apartment') lines.push("je vis en appartement sans extérieur")
  else                                 lines.push("j'ai une maison avec jardin")

  if (answers.activity === 'low')       lines.push("j'ai un mode de vie calme et sédentaire")
  else if (answers.activity === 'medium') lines.push("j'ai un niveau d'activité modéré")
  else                                  lines.push("je suis très sportif(ve) et actif(ve) au quotidien")

  if (answers.family === 'kids_young')  lines.push("j'ai de jeunes enfants de moins de 8 ans")
  else if (answers.family === 'kids_old') lines.push("j'ai des enfants de plus de 8 ans")
  else if (answers.family === 'couple') lines.push("je vis en couple sans enfants")
  else                                  lines.push("je vis seul(e)")

  if (answers.other_pets === 'has_dog')      lines.push("j'ai déjà un chien à la maison")
  else if (answers.other_pets === 'has_cat') lines.push("j'ai déjà un chat à la maison")
  else                                       lines.push("je n'ai pas d'autres animaux")

  if (answers.experience === 'first') lines.push("c'est mon tout premier animal de compagnie")
  else                                lines.push("j'ai déjà eu des animaux par le passé")

  const speciesLabel =
    species === 'chien' ? 'chiens' :
    species === 'chat'  ? 'chats' :
    species === 'lapin' ? 'lapins' :
    'animaux'

  return (
    "Bonjour ! J'aimerais adopter un animal et j'ai besoin de tes conseils personnalisés. " +
    "Voici mon profil : " +
    lines.join(', ') +
    `. Peux-tu me recommander 3 ou 4 ${speciesLabel} disponibles dans les refuges partenaires qui correspondent vraiment à ma situation ? ` +
    (species !== 'any' ? `IMPORTANT : je veux uniquement des ${speciesLabel}, pas d'autre espèce.` : '')
  )
}


type Phase = 'quiz' | 'streaming' | 'done'

export default function QuizPage() {
  const [step, setStep]       = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [selected, setSelected] = useState<string | null>(null)
  const [phase, setPhase]     = useState<Phase>('quiz')
  const [result, setResult]   = useState('')
  const resultRef = useRef<HTMLDivElement>(null)

  const current = QUESTIONS[step]
  const isLast  = step === QUESTIONS.length - 1
  const progress = (step / QUESTIONS.length) * 100

  const handleSelect = (value: string) => setSelected(value)

  const handleNext = () => {
    if (!selected) return
    const newAnswers = { ...answers, [current.id]: selected }
    setAnswers(newAnswers)
    setSelected(null)

    if (isLast) {
      startChat(newAnswers)
    } else {
      setStep(s => s + 1)
    }
  }

  const handleBack = () => {
    if (step === 0) return
    const prevStep = step - 1
    setSelected(answers[QUESTIONS[prevStep].id] ?? null)
    setStep(prevStep)
  }

  const startChat = async (finalAnswers: Record<string, string>) => {
    setPhase('streaming')
    setResult('')
    const message = buildMessage(finalAnswers)

    setTimeout(() => {
      resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 150)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history: [], source: 'quiz' }),
      })

      if (!response.body) throw new Error('No response body')

      const reader  = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer    = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6).trim()
          if (data === '[DONE]') continue
          try {
            const { token } = JSON.parse(data)
            if (token) setResult(prev => prev + token)
          } catch {}
        }
      }
    } catch {
      setResult('Désolé, une erreur est survenue. Veuillez réessayer.')
    }

    setPhase('done')
  }

  const resetQuiz = () => {
    setStep(0)
    setAnswers({})
    setSelected(null)
    setPhase('quiz')
    setResult('')
  }

  const cols = current?.options.length === 2 ? 'grid-cols-2' : 'grid-cols-2'

  return (
    <main className="min-h-screen">

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section
        className="-mt-9 pt-[100px] pb-16 px-6 text-center"
        style={{ background: 'var(--nav)' }}
      >
        <p className="text-white/60 uppercase tracking-widest text-xs font-semibold mb-3">
          Trouver mon compagnon
        </p>
        <h1
          className="text-6xl md:text-8xl text-white uppercase tracking-wider leading-none"
          style={{ fontFamily: 'var(--font-bebas), Impact, sans-serif' }}
        >
          Quiz d'adoption
        </h1>
        <p className="text-white/60 mt-4 max-w-md mx-auto leading-relaxed">
          Répondez à {QUESTIONS.length} questions et PawBuddy trouve les animaux faits pour vous.
        </p>
      </section>

      <div className="max-w-2xl mx-auto px-6 py-12">

        {/* ── Quiz ────────────────────────────────────────────────────────── */}
        {phase === 'quiz' && (
          <div>
            {/* Progress */}
            <div className="mb-8">
              <div
                className="flex justify-between text-xs mb-2 font-semibold uppercase tracking-widest"
                style={{ color: 'var(--text-muted)' }}
              >
                <span>Question {step + 1} / {QUESTIONS.length}</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <div
                className="h-1.5 rounded-full overflow-hidden"
                style={{ background: 'var(--border)' }}
              >
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${progress}%`, background: 'var(--accent)' }}
                />
              </div>

              {/* Dots */}
              <div className="flex justify-center gap-2 mt-4">
                {QUESTIONS.map((_, i) => (
                  <div
                    key={i}
                    className="rounded-full transition-all duration-300"
                    style={{
                      width:      i === step ? '20px' : '8px',
                      height:     '8px',
                      background: i < step
                        ? 'var(--primary)'
                        : i === step
                          ? 'var(--accent)'
                          : 'var(--border)',
                    }}
                  />
                ))}
              </div>
            </div>

            {/* Question card */}
            <div
              className="rounded-2xl p-8 mb-6"
              style={{ background: 'var(--card)', border: '1px solid var(--border)' }}
            >
              <h2
                className="text-xl md:text-2xl font-semibold mb-7 text-center"
                style={{ color: 'var(--text)' }}
              >
                {current.question}
              </h2>

              <div className={`grid ${cols} gap-3`}>
                {current.options.map(opt => {
                  const isSelected = selected === opt.value
                  return (
                    <button
                      key={opt.value}
                      onClick={() => handleSelect(opt.value)}
                      className="flex flex-col items-center gap-2 p-4 rounded-xl transition-all duration-200 text-center hover:-translate-y-0.5 active:scale-95"
                      style={{
                        background:  isSelected ? 'rgba(181,80,26,0.07)' : 'var(--bg)',
                        border:      `2px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                        boxShadow:   isSelected ? '0 0 0 3px rgba(181,80,26,0.10)' : 'none',
                      }}
                    >
                      <span className="text-3xl leading-none">{opt.icon}</span>
                      <span
                        className="font-semibold text-sm"
                        style={{ color: isSelected ? 'var(--accent)' : 'var(--text)' }}
                      >
                        {opt.label}
                      </span>
                      {opt.desc && (
                        <span className="text-xs leading-tight" style={{ color: 'var(--text-muted)' }}>
                          {opt.desc}
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Navigation */}
            <div className="flex gap-3">
              {step > 0 && (
                <button
                  onClick={handleBack}
                  className="btn-secondary flex-shrink-0"
                >
                  ← Retour
                </button>
              )}
              <button
                onClick={handleNext}
                disabled={!selected}
                className={`${isLast ? 'btn-accent' : 'btn-primary'} flex-1 disabled:opacity-40 disabled:cursor-not-allowed`}
              >
                {isLast ? '🐾 Trouver mon compagnon' : 'Suivant →'}
              </button>
            </div>
          </div>
        )}

        {/* ── Résultats ───────────────────────────────────────────────────── */}
        {(phase === 'streaming' || phase === 'done') && (
          <div ref={resultRef}>

            {/* Recap du profil */}
            <div
              className="rounded-2xl p-5 mb-5 flex flex-wrap gap-2"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
            >
              <span className="text-xs font-semibold uppercase tracking-widest w-full mb-1" style={{ color: 'var(--text-muted)' }}>
                Votre profil
              </span>
              {Object.entries(answers).map(([qid, val]) => {
                const q = QUESTIONS.find(q => q.id === qid)
                const opt = q?.options.find(o => o.value === val)
                if (!opt) return null
                return (
                  <span key={qid} className="tag text-xs">
                    {opt.icon} {opt.label}
                  </span>
                )
              })}
            </div>

            {/* Réponse PawBuddy */}
            <div
              className="rounded-2xl p-8 mb-6"
              style={{ background: 'var(--card)', border: '1px solid var(--border)' }}
            >
              {/* Header PawBuddy */}
              <div
                className="flex items-center gap-3 mb-6 pb-4"
                style={{ borderBottom: '1px solid var(--border)' }}
              >
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                  style={{ background: 'var(--nav)' }}
                >
                  <img src="/pawmatch-icone-patte.svg" alt="" className="w-6 h-6" />
                </div>
                <div className="flex-1">
                  <div className="font-semibold text-sm" style={{ color: 'var(--text)' }}>
                    PawBuddy
                  </div>
                  <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {phase === 'streaming' ? 'Analyse de votre profil…' : 'Recommandations personnalisées'}
                  </div>
                </div>
                {phase === 'streaming' && (
                  <div className="flex gap-1 items-center">
                    {[0, 150, 300].map(delay => (
                      <span
                        key={delay}
                        className="w-2 h-2 rounded-full animate-bounce"
                        style={{ background: 'var(--text-muted)', animationDelay: `${delay}ms` }}
                      />
                    ))}
                  </div>
                )}
              </div>

              {/* Contenu streamé */}
              <div className="text-sm leading-relaxed" style={{ color: 'var(--text)' }}>
                {result ? (
                  <>
                    <MarkdownContent text={result} />
                    {phase === 'streaming' && (
                      <span
                        className="inline-block w-0.5 h-4 ml-0.5 animate-pulse"
                        style={{ background: 'var(--accent)', verticalAlign: 'text-bottom' }}
                      />
                    )}
                  </>
                ) : (
                  <span style={{ color: 'var(--text-muted)' }}>
                    PawBuddy analyse votre profil et consulte les refuges…
                  </span>
                )}
              </div>
            </div>

            {/* Actions */}
            {phase === 'done' && (
              <div className="flex gap-3 flex-wrap">
                <button onClick={resetQuiz} className="btn-secondary">
                  ← Refaire le quiz
                </button>
                <Link href="/animals" className="btn-primary flex-1 justify-center">
                  Parcourir tous les animaux →
                </Link>
              </div>
            )}
          </div>
        )}

      </div>
    </main>
  )
}
