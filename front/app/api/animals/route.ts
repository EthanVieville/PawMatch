const API_URL = process.env.API_URL ?? 'http://localhost:8000'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  try {
    const res = await fetch(`${API_URL}/animals?${searchParams}`, { cache: 'no-store' })
    if (!res.ok) throw new Error(`API responded ${res.status}`)
    return Response.json(await res.json())
  } catch {
    return Response.json({ total: 0, page: 1, limit: 25, items: [] })
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const res = await fetch(`${API_URL}/animals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      cache: 'no-store',
    })
    if (!res.ok) throw new Error(`API responded ${res.status}`)
    return Response.json(await res.json(), { status: 201 })
  } catch {
    return Response.json({ error: 'Erreur lors de la création' }, { status: 500 })
  }
}