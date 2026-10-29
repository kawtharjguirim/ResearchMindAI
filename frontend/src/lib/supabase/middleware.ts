import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { publicOrigin } from "@/lib/origin";

const PUBLIC_PATHS = ["/signin", "/signup", "/auth"];
const AUTH_PAGES = ["/signin", "/signup"];

export async function updateSession(request: NextRequest) {
  let response = NextResponse.next({ request });

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return response; // Not configured yet: let pages show the setup message.

  const supabase = createServerClient(url, key, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (toSet) => {
        toSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        toSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
      },
    },
  });

  // Refreshes the session cookie when needed. Do not run code between client creation and this call.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const path = request.nextUrl.pathname;
  const isPublic = PUBLIC_PATHS.some((p) => path === p || path.startsWith(`${p}/`));

  const origin = publicOrigin(request);

  if (!user && !isPublic) {
    const search = path === "/" ? "" : `?next=${encodeURIComponent(path)}`;
    return NextResponse.redirect(`${origin}/signin${search}`);
  }

  if (user && AUTH_PAGES.includes(path)) {
    return NextResponse.redirect(`${origin}/projects`);
  }

  return response;
}
