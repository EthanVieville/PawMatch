import AnimalCard from "../../components/AnimalCard";
import { animals } from "./data";

export default function AnimalsPage() {
  return (
    <main className="max-w-6xl mx-auto px-6 py-10">

      <h1 className="text-3xl font-bold mb-8">
        Animaux disponibles
      </h1>

      <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-6">

        {animals.map((animal) => (
          <AnimalCard key={animal.id} animal={animal} />
        ))}

      </div>

    </main>
  );
}