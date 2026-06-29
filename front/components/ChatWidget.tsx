'use client'

import { useState, useRef, useEffect } from 'react'
import MarkdownContent from './MarkdownContent'

interface Message {
  role: 'user' | 'assistant'
  content: string
  traceId?: string
  feedback?: 'positive' | 'negative'
}

const STORAGE_KEY = 'pawmatch_chat_history'

const WELCOME: Message = {
  role: 'assistant',
  content:
    "Bonjour ! Je suis PawBuddy 🐾 Je peux vous aider à trouver un animal à adopter, vous expliquer les démarches d'adoption, ou vous conseiller sur les soins. Que puis-je faire pour vous ?",
}


export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([WELCOME])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try { setMessages(JSON.parse(saved)) } catch {}
    }
  }, [])

  useEffect(() => {
    if (messages.length > 1) localStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
  }, [messages])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 100)
  }, [isOpen])

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || isStreaming) return

    const userMessage: Message = { role: 'user', content: text }
    const history = messages.slice(1)

    setMessages(prev => [...prev, userMessage, { role: 'assistant', content: '' }])
    setInput('')
    setIsStreaming(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history: history.map(m => ({ role: m.role, content: m.content })),
        }),
      })

      if (!response.body) throw new Error('No response body')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

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
            const parsed = JSON.parse(data)
            if (parsed.token) {
              setMessages(prev => {
                const updated = [...prev]
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  content: updated[updated.length - 1].content + parsed.token,
                }
                return updated
              })
            } else if (parsed.trace_id) {
              setMessages(prev => {
                const updated = [...prev]
                updated[updated.length - 1] = {
                  ...updated[updated.length - 1],
                  traceId: parsed.trace_id,
                }
                return updated
              })
            }
          } catch {}
        }
      }
    } catch {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: 'Désolé, une erreur est survenue. Veuillez réessayer.',
        }
        return updated
      })
    } finally {
      setIsStreaming(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearHistory = () => {
    setMessages([WELCOME])
    localStorage.removeItem(STORAGE_KEY)
  }

  const sendFeedback = async (index: number, rating: 'positive' | 'negative') => {
    const msg = messages[index]
    if (!msg.traceId || msg.feedback) return
    setMessages(prev => {
      const updated = [...prev]
      updated[index] = { ...updated[index], feedback: rating }
      return updated
    })
    try {
      await fetch('/api/chat/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trace_id: msg.traceId, rating }),
      })
    } catch {}
  }

  return (
    <>
      {/* Fenêtre de chat — toujours dans le DOM pour les transitions fluides */}
      <div
        className="fixed bottom-24 right-6 z-50 flex flex-col rounded-2xl shadow-2xl overflow-hidden"
        style={{
          width: 400,
          height: 640,
          transformOrigin: 'bottom right',
          opacity: isOpen ? 1 : 0,
          transform: isOpen ? 'translateY(0) scale(1)' : 'translateY(28px) scale(0.92)',
          pointerEvents: isOpen ? 'auto' : 'none',
          visibility: isOpen ? 'visible' : 'hidden',
          // spring cubic-bezier à l'ouverture, ease-in rapide à la fermeture
          transition: isOpen
            ? 'opacity 0.25s ease, transform 0.4s cubic-bezier(0.34,1.56,0.64,1), visibility 0s linear 0s'
            : 'opacity 0.2s ease, transform 0.25s ease-in, visibility 0s linear 0.25s',
        }}
      >
        {/* ── Header camo ─────────────────────────────────────────────────── */}
        <div
          className="relative flex items-center justify-between px-4 py-3 flex-shrink-0"
          style={{
            backgroundImage: 'url(/camo_kaki.jpg)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
          }}
        >
          {/* overlay pour lisibilité */}
          <div className="absolute inset-0" style={{ background: 'rgba(25,33,15,0.55)' }} />

          <div className="relative flex items-center gap-3">
            <img src="/pawmatch-icone-patte.svg" alt="" className="w-9 h-9 drop-shadow" />
            <div className="text-white">
              <div className="font-semibold text-sm tracking-wide">PawBuddy</div>
              <div className="text-xs opacity-75">Assistant adoption</div>
            </div>
          </div>

          <div className="relative flex items-center gap-2">
            <button
              onClick={clearHistory}
              className="text-xs px-2 py-1 rounded text-white opacity-70 hover:opacity-100 hover:bg-white/20 transition"
            >
              Effacer
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className="text-2xl leading-none text-white opacity-70 hover:opacity-100 transition"
            >
              ×
            </button>
          </div>
        </div>

        {/* ── Messages ────────────────────────────────────────────────────── */}
        <div
          className="flex-1 overflow-y-auto px-4 py-3 space-y-3"
          style={{ background: 'var(--bg)' }}
        >
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-[85%] px-3 py-2 rounded-2xl text-sm leading-relaxed ${
                  msg.role === 'user' ? 'rounded-br-sm text-white' : 'rounded-bl-sm'
                }`}
                style={
                  msg.role === 'user'
                    ? { background: 'var(--accent)' }
                    : {
                        background: 'var(--card)',
                        color: 'var(--text)',
                        border: '1px solid var(--border)',
                      }
                }
              >
                {msg.role === 'assistant' && msg.content === '' ? (
                  <span className="flex gap-1 items-center py-0.5">
                    {[0, 150, 300].map(delay => (
                      <span
                        key={delay}
                        className="w-2 h-2 rounded-full animate-bounce"
                        style={{ background: 'var(--text-muted)', animationDelay: `${delay}ms` }}
                      />
                    ))}
                  </span>
                ) : (
                  <MarkdownContent text={msg.content} />
                )}
              </div>

              {msg.role === 'assistant' && msg.traceId && msg.content !== '' && (
                <div className="flex gap-1 mt-1 px-1">
                  <button
                    onClick={() => sendFeedback(i, 'positive')}
                    disabled={!!msg.feedback}
                    title="Réponse utile"
                    className="text-base leading-none transition-opacity disabled:cursor-default"
                    style={{ opacity: msg.feedback && msg.feedback !== 'positive' ? 0.25 : 1 }}
                  >
                    👍
                  </button>
                  <button
                    onClick={() => sendFeedback(i, 'negative')}
                    disabled={!!msg.feedback}
                    title="Réponse à améliorer"
                    className="text-base leading-none transition-opacity disabled:cursor-default"
                    style={{ opacity: msg.feedback && msg.feedback !== 'negative' ? 0.25 : 1 }}
                  >
                    👎
                  </button>
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* ── Input ───────────────────────────────────────────────────────── */}
        <div
          className="px-4 py-3 flex-shrink-0 border-t"
          style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
        >
          <div className="flex gap-2">
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Posez votre question…"
              disabled={isStreaming}
              className="flex-1 text-sm rounded-xl px-3 py-2 outline-none transition disabled:opacity-50 border"
              style={{
                background: 'var(--bg)',
                borderColor: 'var(--border)',
                color: 'var(--text)',
              }}
            />
            <button
              onClick={sendMessage}
              disabled={isStreaming || !input.trim()}
              className="text-white px-4 py-2 rounded-xl font-bold transition disabled:opacity-40 hover:opacity-90"
              style={{ background: 'var(--accent)' }}
            >
              ➤
            </button>
          </div>
        </div>
      </div>

      {/* ── Bouton flottant ─────────────────────────────────────────────── */}
      <button
        onClick={() => setIsOpen(prev => !prev)}
        className="fixed bottom-6 right-6 z-50 flex items-center justify-center transition-transform hover:scale-110 active:scale-95"
        style={{ filter: 'drop-shadow(0 4px 14px rgba(0,0,0,0.4))' }}
        aria-label="Ouvrir PawBuddy"
      >
        {isOpen ? (
          <span
            className="w-16 h-16 rounded-full flex items-center justify-center text-white text-2xl leading-none"
            style={{ background: 'var(--nav)' }}
          >
            ×
          </span>
        ) : (
          <img src="/pawmatch-icone-patte.svg" alt="" className="w-16 h-16" />
        )}
      </button>
    </>
  )
}
