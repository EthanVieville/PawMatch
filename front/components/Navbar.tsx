export default function Navbar() {
  return (
    <nav className="bg-white/80 backdrop-blur border-b">

      <div className="max-w-6xl mx-auto flex justify-between items-center px-6 py-4">

        <h1 className="font-bold text-lg">🐾 AdoptMe</h1>

        <div className="flex gap-6 text-sm text-gray-600">

          <a className="hover:text-black" href="/">
            Accueil
          </a>

          <a className="hover:text-black" href="/animals">
            Animaux
          </a>

          <a className="hover:text-black" href="/map">
            Carte
          </a>

          <a className="hover:text-black" href="/post">
            Publier
          </a>

        </div>

      </div>

    </nav>
  );
}