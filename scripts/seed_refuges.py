"""
Géocode les refuges présents en base via Nominatim (OpenStreetMap — gratuit, sans clé API).

Run:
    python scripts/seed_refuges.py
    DATABASE_URL=postgresql://... python scripts/seed_refuges.py

Idempotent : ne géocode que les refuges pas encore trouvés (lat IS NULL ou absent).
Rate limit Nominatim : 1 requête/seconde (ToS).
"""

import json
import os
import re
import time
import urllib.parse
import urllib.request

import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://pawmatch:pawmatch@localhost:5432/pawmatch",
)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "PawMatch/1.0 (student project)"

# Prefixes to strip when extracting the location part from SPA names
_SPA_PREFIXES = [
    "Grand Refuge de la ", "Grand Refuge de l'", "Grand Refuge de ",
    "Maison SPA de la ", "Maison SPA de l'", "Maison SPA de ",
    "Refuge de la ", "Refuge de l'", "Refuge de Le ", "Refuge de Les ",
    "Refuge des ", "Refuge du ", "Refuge d'", "Refuge de ",
]

# Tokens that indicate the part after "–" is a description, not a city
_DESCRIPTIVE_STARTS = (
    "les ", "des ", "de l'", "de la ", "du ", "l'", "un ", "une ",
    "le ", "la ", "au ", "aux ",
)


def _extract_locations(name: str) -> list[str]:
    """
    Return candidate location strings from a refuge name, best first.

    Example:
        "La SPA - Refuge de Brugheas – Vichy"
        → ["Brugheas", "Vichy"]

        "La SPA - Refuge d'Aix-En-Provence – Des Chiens En Liberté"
        → ["Aix-En-Provence"]
    """
    locations: list[str] = []
    name_lower = name.lower()

    # 1. Extract city/location before the "–" separator
    for prefix in _SPA_PREFIXES:
        idx = name_lower.find(prefix.lower())
        if idx == -1:
            continue
        raw = name[idx + len(prefix):]
        # Cut at "–" or "—"
        for sep in ("–", "—"):
            if sep in raw:
                raw = raw[: raw.index(sep)]
        # Cut at " - sub-name"
        raw = re.sub(r"\s+-\s+.*", "", raw).strip()
        if raw and len(raw) > 2:
            locations.append(raw)
        break

    # 2. Also try the part after "–" — often the reference city
    for sep in ("–", "—"):
        if sep in name:
            after = name.split(sep, 1)[1].strip()
            after = re.sub(r"\s+-\s+.*", "", after).strip()
            after_lower = after.lower()
            # Skip if it looks like a description rather than a city
            if (
                after
                and 2 < len(after) < 35
                and not any(after_lower.startswith(t) for t in _DESCRIPTIVE_STARTS)
                and after not in locations
            ):
                locations.append(after)
            break

    return locations


def _nominatim(query: str) -> tuple[float, float] | None:
    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "limit": 1,
        "countrycodes": "fr",
    })
    req = urllib.request.Request(
        f"{NOMINATIM_URL}?{params}",
        headers={"User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            results = json.loads(resp.read())
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as e:
        print(f"    [error] {e}")
    return None


def geocode(name: str) -> tuple[float, float] | None:
    """
    Try progressively simpler queries until a result is found:
      1. Full name
      2. Full name + "France"
      3. Extracted city + "France"
      4. Extracted city alone
      5. Extracted secondary location + "France"  (part after "–")
    """
    locations = _extract_locations(name)

    queries: list[str] = [name, f"{name} France"]
    for loc in locations:
        queries.append(f"{loc} France")
        queries.append(loc)

    seen: set[str] = set()
    for query in queries:
        if query in seen:
            continue
        seen.add(query)
        result = _nominatim(query)
        time.sleep(1)  # Nominatim ToS: max 1 req/sec
        if result:
            return result

    return None


def run():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS refuges (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR UNIQUE NOT NULL,
                    source VARCHAR,
                    lat DOUBLE PRECISION,
                    lng DOUBLE PRECISION,
                    geocoded_at TIMESTAMP
                )
            """)
            conn.commit()

            cur.execute("""
                SELECT DISTINCT refuge, source FROM animals
                WHERE refuge IS NOT NULL AND refuge != ''
            """)
            rows = cur.fetchall()
            print(f"Found {len(rows)} distinct refuge(s) in animals table.")

            found = 0
            not_found = 0

            for name, source in rows:
                cur.execute("SELECT lat FROM refuges WHERE name = %s", (name,))
                existing = cur.fetchone()
                if existing and existing[0] is not None:
                    print(f"  [skip] {name}")
                    continue

                print(f"  Geocoding: {name} ...", end=" ", flush=True)
                result = geocode(name)

                if result:
                    lat, lng = result
                    print(f"→ {lat:.4f}, {lng:.4f}")
                    cur.execute("""
                        INSERT INTO refuges (id, name, source, lat, lng, geocoded_at)
                        VALUES (gen_random_uuid(), %s, %s, %s, %s, NOW())
                        ON CONFLICT (name) DO UPDATE
                            SET lat = EXCLUDED.lat, lng = EXCLUDED.lng, geocoded_at = NOW()
                    """, (name, source, lat, lng))
                    found += 1
                else:
                    print("→ not found")
                    cur.execute("""
                        INSERT INTO refuges (id, name, source, geocoded_at)
                        VALUES (gen_random_uuid(), %s, %s, NOW())
                        ON CONFLICT (name) DO UPDATE SET geocoded_at = NOW()
                    """, (name, source))
                    not_found += 1

                conn.commit()

        print(f"\nDone. {found} geocoded, {not_found} not found.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
