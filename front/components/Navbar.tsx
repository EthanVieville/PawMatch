'use client';
import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const LINKS = [
  { href: '/',        label: 'Accueil' },
  { href: '/animals', label: 'Animaux' },
  { href: '/map',     label: 'Carte' },
];

// 15 dents régulières — le fond camo se termine en zigzag Y2K
// La zone de contenu occupe 72% de la hauteur, la vague les 28% restants
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

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return (
    <div className="sticky top-0 z-50">

      {/* ── Barre principale avec vague ──────────────────────────────────── */}
      {/* drop-shadow sur le parent, clip-path sur l'enfant */}
      <div style={{ filter: 'drop-shadow(0 8px 14px rgba(0,0,0,0.45))' }}>
        <div
          style={{
            backgroundImage: "url('/camo_kaki.jpg')",
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            paddingBottom: '36px',   /* espace pour la zone de vague */
            clipPath: WAVE_CLIP,
          }}
        >
          <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">

            {/* Logo */}
            <Link href="/">
              <img
                src="/pawmatch-logo-navbar.svg"
                alt="PawMatch"
                className="h-12 w-auto"
                style={{ filter: 'drop-shadow(0 1px 4px rgba(0,0,0,0.6))' }}
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
                      ? 'text-white border-b-2 border-white pb-0.5'
                      : 'text-white/70 hover:text-white'
                  }`}
                  style={{ textShadow: '0 1px 4px rgba(0,0,0,0.5)' }}
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
              className="md:hidden text-white p-1"
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
            backgroundImage: "url('/camo_kaki.jpg')",
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            borderColor: 'rgba(255,255,255,0.15)',
            marginTop: '-1px',
          }}
        >
          {LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className="text-white/80 hover:text-white font-semibold uppercase tracking-widest text-sm"
              style={{ textShadow: '0 1px 3px rgba(0,0,0,0.5)' }}
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
