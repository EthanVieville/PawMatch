import { animals } from "../data";
import Link from "next/link";

export default async function AnimalDetail({
  params,
}: {
  params: { id: string };
}) {
  const animal = animals.find((a) => a.id === Number(params.id));

  if (!animal) {
    return <div className="p-10">Animal introuvable</div>;
  }

  return (
    <main className="max-w-3xl mx-auto px-6 py-10">

      <Link href="/animals" className="text-emerald-600 hover:underline">
        ← Retour
      </Link>

      <div className="mt-6 bg-white rounded-2xl shadow p-6">

        <img
          src={animal.image}
          className="rounded-xl w-full mb-6"
        />

        <h1 className="text-3xl font-bold mb-2">
          {animal.name}
        </h1>

        <p className="text-gray-600">
          {animal.type} • {animal.color}
        </p>

        <p className="text-gray-500 mb-4">
          📍 {animal.location}
        </p>

        <p className="text-gray-700">
          {animal.description}
        </p>

        <button className="btn-primary w-full mt-6">
          Aller vers le site d'adoption
        </button>

      </div>

    </main>
  );
}