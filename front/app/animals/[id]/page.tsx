import Link from "next/link";
import AnimalCard, { Animal } from "../../../components/AnimalCard";

export const dynamic = "force-dynamic";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

const SOURCE_LABELS: Record<string, string> = {
  "la-spa":        "La SPA",
  "secondechance": "Seconde Chance",
};

async function getAnimal(id: string): Promise<Animal | null> {
  try {
    const res = await fetch(`${API_URL}/animals/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function getSimilarAnimals(id: string): Promise<Animal[]> {
  try {
    const res = await fetch(`${API_URL}/animals/${id}/similar`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function AnimalDetail({
  params,
}: {
  params: { id: string };
}) {
  const [animal, similar] = await Promise.all([
    getAnimal(params.id),
    getSimilarAnimals(params.id),
  ]);

  if (!animal) {
    return (
      <main className="p-10">
        <p style={{ color: "var(--text-muted)" }}>Animal introuvable.</p>
        <Link
          href="/animals"
          className="mt-4 block text-sm font-semibold hover:underline"
          style={{ color: "var(--primary)" }}
        >
          ← Retour à la liste
        </Link>
      </main>
    );
  }

  const images = animal.images;

  return (
    <main className="max-w-5xl mx-auto px-6 py-10">

      <Link
        href="/animals"
        className="text-sm font-semibold hover:underline"
        style={{ color: "var(--primary)" }}
      >
        ← Retour à la liste
      </Link>

      <div
        className="mt-6 rounded-2xl border p-6 max-w-3xl"
        style={{ background: "var(--card)", borderColor: "var(--border)" }}
      >

        {/* Image principale */}
        {images.length > 0 ? (
          <img
            src={images[0]}
            alt={animal.name}
            className="rounded-xl w-full mb-6 object-cover max-h-80"
          />
        ) : (
          <div
            className="rounded-xl w-full mb-6 h-52 flex items-center justify-center text-5xl"
            style={{ background: "var(--surface)" }}
          >
            🐾
          </div>
        )}

        {/* Galerie */}
        {images.length > 1 && (
          <div className="flex gap-2 mb-6 overflow-x-auto">
            {images.slice(1).map((src, i) => (
              <img
                key={i}
                src={src}
                alt={`${animal.name} ${i + 2}`}
                className="h-20 w-20 rounded-lg object-cover flex-shrink-0 border"
                style={{ borderColor: "var(--border)" }}
              />
            ))}
          </div>
        )}

        {/* Nom */}
        <h1
          className="text-5xl uppercase tracking-wider capitalize mb-4"
          style={{
            fontFamily: "var(--font-bebas), Impact, sans-serif",
            color: "var(--text)",
          }}
        >
          {animal.name.toLowerCase()}
        </h1>

        {/* Infos structurées */}
        <div
          className="grid grid-cols-2 gap-x-6 gap-y-4 text-sm mb-6 p-4 rounded-xl"
          style={{ background: "var(--surface)" }}
        >
          {animal.species && (
            <div>
              <span className="text-xs uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Espèce</span>
              <p className="font-semibold capitalize mt-0.5">{animal.species}</p>
            </div>
          )}
          {animal.race && (
            <div>
              <span className="text-xs uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Race</span>
              <p className="font-semibold capitalize mt-0.5">{animal.race}</p>
            </div>
          )}
          {animal.sex && (
            <div>
              <span className="text-xs uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Sexe</span>
              <p className="font-semibold capitalize mt-0.5">{animal.sex}</p>
            </div>
          )}
          {animal.age !== null && (
            <div>
              <span className="text-xs uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Âge</span>
              <p className="font-semibold mt-0.5">{animal.age} an{animal.age > 1 ? "s" : ""}</p>
            </div>
          )}
          {animal.refuge && (
            <div className="col-span-2">
              <span className="text-xs uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Refuge</span>
              <p className="font-semibold mt-0.5">📍 {animal.refuge}</p>
            </div>
          )}
          {animal.source && (
            <div>
              <span className="text-xs uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>Source</span>
              <p className="font-semibold mt-0.5">{SOURCE_LABELS[animal.source] ?? animal.source}</p>
            </div>
          )}
        </div>

        {/* Description */}
        {animal.description ? (
          <div className="mb-6">
            <h2
              className="text-xl uppercase tracking-wider mb-3"
              style={{
                fontFamily: "var(--font-bebas), Impact, sans-serif",
                color: "var(--primary)",
              }}
            >
              Présentation
            </h2>
            <p className="leading-relaxed" style={{ color: "var(--text-muted)" }}>
              {animal.description}
            </p>
          </div>
        ) : (
          <p className="text-sm italic mb-6" style={{ color: "var(--text-muted)" }}>
            Aucune description disponible.
          </p>
        )}

        {/* Incompatibilités */}
        {animal.incompatibilities.length > 0 && (
          <div className="rounded-lg px-4 py-3 mb-6 bg-red-50 border border-red-200">
            <p className="text-sm text-red-700 font-medium">
              ⚠️ Incompatible avec : {animal.incompatibilities.join(", ")}
            </p>
          </div>
        )}

        {/* CTA adoption */}
        <a href={animal.source_url} target="_blank" rel="noopener noreferrer">
          <button className="btn-accent w-full mt-2">
            Voir la fiche d&apos;adoption →
          </button>
        </a>

      </div>

      {/* Animaux similaires */}
      {similar.length > 0 && (
        <section className="mt-14">
          <h2
            className="text-4xl uppercase tracking-wider mb-8"
            style={{
              fontFamily: "var(--font-bebas), Impact, sans-serif",
              color: "var(--primary)",
            }}
          >
            Animaux similaires
          </h2>
          <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-6">
            {similar.map((a) => (
              <AnimalCard key={a.id} animal={a} />
            ))}
          </div>
        </section>
      )}

    </main>
  );
}
