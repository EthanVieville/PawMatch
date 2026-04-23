// Minimal full-stack starter (Next.js) for your animal adoption platform
// Structure fits your repo: place this at root alongside dl_models/ and scrapper/

// =============================
// 1. package.json
// =============================
{
  "name": "animal-platform",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.2.0",
    "react": "18.2.0",
    "react-dom": "18.2.0"
  }
}

// =============================
// 2. app/layout.tsx
// =============================
export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: 'Arial, sans-serif' }}>
        {children}
      </body>
    </html>
  );
}

// =============================
// 3. app/page.tsx
// =============================
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
      <p>Trouve facilement un animal qui te correspond</p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 20 }}>
        {animals.map(a => (
          <AnimalCard key={a.id} animal={a} />
        ))}
      </div>
    </main>
  );
}

// =============================
// 4. components/AnimalCard.tsx
// =============================
export default function AnimalCard({ animal }) {
  return (
    <div style={{ border: '1px solid #ddd', borderRadius: 10, overflow: 'hidden' }}>
      <img src={animal.image} alt={animal.name} style={{ width: '100%' }} />
      <div style={{ padding: 10 }}>
        <h3>{animal.name}</h3>
        <p>{animal.type} • {animal.color}</p>
        <p>{animal.location}</p>
        <button style={{ padding: 10, width: '100%' }}>
          Voir plus
        </button>
      </div>
    </div>
  );
}

// =============================
// 5. API route (future Python bridge)
// =============================
// app/api/animals/route.ts

export async function GET() {
  return Response.json([
    {
      id: 1,
      name: "Milo",
      type: "Chat",
      color: "Noir"
    }
  ]);
}

// =============================
// NOTES
// =============================
// - Next.js runs well on AWS (via Vercel, ECS, or Lambda)
// - Later you can connect Python via:
//    - FastAPI microservice (recommended)
//    - or call ML scripts via API
// - Replace static animals with DB (PostgreSQL)
// - Add map later (Mapbox / Leaflet)
// - Add chatbot UI later (simple floating widget)
