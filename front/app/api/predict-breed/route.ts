const API_URL = process.env.API_URL ?? 'http://localhost:8000'

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const res = await fetch(`${API_URL}/predict-breed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      cache: 'no-store',
    })
    if (!res.ok) return Response.json(null, { status: res.status })
    return Response.json(await res.json())
  } catch {
    return Response.json(null, { status: 503 })
  }
}