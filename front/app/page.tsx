export default function Home() {
  return (
    <main className="max-w-6xl mx-auto px-6 py-12">

      {/* HERO */}
      <section className="relative text-center py-28 rounded-3xl overflow-hidden">

        {/* IMAGE */}
        <div className="absolute inset-0">
          <img
            src="/hero.png"
            className="w-full h-full object-cover"
          />
        </div>

        {/* overlay sombre (plus joli que blanc) */}
        <div className="absolute inset-0 bg-black/40"></div>

        {/* content */}
        <div className="relative z-10 text-white">

          <h1 className="text-5xl font-bold tracking-tight">
            Trouvez un animal à adopter 🐾
          </h1>

          <p className="text-white/80 text-lg mt-6 max-w-2xl mx-auto">
            Une plateforme centralisée pour adopter chiens et chats facilement.
          </p>

          <div className="mt-10 flex gap-4 justify-center">

            <a href="/animals" className="btn-primary">
              Voir les animaux
            </a>

            <a href="/post" className="btn-secondary">
              Publier une annonce
            </a>

          </div>

        </div>

      </section>

      {/* FEATURES */}
      <section className="grid md:grid-cols-3 gap-6 mt-20">

        <div className="bg-white p-6 rounded-2xl shadow-sm hover:shadow-md transition">
          <h3 className="font-semibold text-lg">🐶 Centralisé</h3>
          <p className="text-gray-500 mt-2">
            Toutes les annonces d’adoption regroupées en un seul endroit.
          </p>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm hover:shadow-md transition">
          <h3 className="font-semibold text-lg">🧠 Intelligent</h3>
          <p className="text-gray-500 mt-2">
            Filtres et recommandations selon ton style de vie.
          </p>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm hover:shadow-md transition">
          <h3 className="font-semibold text-lg">🏡 Responsable</h3>
          <p className="text-gray-500 mt-2">
            Adoption facilitée avec infos claires des refuges.
          </p>
        </div>

      </section>

    </main>
  );
}