import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const apiUrl = process.env.SESSIONZERO_API_URL;
  if (!apiUrl) {
    return NextResponse.json(
      { error: { code: "API_NOT_CONFIGURED", message: "API URL is not configured." } },
      { status: 503 },
    );
  }

  try {
    const response = await fetch(`${apiUrl.replace(/\/$/, "")}/api/v1/capabilities`, {
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    const body: unknown = await response.json();
    return NextResponse.json(body, { status: response.status });
  } catch {
    return NextResponse.json(
      { error: { code: "API_UNAVAILABLE", message: "SessionZero API is unavailable." } },
      { status: 502 },
    );
  }
}
