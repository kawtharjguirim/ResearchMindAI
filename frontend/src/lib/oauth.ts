import type { Provider } from "@supabase/supabase-js";
import { getSupabase } from "./supabase/client";

export async function signInWithProvider(provider: Provider, next = "/projects") {
  const redirectTo = `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`;
  const { error } = await getSupabase().auth.signInWithOAuth({ provider, options: { redirectTo } });
  if (error) throw error;
}

export function friendlyAuthError(message: string) {
  const m = message.toLowerCase();
  if (m.includes("invalid login credentials")) return "Incorrect email or password.";
  if (m.includes("email not confirmed")) return "Please confirm your email address first: check your inbox.";
  if (m.includes("user already registered")) return "An account already exists with this email. Try signing in.";
  if (m.includes("provider is not enabled")) return "This sign-in method is not enabled in Supabase yet.";
  if (m.includes("password")) return message;
  return message || "Something went wrong. Please try again.";
}
