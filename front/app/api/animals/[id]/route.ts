const API_URL = process.env.API_URL ?? 'http://localhost:8000'

export async function GET(
  _request: Request,
  { params }: { params: { id: string } },
) {
  try {
    const res = await fetch(`${API_URL}/animals/${params.id}`, { cache: 'no-store' })
    if (!res.ok) return Response.json({ error: 'Not found' }, { status: 404 })
    return Response.json(await res.json())
  } catch {
    return Response.json({ error: 'Server error' }, { status: 500 })
  }
}
