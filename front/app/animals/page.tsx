import AnimalCard, { Animal } from "../../components/AnimalCard";

export const dynamic = "force-dynamic";

const API_URL = process.env.API_URL ?? "http://localhost:8000";

async function getAnimals(): Promise<Animal[]> {
  try {
    const res = await fetch(`${API_URL}/animals`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function AnimalsPage() {
  const animals = await getAnimals();

  return (
    <main className="max-w-6xl mx-auto px-6 py-10">

      <h1 className="text-3xl font-bold mb-8">
        Animaux disponibles
      </h1>

      {animals.length === 0 ? (
        <p className="text-gray-500">Aucun animal disponible pour le moment.</p>
      ) : (
        <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-6">
          {animals.map((animal) => (
            <AnimalCard key={animal.id} animal={animal} />
          ))}
        </div>
      )}

    </main>
  );
}
