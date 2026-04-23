import AnimalCard from '../components/AnimalCard';

const animals = [
  {
    id: 1,
    name: "Milo",
    type: "Chat",
    color: "Noir",
    location: "Paris",
    image: "https://placekitten.com/300/200"
  },
  {
    id: 2,
    name: "Rex",
    type: "Chien",
    color: "Marron",
    location: "Lyon",
    image: "https://placedog.net/300/200"
  }
];

export default function Home() {
  return (
    <main style={{ padding: 20 }}>
      <h1>Adopte ton compagnon 🐾</h1>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
        gap: 20
      }}>
        {animals.map(a => (
          <AnimalCard key={a.id} animal={a} />
        ))}
      </div>
    </main>
  );
}