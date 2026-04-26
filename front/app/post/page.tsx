export default function PostPage() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-10">

      <h1 className="text-3xl font-bold mb-6">
        Publier une annonce 📝
      </h1>

      <div className="bg-white rounded-2xl shadow p-6 space-y-4">

        <input
          className="w-full border p-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500"
          placeholder="Nom de l'animal"
        />

        <input
          className="w-full border p-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500"
          placeholder="Type (chien, chat...)"
        />

        <input
          className="w-full border p-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500"
          placeholder="Localisation"
        />

        <button className="btn-primary w-full">
          Publier
        </button>

      </div>

    </main>
  );
}