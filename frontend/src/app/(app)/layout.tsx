import { redirect } from "next/navigation";
import { Shell } from "@/components/shell";
import { createSupabaseServer } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    redirect("/signin");
  }
  const supabase = await createSupabaseServer();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/signin");

  const meta = user.user_metadata ?? {};
  return <Shell user={{ email: user.email ?? null, name: meta.full_name ?? meta.name ?? null }}>{children}</Shell>;
}
