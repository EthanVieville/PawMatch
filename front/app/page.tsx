const FEATURES = [
  {
    icon: '🔍',
    title: 'Centralisé',
    desc: 'La SPA, Seconde Chance et d\'autres sources réunies en une seule recherche.',
  },
  {
    icon: '🧠',
    title: 'Intelligent',
    desc: 'Notre assistant IA PawBuddy vous aide à trouver l\'animal fait pour vous.',
  },
  {
    icon: '📍',
    title: 'Localisé',
    desc: 'Visualisez les refuges sur la carte et trouvez le plus proche de chez vous.',
  },
];

const STATS = [
  { value: '500+', label: 'Animaux disponibles' },
  { value: '76',   label: 'Refuges partenaires' },
  { value: '2',    label: 'Sources agrégées' },
];

export default function Home() {
  return (
    <main>

      {/* ── HERO ─────────────────────────────────────────────────────────── */}
      {/* -mt-9 remonte la section sous la vague de la navbar pour éviter le fond sable visible */}
      <section className="relative h-[820px] overflow-hidden -mt-9">
        <img
          src="/golden_hour_welcome_page.jpg"
          className="absolute inset-0 w-full h-full object-cover"
          style={{ objectPosition: '50% 55%' }}
          alt=""
        />
        <div
          className="absolute inset-0"
          style={{
            background:
              'linear-gradient(to bottom, rgba(61,74,46,0.65) 0%, rgba(28,28,16,0.88) 100%)',
          }}
        />
        <div className="relative z-10 h-full flex flex-col justify-center items-center text-center px-6">
          <p className="text-white/60 uppercase tracking-widest text-xs font-semibold mb-4">
            Plateforme d'adoption animale
          </p>
          <h1
            className="text-7xl md:text-9xl text-white uppercase tracking-wider leading-none"
            style={{ fontFamily: 'var(--font-bebas), Impact, sans-serif' }}
          >
            Trouvez<br />votre compagnon
          </h1>
          <p className="text-white/70 text-lg mt-6 max-w-xl leading-relaxed">
            Des centaines d&apos;animaux dans les refuges partenaires, à portée de clic.
          </p>
          <div className="mt-10 flex gap-4 flex-wrap justify-center">
            <a href="/animals" className="btn-primary text-base">
              Voir les animaux
            </a>
            <a
              href="/map"
              className="inline-flex items-center justify-center px-6 py-3 rounded-lg font-semibold tracking-wide transition-all duration-200 border text-white hover:bg-white/10"
              style={{ borderColor: 'rgba(255,255,255,0.3)' }}
            >
              Explorer la carte
            </a>
          </div>
        </div>
      </section>

      {/* ── STATS BAR ────────────────────────────────────────────────────── */}
      <div style={{ background: 'var(--primary)' }} className="py-5">
        <div className="max-w-6xl mx-auto px-6 flex justify-center gap-12 flex-wrap">
          {STATS.map(({ value, label }) => (
            <div key={label} className="text-center text-white">
              <p
                className="text-3xl tracking-wide"
                style={{ fontFamily: 'var(--font-bebas), Impact, sans-serif' }}
              >
                {value}
              </p>
              <p className="text-white/70 text-xs uppercase tracking-widest mt-0.5">
                {label}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* ── FEATURES ─────────────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <p
          className="text-center text-5xl uppercase tracking-wider mb-12"
          style={{
            fontFamily: 'var(--font-bebas), Impact, sans-serif',
            color: 'var(--primary)',
          }}
        >
          Comment ça marche
        </p>
        <div className="grid md:grid-cols-3 gap-8">
          {FEATURES.map(({ icon, title, desc }) => (
            <div
              key={title}
              className="rounded-2xl p-8 border transition-all hover:-translate-y-1 hover:shadow-lg"
              style={{ background: 'var(--card)', borderColor: 'var(--border)' }}
            >
              <span className="text-4xl">{icon}</span>
              <h3
                className="text-2xl uppercase tracking-wider mt-4 mb-2"
                style={{
                  fontFamily: 'var(--font-bebas), Impact, sans-serif',
                  color: 'var(--primary)',
                }}
              >
                {title}
              </h3>
              <p style={{ color: 'var(--text-muted)' }} className="leading-relaxed">
                {desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────────── */}
      <section className="pb-20 px-6">
        <div
          className="max-w-3xl mx-auto rounded-2xl p-12 text-center"
          style={{ background: 'var(--nav)' }}
        >
          <p
            className="text-5xl text-white uppercase tracking-wider mb-4"
            style={{ fontFamily: 'var(--font-bebas), Impact, sans-serif' }}
          >
            Prêt à adopter ?
          </p>
          <p className="mb-8" style={{ color: 'rgba(255,255,255,0.6)' }}>
            Votre futur compagnon vous attend dans un refuge près de chez vous.
          </p>
          <a href="/animals" className="btn-accent text-base">
            Parcourir les animaux
          </a>
        </div>
      </section>

    </main>
  );
}
