export async function GET() {
  return Response.json([
    { id: 1, name: "Milo", type: "Chat", color: "Noir" }
  ]);
}