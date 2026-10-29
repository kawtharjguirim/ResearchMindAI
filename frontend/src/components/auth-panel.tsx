import type { ReactNode } from "react";
import { Icon } from "./icons";
import { Logo, LogoMark } from "./logo";
import { ThemeButton } from "./theme";

export function AuthLayout({ children, aside }: { children: ReactNode; aside: ReactNode }) {
  return (
    <div className="grid min-h-screen bg-white dark:bg-dark-primary lg:grid-cols-2">
      <div className="flex flex-col px-6 py-8 sm:px-12">
        <div className="flex items-center justify-between">
          <Logo href="/" />
          <ThemeButton />
        </div>
        {children}
      </div>
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-[#7A5AF8] to-[#B5B1FF] lg:flex lg:flex-col lg:items-center lg:justify-center lg:px-12">
        <div className="absolute -right-24 -top-24 size-80 rounded-full bg-white/10" />
        <div className="absolute -bottom-32 -left-20 size-96 rounded-full bg-[#FF58D5]/20 blur-3xl" />
        {aside}
      </div>
    </div>
  );
}

const cite = (n: number) => <span className="rounded bg-primary-50 px-1 text-[10px] font-semibold text-primary-600">[{n}]</span>;

export function SignInAside() {
  return (
    <div className="relative flex w-full flex-col items-center">
      <div className="floating w-full max-w-[420px] rounded-3xl bg-white p-5 shadow-[0_30px_60px_-20px_rgba(23,31,46,0.45)] dark:bg-dark-secondary">
        <div className="flex justify-end">
          <p className="max-w-[85%] rounded-2xl rounded-tr-md bg-gray-100 px-4 py-2.5 text-xs text-gray-800 dark:bg-white/10 dark:text-white/90">
            Which datasets are used in these papers?
          </p>
        </div>
        <div className="mt-4 flex gap-2.5">
          <LogoMark className="size-7" />
          <div className="flex-1 space-y-2.5">
            <p className="text-xs leading-relaxed text-gray-600 dark:text-gray-300">
              EyePACS-1 and Messidor-2 {cite(1)}, then APTOS 2019 in the MICCAI talk {cite(3)}.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {["Gulshan et al. · p. 4", "Fig. 2", "MICCAI · 12:20"].map((c) => (
                <span key={c} className="rounded-full border border-gray-200 px-2.5 py-0.5 text-[10px] font-medium text-gray-600 dark:border-white/10 dark:text-gray-300">
                  {c}
                </span>
              ))}
            </div>
            <p className="flex items-center gap-1.5 text-[10px] font-medium text-[#027A48] dark:text-[#6CE9A6]">
              <Icon name="shield" className="size-3.5" />3 of 3 claims linked to a source
            </p>
          </div>
        </div>
      </div>
      <p className="mt-12 max-w-[420px] text-center text-2xl font-semibold leading-snug text-white">
        Centralize your sources, get evidence-backed answers.
      </p>
    </div>
  );
}

export function SignUpAside() {
  const steps = [
    ["Create a project", "Give it a title and a research question."],
    ["Import your sources", "PDFs, web pages, figures, videos, notes."],
    ["Ask your questions", "Every answer cites its source."],
  ];
  return (
    <div className="relative w-full max-w-[420px]">
      <p className="text-2xl font-semibold leading-snug text-white">Your first project in three steps</p>
      <ol className="mt-8 space-y-4">
        {steps.map(([a, b], i) => (
          <li key={a} className="flex gap-4 rounded-2xl bg-white/15 p-4 backdrop-blur">
            <span className="inline-flex size-9 shrink-0 items-center justify-center rounded-full bg-white text-sm font-bold text-primary-600">{i + 1}</span>
            <div>
              <p className="font-semibold text-white">{a}</p>
              <p className="mt-0.5 text-sm text-white/80">{b}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function SetupNotice() {
  return (
    <div className="mt-6 flex gap-2 rounded-2xl bg-[#FFFAEB] px-4 py-3 text-sm text-[#B54708] dark:bg-[#F79009]/10 dark:text-[#FEC84B]">
      <Icon name="alert" className="mt-0.5 size-4 shrink-0" />
      <span>
        Supabase is not configured. Copy <code>.env.example</code> to <code>.env.local</code>, add your project URL and anon key, then restart <code>npm run dev</code>.
      </span>
    </div>
  );
}

export function FormError({ message }: { message: string }) {
  return (
    <p role="alert" className="flex items-start gap-2 rounded-2xl bg-error-50 px-4 py-3 text-sm text-error-600 dark:bg-error-500/15 dark:text-[#FDA29B]">
      <Icon name="alert" className="mt-0.5 size-4 shrink-0" />
      {message}
    </p>
  );
}
