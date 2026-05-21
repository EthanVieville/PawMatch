export async function GET() {
  const apiUrl = process.env.API_URL ?? 'http://localhost:8000'
  try {
    const res = await fetch(`${apiUrl}/refuges`, { cache: 'no-store' })
    if (!res.ok) throw new Error(`API responded ${res.status}`)
    return Response.json(await res.json())
  } catch {
    return Response.json([])
  }
}
