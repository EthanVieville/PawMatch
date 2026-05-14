import { NextRequest } from 'next/server'

const API_URL = process.env.API_URL || 'http://localhost:8000'

export async function POST(req: NextRequest) {
  const body = await req.json()

  const response = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  return new Response(response.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'X-Accel-Buffering': 'no',
    },
  })
}
