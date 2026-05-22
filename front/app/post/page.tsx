"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

type Prediction = { species: string; breed: string; confidence: number };

const SPECIES_OPTIONS = ["chien", "chat", "lapin"];
const SEX_OPTIONS = ["male", "femelle"];
const INCOMPAT_OPTIONS = ["Chiens", "Chats", "Enfants", "Autres animaux", "NAC"];

const SPECIES_EMOJI: Record<string, string> = { chien: "🐶", chat: "🐱", lapin: "🐰" };

/* ── Chip de sélection ─────────────────────────────────────────────────────── */
function Chip({
  label, selected, onClick,
}: { label: string; selected: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="px-4 py-1.5 rounded-full text-sm font-semibold border transition-all duration-150 capitalize"
      style={
        selected
          ? { background: "var(--primary)", color: "#fff", borderColor: "var(--primary)" }
          : { background: "var(--surface)", color: "var(--text)", borderColor: "var(--border)" }
      }
    >
      {SPECIES_EMOJI[label] ?? ""} {label}
    </button>
  );
}

/* ── Label de champ avec badge IA ──────────────────────────────────────────── */
function FieldLabel({ children, ai }: { children: React.ReactNode; ai?: boolean }) {
  return (
    <label className="flex items-center gap-2 text-xs uppercase tracking-widest mb-1" style={{ color: "var(--text-muted)" }}>
      {children}
      {ai && (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wider text-white"
          style={{ background: "var(--accent)" }}>
          IA
        </span>
      )}
    </label>
  );
}

/* ── Indicateur de progression ─────────────────────────────────────────────── */
function StepIndicator({ step }: { step: 1 | 2 }) {
  return (
    <div className="flex items-center gap-3 mb-8">
      {[1, 2].map((s) => (
        <div key={s} className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-300"
            style={
              step >= s
                ? { background: "var(--primary)", color: "#fff" }
                : { background: "var(--surface)", color: "var(--text-muted)", border: "2px solid var(--border)" }
            }
          >
            {s < step ? "✓" : s}
          </div>
          <span className="text-xs font-semibold uppercase tracking-wider"
            style={{ color: step >= s ? "var(--text)" : "var(--text-muted)" }}>
            {s === 1 ? "Photo & nom" : "Détails"}
          </span>
          {s < 2 && <div className="w-8 h-px" style={{ background: "var(--border)" }} />}
        </div>
      ))}
    </div>
  );
}

/* ── Compression image côté client → data URI (pas de stockage serveur) ──────── */
async function compressToDataUri(file: File, maxPx = 600, quality = 0.72): Promise<string> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(maxPx / img.width, maxPx / img.height, 1);
      const canvas = document.createElement("canvas");
      canvas.width  = Math.round(img.width  * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(img.src);
      resolve(canvas.toDataURL("image/jpeg", quality));
    };
    img.src = URL.createObjectURL(file);
  });
}

/* ═══════════════════════════════════════════════════════════════════════════ */

export default function PostPage() {
  const router = useRouter();

  /* ── Step 1 ─────────────────────────────────────────────────────────────── */
  const [step, setStep] = useState<1 | 2>(1);
  const [name, setName] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /* ── Step 2 ─────────────────────────────────────────────────────────────── */
  const [species, setSpecies] = useState("");
  const [race, setRace] = useState("");
  const [sex, setSex] = useState("");
  const [age, setAge] = useState("");
  const [description, setDescription] = useState("");
  const [refuge, setRefuge] = useState("");
  const [incompatibilities, setIncompatibilities] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /* ── Helpers ────────────────────────────────────────────────────────────── */
  const aiSpecies = prediction?.species === species;
  const aiRace = prediction?.breed === race && race !== "";

  async function processFile(file: File) {
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
    setPredicting(true);
    setPrediction(null);

    // Compression client-side — pas de stockage fichier serveur
    const dataUri = await compressToDataUri(file);
    setImageUrl(dataUri);

    // Prédiction IA (optionnelle)
    try {
      const b64 = dataUri.split(",")[1];
      const res = await fetch("/api/predict-breed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_data: b64 }),
      });
      if (res.ok) {
        const pred: Prediction = await res.json();
        setPrediction(pred);
        setSpecies(pred.species);
        setRace(pred.breed);
      }
    } catch { /* prediction optionnelle */ }

    setPredicting(false);
  }

  function handleFileDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file?.type.startsWith("image/")) processFile(file);
  }

  function toggleIncompat(val: string) {
    setIncompatibilities((prev) =>
      prev.includes(val) ? prev.filter((x) => x !== val) : [...prev, val]
    );
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch("/api/animals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          species: species || null,
          race: race.trim() || null,
          sex: sex || null,
          age: age ? parseInt(age) : null,
          description: description.trim() || null,
          refuge: refuge.trim() || null,
          incompatibilities,
          image_urls: imageUrl ? [imageUrl] : [],
        }),
      });
      if (!res.ok) throw new Error();
      const animal = await res.json();
      if (!animal?.id) throw new Error('ID manquant');
      router.push(`/animals/${animal.id}`);
    } catch {
      setError("Une erreur est survenue. Vérifiez votre connexion et réessayez.");
      setSubmitting(false);
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════ */

  return (
    <main className="max-w-2xl mx-auto px-6 py-10">

      {/* En-tête */}
      <div className="flex items-center gap-4 mb-2">
        <img src="/pawmatch-icone-patte.svg" alt="" className="w-10 h-10 opacity-70" />
        <h1
          className="text-5xl uppercase tracking-wider"
          style={{ fontFamily: "var(--font-bebas), Impact, sans-serif", color: "var(--primary)" }}
        >
          Publier une annonce
        </h1>
      </div>
      <p className="text-sm mb-8" style={{ color: "var(--text-muted)" }}>
        Aidez un animal à trouver sa famille — l&apos;IA pré-remplira les champs pour vous.
      </p>

      <StepIndicator step={step} />

      {/* ── ÉTAPE 1 ─────────────────────────────────────────────────────── */}
      {step === 1 && (
        <div
          className="rounded-2xl border p-8 space-y-6"
          style={{ background: "var(--card)", borderColor: "var(--border)" }}
        >
          {/* Nom */}
          <div>
            <FieldLabel>Nom de l&apos;animal *</FieldLabel>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex : Noisette, Thor, Milo…"
              className="w-full px-4 py-3 rounded-xl text-sm font-medium outline-none transition-all"
              style={{
                background: "var(--surface)",
                border: "1.5px solid var(--border)",
                color: "var(--text)",
              }}
              onFocus={(e) => (e.target.style.borderColor = "var(--primary)")}
              onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
            />
          </div>

          {/* Zone de dépôt photo */}
          <div>
            <FieldLabel>Photo *</FieldLabel>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) processFile(f); }}
            />

            {imagePreview ? (
              <div className="relative rounded-xl overflow-hidden" style={{ height: 260 }}>
                <img src={imagePreview} alt="preview" className="w-full h-full object-cover" />
                <div
                  className="absolute inset-0 flex flex-col items-center justify-center gap-2"
                  style={{ background: "rgba(28,28,16,0.45)" }}
                >
                  {predicting ? (
                    <>
                      <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span className="text-white text-xs font-semibold tracking-wider uppercase">
                        Analyse IA en cours…
                      </span>
                    </>
                  ) : prediction ? (
                    <div
                      className="px-4 py-2 rounded-xl text-center"
                      style={{ background: "var(--accent)", color: "#fff" }}
                    >
                      <p className="text-xs uppercase tracking-wider font-semibold opacity-80">Détecté</p>
                      <p className="text-lg font-bold capitalize">{prediction.species} · {prediction.breed}</p>
                      <p className="text-xs opacity-70">Confiance : {Math.round(prediction.confidence * 100)}%</p>
                    </div>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="absolute top-3 right-3 px-3 py-1.5 rounded-lg text-xs font-semibold"
                  style={{ background: "rgba(255,255,255,0.85)", color: "var(--text)" }}
                >
                  Changer
                </button>
              </div>
            ) : (
              <div
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleFileDrop}
                className="rounded-xl border-2 border-dashed flex flex-col items-center justify-center gap-3 cursor-pointer transition-all duration-200 select-none"
                style={{
                  height: 220,
                  borderColor: dragOver ? "var(--accent)" : "var(--border)",
                  background: dragOver ? "rgba(181,80,26,0.06)" : "var(--surface)",
                }}
              >
                <img src="/pawmatch-icone-patte.svg" alt="" className="w-12 h-12 opacity-40" />
                <p className="text-sm font-semibold" style={{ color: "var(--text-muted)" }}>
                  Glissez une photo ici
                </p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  ou cliquez pour sélectionner
                </p>
              </div>
            )}
          </div>

          {/* Bouton continuer */}
          <button
            type="button"
            disabled={!name.trim() || !imageFile || predicting}
            onClick={() => setStep(2)}
            className="btn-accent w-full disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {predicting ? "Analyse en cours…" : "Continuer →"}
          </button>
        </div>
      )}

      {/* ── ÉTAPE 2 ─────────────────────────────────────────────────────── */}
      {step === 2 && (
        <form onSubmit={handleSubmit}>
          <div
            className="rounded-2xl border p-8 space-y-6"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >

            {/* Récap step 1 */}
            <div
              className="flex items-center gap-4 p-3 rounded-xl"
              style={{ background: "var(--surface)" }}
            >
              {imagePreview && (
                <img src={imagePreview} alt={name} className="w-14 h-14 rounded-lg object-cover flex-shrink-0" />
              )}
              <div>
                <p className="font-bold text-lg capitalize" style={{ fontFamily: "var(--font-bebas), Impact, sans-serif" }}>
                  {name}
                </p>
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="text-xs underline"
                  style={{ color: "var(--text-muted)" }}
                >
                  ← Modifier
                </button>
              </div>
            </div>

            {/* Espèce */}
            <div>
              <FieldLabel ai={aiSpecies}>Espèce</FieldLabel>
              <div className="flex flex-wrap gap-2">
                {SPECIES_OPTIONS.map((s) => (
                  <Chip key={s} label={s} selected={species === s} onClick={() => setSpecies(s)} />
                ))}
              </div>
            </div>

            {/* Race */}
            <div>
              <FieldLabel ai={aiRace}>
                Race
                {aiRace && prediction && (
                  <span className="text-[10px] normal-case" style={{ color: "var(--text-muted)" }}>
                    ({Math.round(prediction.confidence * 100)}% de confiance)
                  </span>
                )}
              </FieldLabel>
              <input
                value={race}
                onChange={(e) => setRace(e.target.value)}
                placeholder="Labrador, Siamois, croisé…"
                className="w-full px-4 py-3 rounded-xl text-sm font-medium outline-none transition-all"
                style={{
                  background: "var(--surface)",
                  border: `1.5px solid ${aiRace ? "var(--accent)" : "var(--border)"}`,
                  color: "var(--text)",
                }}
                onFocus={(e) => (e.target.style.borderColor = "var(--primary)")}
                onBlur={(e) => (e.target.style.borderColor = aiRace ? "var(--accent)" : "var(--border)")}
              />
            </div>

            {/* Sexe + Âge */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <FieldLabel>Sexe</FieldLabel>
                <div className="flex gap-2">
                  {SEX_OPTIONS.map((s) => (
                    <Chip key={s} label={s} selected={sex === s} onClick={() => setSex(s)} />
                  ))}
                </div>
              </div>
              <div>
                <FieldLabel>Âge (ans)</FieldLabel>
                <input
                  type="number"
                  min={0}
                  max={30}
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  placeholder="Ex : 3"
                  className="w-full px-4 py-3 rounded-xl text-sm font-medium outline-none transition-all"
                  style={{
                    background: "var(--surface)",
                    border: "1.5px solid var(--border)",
                    color: "var(--text)",
                  }}
                  onFocus={(e) => (e.target.style.borderColor = "var(--primary)")}
                  onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
                />
              </div>
            </div>

            {/* Description */}
            <div>
              <FieldLabel>Description</FieldLabel>
              <textarea
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Parlez de son caractère, ses habitudes, ce qu'il aime…"
                className="w-full px-4 py-3 rounded-xl text-sm font-medium outline-none transition-all resize-none"
                style={{
                  background: "var(--surface)",
                  border: "1.5px solid var(--border)",
                  color: "var(--text)",
                }}
                onFocus={(e) => (e.target.style.borderColor = "var(--primary)")}
                onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
              />
            </div>

            {/* Refuge / lieu */}
            <div>
              <FieldLabel>Refuge / Localisation</FieldLabel>
              <input
                value={refuge}
                onChange={(e) => setRefuge(e.target.value)}
                placeholder="Ex : SPA Paris, Association Bordeaux…"
                className="w-full px-4 py-3 rounded-xl text-sm font-medium outline-none transition-all"
                style={{
                  background: "var(--surface)",
                  border: "1.5px solid var(--border)",
                  color: "var(--text)",
                }}
                onFocus={(e) => (e.target.style.borderColor = "var(--primary)")}
                onBlur={(e) => (e.target.style.borderColor = "var(--border)")}
              />
            </div>

            {/* Incompatibilités */}
            <div>
              <FieldLabel>Incompatibilités</FieldLabel>
              <div className="flex flex-wrap gap-2">
                {INCOMPAT_OPTIONS.map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => toggleIncompat(opt)}
                    className="px-3 py-1.5 rounded-full text-xs font-semibold border transition-all duration-150"
                    style={
                      incompatibilities.includes(opt)
                        ? { background: "#fee2e2", color: "#b91c1c", borderColor: "#fca5a5" }
                        : { background: "var(--surface)", color: "var(--text-muted)", borderColor: "var(--border)" }
                    }
                  >
                    {incompatibilities.includes(opt) ? "✕ " : ""}{opt}
                  </button>
                ))}
              </div>
            </div>

            {/* Erreur */}
            {error && (
              <p className="text-sm text-red-600 bg-red-50 rounded-lg px-4 py-2">{error}</p>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={!name.trim() || submitting}
              className="btn-primary w-full disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {submitting ? "Publication en cours…" : "Publier l'annonce →"}
            </button>

          </div>
        </form>
      )}

    </main>
  );
}