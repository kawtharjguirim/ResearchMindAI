import { NextResponse, type NextRequest } from "next/server";
import { publicOrigin } from "@/lib/origin";
import { createSupabaseServer } from "@/lib/supabase/server";

// OAuth and email-confirmation links land here with a `code` to exchange for a session.
export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const origin = publicOrigin(request);
  const code = searchParams.get("code");
  const nextParam = searchParams.get("next") ?? "/projects";
  const next = nextParam.startsWith("/") && !nextParam.startsWith("//") ? nextParam : "/projects";

  if (code) {
    const supabase = await createSupabaseServer();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) return NextResponse.redirect(`${origin}${next}`);
  }
  return NextResponse.redirect(`${origin}/signin?error=auth`);
}
