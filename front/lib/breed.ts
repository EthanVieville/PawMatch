const VAGUE_BREEDS = new Set([
  "européen", "chat européen", "european", "european shorthair",
  "gouttière", "chat de gouttière", "chat de gouttiere",
  "domestique", "chat domestique", "domestic shorthair",
  "commun", "chat commun", "commun européen",
  "bâtard", "batard", "chien bâtard",
  "croisé", "croise", "chien croisé",
  "mélange", "melange", "mixte", "race mixte", "chien de race mixte",
  "inconnu", "race inconnue", "sans race", "srd", "sans race déterminée",
]);

export function isVagueBreed(race: string | null): boolean {
  if (!race) return false;
  return VAGUE_BREEDS.has(race.toLowerCase().trim());
}
