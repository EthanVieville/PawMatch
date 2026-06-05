'use client';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const LINKS = [
  { href: '/',        label: 'Accueil' },
  { href: '/animals', label: 'Animaux' },
  { href: '/map',     label: 'Carte' },
  { href: '/quiz',    label: 'Quiz' },
];

const WAVE_CLIP =
  'polygon(0% 0%, 100% 0%, 100% 72%,' +
  '96.67% 100%, 93.33% 72%,' +
  '90% 100%, 86.67% 72%,' +
  '83.33% 100%, 80% 72%,' +
  '76.67% 100%, 73.33% 72%,' +
  '70% 100%, 66.67% 72%,' +
  '63.33% 100%, 60% 72%,' +
  '56.67% 100%, 53.33% 72%,' +
  '50% 100%, 46.67% 72%,' +
  '43.33% 100%, 40% 72%,' +
  '36.67% 100%, 33.33% 72%,' +
  '30% 100%, 26.67% 72%,' +
  '23.33% 100%, 20% 72%,' +
  '16.67% 100%, 13.33% 72%,' +
  '10% 100%, 6.67% 72%,' +
  '3.33% 100%, 0% 72%)';

// Même nombre de sommets que WAVE_CLIP pour permettre l'interpolation CSS
const FLAT_CLIP =
  'polygon(0% 0%, 100% 0%, 100% 100%,' +
  '96.67% 100%, 93.33% 100%,' +
  '90% 100%, 86.67% 100%,' +
  '83.33% 100%, 80% 100%,' +
  '76.67% 100%, 73.33% 100%,' +
  '70% 100%, 66.67% 100%,' +
  '63.33% 100%, 60% 100%,' +
  '56.67% 100%, 53.33% 100%,' +
  '50% 100%, 46.67% 100%,' +
  '43.33% 100%, 40% 100%,' +
  '36.67% 100%, 33.33% 100%,' +
  '30% 100%, 26.67% 100%,' +
  '23.33% 100%, 20% 100%,' +
  '16.67% 100%, 13.33% 100%,' +
  '10% 100%, 6.67% 100%,' +
  '3.33% 100%, 0% 100%)';

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 60);
    window.addEventListener('scroll', fn, { passive: true });
    return () => window.removeEventListener('scroll', fn);
  }, []);

  return (
    <div className="sticky top-0 z-50">

      {/* ── Barre principale avec vague ──────────────────────────────────── */}
      {/* drop-shadow sur le parent, clip-path sur l'enfant */}
      <div style={{ filter: 'drop-shadow(0 6px 16px rgba(0,0,0,0.3))' }}>
        <div
          style={{
            background: '#E2D5BB',
            paddingBottom: scrolled || pathname === '/map' ? '0px' : '36px',
            clipPath: scrolled || pathname === '/map' ? FLAT_CLIP : WAVE_CLIP,
            transition: 'clip-path 0.4s ease, padding-bottom 0.4s ease',
          }}
        >
          <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">

            {/* Logo */}
            <Link href="/">
              <img
                src="/pawmatch-logo.png"
                alt="PawMatch"
                className="h-14 w-auto"
                style={{ mixBlendMode: 'multiply' }}
              />
            </Link>

            {/* Desktop links */}
            <div className="hidden md:flex items-center gap-8">
              {LINKS.map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className={`text-sm font-semibold uppercase tracking-widest transition-colors ${
                    pathname === href
                      ? 'border-b-2 pb-0.5'
                      : 'hover:opacity-100'
                  }`}
                  style={
                    pathname === href
                      ? { color: '#3D4A2E', borderColor: '#3D4A2E' }
                      : { color: '#6B6250' }
                  }
                >
                  {label}
                </Link>
              ))}
              <Link href="/post" className="btn-accent text-sm py-2 px-5">
                Publier
              </Link>
            </div>

            {/* Hamburger mobile */}
            <button
              className="md:hidden p-1"
              style={{ color: '#3D4A2E' }}
              onClick={() => setOpen(!open)}
              aria-label="Menu"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {open ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* ── Menu mobile (sous la vague, fond camo sans clip) ─────────────── */}
      {open && (
        <div
          className="md:hidden px-6 py-4 flex flex-col gap-4 border-t"
          style={{
            background: '#E2D5BB',
            borderColor: 'rgba(61,74,46,0.2)',
            marginTop: '-1px',
          }}
        >
          {LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className="font-semibold uppercase tracking-widest text-sm hover:opacity-70 transition-opacity"
              style={{ color: '#6B6250' }}
              onClick={() => setOpen(false)}
            >
              {label}
            </Link>
          ))}
          <Link
            href="/post"
            className="btn-accent text-sm text-center"
            onClick={() => setOpen(false)}
          >
            Publier
          </Link>
        </div>
      )}
    </div>
  );
}
