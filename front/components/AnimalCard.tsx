import Link from "next/link";

export type Animal = {
  id: string;
  name: string;
  species: string | null;
  race: string | null;
  refuge: string | null;
  sex: string | null;
  age: number | null;
  description: string | null;
  images: string[];
  source: string | null;
  source_url: string;
  incompatibilities: string[];
};

const SOURCE_LABELS: Record<string, string> = {
  "la-spa":        "La SPA",
  "secondechance": "Seconde Chance",
};

const SPECIES_EMOJI: Record<string, string> = {
  chien: "🐶",
  chat:  "🐱",
  lapin: "🐰",
};

export default function AnimalCard({ animal }: { animal: Animal }) {
  const image = animal.images[0];
  const emoji = SPECIES_EMOJI[animal.species ?? ""] ?? "🐾";

  return (
    <div
      className="rounded-2xl overflow-hidden flex flex-col hover:-translate-y-1 hover:shadow-xl transition-all duration-300 border"
      style={{ background: "var(--card)", borderColor: "var(--border)" }}
    >

      {/* Image */}
      {image ? (
        <div className="h-52 overflow-hidden">
          <img
            src={image}
            alt={animal.name}
            className="w-full h-full object-cover hover:scale-105 transition duration-500"
          />
        </div>
      ) : (
        <div
          className="h-52 flex items-center justify-center text-5xl"
          style={{ background: "var(--surface)" }}
        >
          {emoji}
        </div>
      )}

      <div className="p-5 flex flex-col flex-1">

        {/* Name */}
        <h3
          className="text-2xl uppercase tracking-wide capitalize mb-3"
          style={{
            fontFamily: "var(--font-bebas), Impact, sans-serif",
            color: "var(--text)",
          }}
        >
          {animal.name.toLowerCase()}
        </h3>

        {/* Tags */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          {animal.species && (
            <span className="tag capitalize">
              {emoji} {animal.species}
            </span>
          )}
          {animal.sex && (
            <span className="tag capitalize">{animal.sex}</span>
          )}
          {animal.age !== null && (
            <span className="tag">
              {animal.age} an{animal.age > 1 ? "s" : ""}
            </span>
          )}
          {animal.race && (
            <span className="tag capitalize">{animal.race}</span>
          )}
        </div>

        {/* Refuge */}
        {animal.refuge && (
          <p className="text-sm mb-2 flex-1 truncate" style={{ color: "var(--text-muted)" }}>
            📍 {animal.refuge}
          </p>
        )}

        {/* Source */}
        {animal.source && (
          <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
            {SOURCE_LABELS[animal.source] ?? animal.source}
          </p>
        )}

        <Link href={`/animals/${animal.id}`}>
          <button className="btn-primary w-full text-sm">
            Voir la fiche →
          </button>
        </Link>

      </div>
    </div>
  );
}
