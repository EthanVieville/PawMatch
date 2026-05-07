export async function GET() {
  const apiUrl = process.env.API_URL ?? 'http://localhost:8000'

  try {
    const res = await fetch(`${apiUrl}/animals`, { cache: 'no-store' })
    if (!res.ok) throw new Error(`API responded ${res.status}`)
    const data = await res.json()
    return Response.json(data)
  } catch {
    // Fallback données de démo si l'API n'est pas démarrée
    return Response.json([
      { id: 'milo', name: 'Milo', species: 'chat', sex: 'male' },
    ])
  }
}