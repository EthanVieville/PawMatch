import AnimalCard from "../../components/AnimalCard";

export const animals = [
  {
    id: 1,
    name: "Milo",
    type: "Chat",
    color: "Noir",
    location: "Paris",
    description: "Chat calme, parfait pour appartement.",
    image: "https://placekitten.com/300/200",
  },
  {
    id: 2,
    name: "Rex",
    type: "Chien",
    color: "Marron",
    location: "Lyon",
    description: "Chien joueur et affectueux.",
    image: "https://placedog.net/300/200",
  },
];

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