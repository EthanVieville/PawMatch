export default function AnimalCard({ animal }) {
  return (
    <div style={{ border: '1px solid #ddd', borderRadius: 10 }}>
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