'use client'

import { useState } from 'react'

export default function AnimalGallery({ images, name }: { images: string[]; name: string }) {
  const [activeIndex, setActiveIndex] = useState(0)
  const [visible, setVisible] = useState(true)

  const select = (i: number) => {
    if (i === activeIndex) return
    setVisible(false)
    setTimeout(() => {
      setActiveIndex(i)
      setVisible(true)
    }, 140)
  }

  if (images.length === 0) {
    return (
      <div
        className="w-full mb-8 h-56 flex items-center justify-center text-5xl rounded-xl"
        style={{ background: 'var(--surface)' }}
      >
        🐾
      </div>
    )
  }

  return (
    <div className="mb-8">

      {/* Polaroid */}
      <div style={{ display: 'flex', justifyContent: 'center', padding: '8px 0 32px' }}>
        <div style={{
          background: 'white',
          padding: '14px 14px 52px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.1), 0 0 0 1px rgba(0,0,0,0.04)',
          transform: 'rotate(-1deg)',
          maxWidth: 480,
          width: '100%',
        }}>
          <img
            src={images[activeIndex]}
            alt={name}
            style={{
              width: '100%',
              height: 300,
              objectFit: 'cover',
              display: 'block',
              opacity: visible ? 1 : 0,
              transition: 'opacity 0.14s ease',
            }}
          />
          <p style={{
            textAlign: 'center',
            marginTop: 10,
            fontSize: 15,
            fontFamily: "'Georgia', cursive",
            color: '#999',
            letterSpacing: 1,
            userSelect: 'none',
          }}>
            {name.toLowerCase()}
          </p>
        </div>
      </div>

      {/* Thumbnails */}
      {images.length > 1 && (
        <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4 }}>
          {images.map((src, i) => (
            <button
              key={i}
              onClick={() => select(i)}
              style={{
                padding: 0, border: 'none', background: 'none',
                cursor: 'pointer', flexShrink: 0,
              }}
            >
              <img
                src={src}
                alt={`${name} ${i + 1}`}
                style={{
                  width: 76,
                  height: 76,
                  objectFit: 'cover',
                  borderRadius: 10,
                  display: 'block',
                  border: i === activeIndex
                    ? '2.5px solid var(--accent)'
                    : '2.5px solid var(--border)',
                  opacity: i === activeIndex ? 1 : 0.6,
                  transform: i === activeIndex ? 'scale(1.05)' : 'scale(1)',
                  transition: 'border-color 0.15s, opacity 0.15s, transform 0.15s',
                }}
              />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
