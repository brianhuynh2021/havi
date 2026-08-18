import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const search = request.nextUrl.search;
  const backendUrl = process.env.INTERNAL_BACKEND_URL || "http://localhost:8000";
  return NextResponse.redirect(`${backendUrl}/connections/tiktok/callback${search}`);
}
