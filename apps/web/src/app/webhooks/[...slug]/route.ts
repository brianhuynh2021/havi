import { NextRequest, NextResponse } from "next/server";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string[] }> }
) {
  const { slug } = await params;
  const path = slug.join("/");
  const backendUrl = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";
  const targetUrl = `${backendUrl}/webhooks/${path}`;

  try {
    const rawBody = await request.text();
    const headers: Record<string, string> = {
      "Content-Type": request.headers.get("content-type") || "application/json",
    };

    // Forward signature headers
    const sig = request.headers.get("x-payos-signature") || request.headers.get("x-signature") || request.headers.get("webhook-signature");
    if (sig) headers["x-signature"] = sig;

    const res = await fetch(targetUrl, {
      method: "POST",
      headers,
      body: rawBody,
    });

    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    console.error("Lỗi khi proxy webhook tới backend:", error);
    return NextResponse.json(
      { error: 1, message: "Webhook proxy error" },
      { status: 500 }
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string[] }> }
) {
  const { slug } = await params;
  const path = slug.join("/");
  const backendUrl = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";
  const targetUrl = `${backendUrl}/webhooks/${path}${request.nextUrl.search}`;

  try {
    const res = await fetch(targetUrl);
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json(
      { error: 1, message: "Webhook proxy error" },
      { status: 500 }
    );
  }
}
