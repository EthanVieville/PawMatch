import { NextRequest, NextResponse } from 'next/server'

const API_URL = process.env.API_URL || 'http://localhost:8000'

export async function POST(req: NextRequest) {
  const body = await req.json()

  const response = await fetch(`${API_URL}/chat/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  return new NextResponse(null, { status: response.status })
}
