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
  "la-spa": "La SPA",
  "secondechance": "Seconde Chance",
};

export default function AnimalCard({ animal }: { animal: Animal }) {
  const image = animal.images[0];

  return (
    <div className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 flex flex-col">

      {image ? (
        <img
          src={image}
          alt={animal.name}
          className="h-52 w-full object-cover hover:scale-105 transition duration-300"
        />
      ) : (
        <div className="h-52 w-full bg-gray-100 flex items-center justify-center text-gray-400 text-sm">
          Pas de photo
        </div>
      )}

      <div className="p-4 flex flex-col flex-1">

        <h3 className="font-semibold text-lg capitalize mb-2">
          {animal.name.toLowerCase()}
        </h3>

        <div className="flex flex-col gap-0.5 text-sm text-gray-500 flex-1">
          {animal.species && (
            <p className="capitalize">
              <span className="text-gray-400">Espèce :</span>{" "}
              {animal.species}
            </p>
          )}
          {animal.race && (
            <p className="capitalize">
              <span className="text-gray-400">Race :</span>{" "}
              {animal.race}
            </p>
          )}
          {animal.sex && (
            <p className="capitalize">
              <span className="text-gray-400">Sexe :</span>{" "}
              {animal.sex}
            </p>
          )}
          {animal.age !== null && (
            <p>
              <span className="text-gray-400">Âge :</span>{" "}
              {animal.age} an{animal.age > 1 ? "s" : ""}
            </p>
          )}
          {animal.refuge && (
            <p className="mt-1">📍 {animal.refuge}</p>
          )}
        </div>

        {animal.source && (
          <p className="text-xs text-gray-400 mt-2">
            {SOURCE_LABELS[animal.source] ?? animal.source}
          </p>
        )}

        <Link href={`/animals/${animal.id}`}>
          <button className="btn-primary w-full mt-3">
            Voir plus
          </button>
        </Link>

      </div>
    </div>
  );
}
