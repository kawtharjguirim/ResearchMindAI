"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import type { Provider } from "@supabase/supabase-js";
import { FormError, SetupNotice } from "@/components/auth-panel";
import { GithubIcon, GoogleIcon, Icon, LinkedinIcon } from "@/components/icons";
import { inputPill } from "@/components/ui";
import { useToast } from "@/components/toast";
import { friendlyAuthError, signInWithProvider } from "@/lib/oauth";
import { getSupabase, isSupabaseConfigured } from "@/lib/supabase/client";

const social =
  "flex min-h-12 w-full items-center justify-center gap-3 rounded-full bg-gray-100 px-4 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-200 disabled:opacity-60 dark:bg-white/5 dark:text-gray-300 dark:hover:bg-white/10";

const label = "mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300";

export function SignUpForm() {
  const router = useRouter();
  const toast = useToast();
  const configured = isSupabaseConfigured();

  const [form, setForm] = useState({ first: "", last: "", email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sentTo, setSentTo] = useState("");

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    const fullName = `${form.first.trim()} ${form.last.trim()}`.trim();
    const { data, error } = await getSupabase().auth.signUp({
      email: form.email,
      password: form.password,
      options: {
        data: { full_name: fullName, first_name: form.first.trim(), last_name: form.last.trim() },
        emailRedirectTo: `${window.location.origin}/auth/callback?next=/projects`,
      },
    });
    setLoading(false);
    if (error) return setError(friendlyAuthError(error.message));

    if (data.session) {
      toast("Account created — welcome to ResearchMind AI");
      router.replace("/projects");
      router.refresh();
    } else {
      // Email confirmation is enabled in Supabase: the user must click the link first.
      setSentTo(form.email);
    }
  }

  async function oauth(provider: Provider) {
    setError("");
    try {
      await signInWithProvider(provider);
    } catch (err) {
      setError(friendlyAuthError((err as Error).message));
    }
  }

  if (sentTo) {
    return (
      <div className="mx-auto flex w-full max-w-[440px] flex-1 flex-col justify-center py-10">
        <span className="inline-flex size-12 items-center justify-center rounded-full bg-success-50 text-success-600 dark:bg-success-600/15">
          <Icon name="check" className="size-6" />
        </span>
        <h1 className="mt-5 text-3xl font-bold text-gray-800 dark:text-white/90">Check your inbox</h1>
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          We sent a confirmation link to <span className="font-medium text-gray-800 dark:text-white/90">{sentTo}</span>. Click it to activate your account.
        </p>
        <Link href="/signin" className="mt-8 font-semibold text-primary-500 hover:text-primary-600">
          Back to sign in
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-[440px] flex-1 flex-col justify-center py-10">
      <h1 className="text-3xl font-bold text-gray-800 dark:text-white/90">Create your account</h1>
      <p className="mt-2 text-gray-500 dark:text-gray-400">Start for free with the Student plan.</p>
      {!configured && <SetupNotice />}

      <div className="mt-8 grid gap-3 sm:grid-cols-3">
        <button type="button" disabled={!configured} onClick={() => oauth("google")} className={social} aria-label="Sign up with Google">
          <GoogleIcon />
          <span className="sm:hidden">Google</span>
        </button>
        <button type="button" disabled={!configured} onClick={() => oauth("github")} className={social} aria-label="Sign up with GitHub">
          <GithubIcon />
          <span className="sm:hidden">GitHub</span>
        </button>
        <button type="button" disabled={!configured} onClick={() => oauth("linkedin_oidc")} className={social} aria-label="Sign up with LinkedIn">
          <LinkedinIcon />
          <span className="sm:hidden">LinkedIn</span>
        </button>
      </div>

      <div className="relative py-5">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-200 dark:border-gray-800" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="bg-white px-4 text-gray-400 dark:bg-dark-primary">or</span>
        </div>
      </div>

      <form onSubmit={onSubmit} className="grid gap-5">
        {error && <FormError message={error} />}
        <div className="grid gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="su-first" className={label}>First name</label>
            <input id="su-first" required autoComplete="given-name" value={form.first} onChange={set("first")} className={inputPill} />
          </div>
          <div>
            <label htmlFor="su-last" className={label}>Last name</label>
            <input id="su-last" required autoComplete="family-name" value={form.last} onChange={set("last")} className={inputPill} />
          </div>
        </div>
        <div>
          <label htmlFor="su-email" className={label}>Email</label>
          <input id="su-email" type="email" required autoComplete="email" placeholder="you@university.edu" value={form.email} onChange={set("email")} className={inputPill} />
        </div>
        <div>
          <label htmlFor="su-pwd" className={label}>Password</label>
          <input
            id="su-pwd"
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            placeholder="At least 8 characters"
            value={form.password}
            onChange={set("password")}
            className={inputPill}
          />
        </div>
        <label className="flex items-start gap-3 text-sm text-gray-600 dark:text-gray-400">
          <input type="checkbox" required className="mt-0.5 size-4 rounded accent-[#7A5AF8]" />I accept the terms of use and the privacy policy.
        </label>
        <button type="submit" disabled={loading || !configured} className="gradient-btn h-12 w-full rounded-full text-sm font-medium">
          {loading ? "Creating your account…" : "Create my account"}
        </button>
      </form>

      <p className="mt-6 text-sm text-gray-600 dark:text-gray-400">
        Already have an account?{" "}
        <Link href="/signin" className="font-semibold text-primary-500 hover:text-primary-600">
          Sign in
        </Link>
      </p>
    </div>
  );
}
