import Link from "next/link";
import { Animal } from "../../../components/AnimalCard";

export const dynamic = "force-dynamic";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

async function getAnimal(id: string): Promise<Animal | null> {
  try {
    const res = await fetch(`${API_URL}/animals/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function AnimalDetail({
  params,
}: {
  params: { id: string };
}) {
  const animal = await getAnimal(params.id);

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

  const image = animal.images[0];
  const subtitle = [animal.species, animal.race].filter(Boolean).join(" • ");

  return (
    <main className="max-w-3xl mx-auto px-6 py-10">

      <Link href="/animals" className="text-emerald-600 hover:underline">
        ← Retour
      </Link>

      <div className="mt-6 bg-white rounded-2xl shadow p-6">

        {image ? (
          <img src={image} alt={animal.name} className="rounded-xl w-full mb-6 object-cover max-h-80" />
        ) : (
          <div className="rounded-xl w-full mb-6 h-52 bg-gray-100 flex items-center justify-center text-gray-400">
            Pas de photo
          </div>
        )}

        <h1 className="text-3xl font-bold mb-1 capitalize">
          {animal.name.toLowerCase()}
        </h1>

        {subtitle && (
          <p className="text-gray-600 capitalize mb-1">{subtitle}</p>
        )}

        {animal.sex && (
          <p className="text-gray-500 text-sm mb-1 capitalize">{animal.sex}</p>
        )}

        {animal.age !== null && (
          <p className="text-gray-500 text-sm mb-1">{animal.age} an{animal.age > 1 ? "s" : ""}</p>
        )}

        {animal.refuge && (
          <p className="text-gray-500 text-sm mb-4">📍 {animal.refuge}</p>
        )}

        {animal.description && (
          <p className="text-gray-700 mb-4">{animal.description}</p>
        )}

        {animal.incompatibilities.length > 0 && (
          <p className="text-sm text-red-500 mb-4">
            ⚠️ Incompatible avec : {animal.incompatibilities.join(", ")}
          </p>
        )}

        <a href={animal.source_url} target="_blank" rel="noopener noreferrer">
          <button className="btn-primary w-full mt-2">
            Aller vers le site d&apos;adoption
          </button>
        </a>

      </div>

    </main>
  );
}
