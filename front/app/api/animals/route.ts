export async function GET(request: Request) {
  const apiUrl = process.env.API_URL ?? 'http://localhost:8000'
  const { searchParams } = new URL(request.url)

  try {
    const res = await fetch(`${apiUrl}/animals?${searchParams}`, { cache: 'no-store' })
    if (!res.ok) throw new Error(`API responded ${res.status}`)
    const data = await res.json()
    return Response.json(data)
  } catch {
    return Response.json({ total: 0, page: 1, limit: 25, items: [] })
  }
}