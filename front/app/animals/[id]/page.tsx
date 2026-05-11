import Link from "next/link";
import AnimalCard, { Animal } from "../../../components/AnimalCard";

export const dynamic = "force-dynamic";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

const SOURCE_LABELS: Record<string, string> = {
  "la-spa": "La SPA",
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
        <p className="text-gray-500">Animal introuvable.</p>
        <Link href="/animals" className="text-emerald-600 hover:underline mt-4 block">
          ← Retour à la liste
        </Link>
      </main>
    );
  }

  const images = animal.images;

  return (
    <main className="max-w-5xl mx-auto px-6 py-10">

      <Link href="/animals" className="text-emerald-600 hover:underline text-sm">
        ← Retour à la liste
      </Link>

      <div className="mt-6 bg-white rounded-2xl shadow p-6 max-w-3xl">

        {/* Image principale */}
        {images.length > 0 ? (
          <img
            src={images[0]}
            alt={animal.name}
            className="rounded-xl w-full mb-6 object-cover max-h-80"
          />
        ) : (
          <div className="rounded-xl w-full mb-6 h-52 bg-gray-100 flex items-center justify-center text-gray-400">
            Pas de photo
          </div>
        )}

        {/* Galerie supplémentaire */}
        {images.length > 1 && (
          <div className="flex gap-2 mb-6 overflow-x-auto">
            {images.slice(1).map((src, i) => (
              <img
                key={i}
                src={src}
                alt={`${animal.name} ${i + 2}`}
                className="h-20 w-20 rounded-lg object-cover flex-shrink-0"
              />
            ))}
          </div>
        )}

        {/* Nom */}
        <h1 className="text-3xl font-bold mb-4 capitalize">
          {animal.name.toLowerCase()}
        </h1>

        {/* Infos structurées */}
        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm mb-6">
          {animal.species && (
            <div>
              <span className="text-gray-400">Espèce</span>
              <p className="font-medium capitalize">{animal.species}</p>
            </div>
          )}
          {animal.race && (
            <div>
              <span className="text-gray-400">Race</span>
              <p className="font-medium capitalize">{animal.race}</p>
            </div>
          )}
          {animal.sex && (
            <div>
              <span className="text-gray-400">Sexe</span>
              <p className="font-medium capitalize">{animal.sex}</p>
            </div>
          )}
          {animal.age !== null && (
            <div>
              <span className="text-gray-400">Âge</span>
              <p className="font-medium">{animal.age} an{animal.age > 1 ? "s" : ""}</p>
            </div>
          )}
          {animal.refuge && (
            <div className="col-span-2">
              <span className="text-gray-400">Refuge</span>
              <p className="font-medium">📍 {animal.refuge}</p>
            </div>
          )}
          {animal.source && (
            <div>
              <span className="text-gray-400">Source</span>
              <p className="font-medium">{SOURCE_LABELS[animal.source] ?? animal.source}</p>
            </div>
          )}
        </div>

        {/* Description */}
        {animal.description ? (
          <div className="mb-6">
            <h2 className="text-base font-semibold mb-2 text-gray-700">Présentation</h2>
            <p className="text-gray-700 leading-relaxed">{animal.description}</p>
          </div>
        ) : (
          <p className="text-gray-400 text-sm italic mb-6">Aucune description disponible.</p>
        )}

        {/* Incompatibilités */}
        {animal.incompatibilities.length > 0 && (
          <div className="bg-red-50 rounded-lg px-4 py-3 mb-6">
            <p className="text-sm text-red-600 font-medium">
              ⚠️ Incompatible avec : {animal.incompatibilities.join(", ")}
            </p>
          </div>
        )}

        {/* Bouton adoption */}
        <a href={animal.source_url} target="_blank" rel="noopener noreferrer">
          <button className="btn-primary w-full mt-2">
            Voir la fiche d&apos;adoption
          </button>
        </a>

      </div>

      {/* Animaux similaires */}
      {similar.length > 0 && (
        <section className="mt-12">
          <h2 className="text-xl font-semibold mb-6">Animaux similaires</h2>
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
