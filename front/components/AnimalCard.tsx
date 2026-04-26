import Link from "next/link";

type Animal = {
  id: number;
  name: string;
  type: string;
  color: string;
  location: string;
  image: string;
};

export default function AnimalCard({ animal }: { animal: Animal }) {
  return (
    <div className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300">

      <img
        src={animal.image}
        alt={animal.name}
        className="h-52 w-full object-cover hover:scale-105 transition duration-300"
      />

      <div className="p-4">

        <h3 className="font-semibold text-lg">
          {animal.name}
        </h3>

        <p className="text-gray-500 text-sm">
          {animal.type} • {animal.color}
        </p>

        <p className="text-gray-400 text-xs mt-1">
          {animal.location}
        </p>

        <Link href={`/animals/${animal.id}`}>
          <button className="btn-primary w-full">
            Voir plus
          </button>
        </Link>

      </div>
    </div>
  );
}