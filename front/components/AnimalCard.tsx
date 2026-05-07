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
  source_url: string;
  incompatibilities: string[];
};

export default function AnimalCard({ animal }: { animal: Animal }) {
  const image = animal.images[0];
  const subtitle = [animal.species, animal.race].filter(Boolean).join(" • ");

  return (
    <div className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300">

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

      <div className="p-4">

        <h3 className="font-semibold text-lg capitalize">
          {animal.name.toLowerCase()}
        </h3>

        {subtitle && (
          <p className="text-gray-500 text-sm capitalize">{subtitle}</p>
        )}

        {animal.refuge && (
          <p className="text-gray-400 text-xs mt-1">📍 {animal.refuge}</p>
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
