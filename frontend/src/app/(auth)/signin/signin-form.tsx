"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import type { Provider } from "@supabase/supabase-js";
import { FormError, SetupNotice } from "@/components/auth-panel";
import { GithubIcon, GoogleIcon, Icon, LinkedinIcon } from "@/components/icons";
import { inputPill } from "@/components/ui";
import { useToast } from "@/components/toast";
import { friendlyAuthError, signInWithProvider } from "@/lib/oauth";
import { getSupabase, isSupabaseConfigured } from "@/lib/supabase/client";

const social =
  "flex min-h-12 w-full items-center justify-center gap-3 rounded-full bg-gray-100 px-6 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-200 hover:text-gray-800 disabled:opacity-60 dark:bg-white/5 dark:text-gray-300 dark:hover:bg-white/10 dark:hover:text-white/90";

export function SignInForm() {
  const router = useRouter();
  const params = useSearchParams();
  const toast = useToast();
  const next = params.get("next") || "/projects";
  const configured = isSupabaseConfigured();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(params.get("error") ? "Sign-in failed or the link has expired. Please try again." : "");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    const { error } = await getSupabase().auth.signInWithPassword({ email, password });
    setLoading(false);
    if (error) return setError(friendlyAuthError(error.message));
    router.replace(next);
    router.refresh();
  }

  async function oauth(provider: Provider) {
    setError("");
    try {
      await signInWithProvider(provider, next);
    } catch (err) {
      setError(friendlyAuthError((err as Error).message));
    }
  }

  async function forgotPassword() {
    if (!email) return setError("Enter your email above, then click “Forgot password?” again.");
    const { error } = await getSupabase().auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/callback?next=/projects`,
    });
    if (error) return setError(friendlyAuthError(error.message));
    toast("A reset link has been sent to your email");
  }

  return (
    <div className="mx-auto flex w-full max-w-[420px] flex-1 flex-col justify-center py-10">
      <h1 className="text-3xl font-bold text-gray-800 dark:text-white/90">Welcome back</h1>
      <p className="mt-2 text-gray-500 dark:text-gray-400">Sign in to get back to your research projects</p>
      {!configured && <SetupNotice />}

      <div className="mt-8 space-y-3">
        <button type="button" disabled={!configured} onClick={() => oauth("google")} className={social}>
          <GoogleIcon />
          Continue with Google
        </button>
        <button type="button" disabled={!configured} onClick={() => oauth("github")} className={social}>
          <GithubIcon />
          Continue with GitHub
        </button>
        <button type="button" disabled={!configured} onClick={() => oauth("linkedin_oidc")} className={social}>
          <LinkedinIcon />
          Continue with LinkedIn
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
        <div>
          <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            placeholder="you@university.edu"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputPill}
          />
        </div>
        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <label htmlFor="password" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Password
            </label>
            <button type="button" onClick={forgotPassword} disabled={!configured} className="text-sm font-medium text-primary-500 hover:text-primary-600">
              Forgot password?
            </button>
          </div>
          <div className="relative">
            <input
              id="password"
              type={showPwd ? "text" : "password"}
              required
              autoComplete="current-password"
              placeholder="Your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`${inputPill} pr-12`}
            />
            <button
              type="button"
              onClick={() => setShowPwd((s) => !s)}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400"
              aria-label={showPwd ? "Hide password" : "Show password"}
            >
              <Icon name={showPwd ? "eyeOff" : "eye"} />
            </button>
          </div>
        </div>
        <button type="submit" disabled={loading || !configured} className="gradient-btn h-12 w-full rounded-full text-sm font-medium">
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className="mt-6 text-sm text-gray-600 dark:text-gray-400">
        Don&apos;t have an account yet?{" "}
        <Link href="/signup" className="font-semibold text-primary-500 hover:text-primary-600">
          Create an account
        </Link>
      </p>
    </div>
  );
}
