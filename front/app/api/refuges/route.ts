export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const apiUrl = process.env.API_URL ?? 'http://localhost:8000'
  try {
    const res = await fetch(`${apiUrl}/refuges?${searchParams.toString()}`, { cache: 'no-store' })
    if (!res.ok) throw new Error(`API responded ${res.status}`)
    return Response.json(await res.json())
  } catch {
    return Response.json([])
  }
}
