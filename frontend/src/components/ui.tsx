// Shared style tokens and small building blocks from the prototype.
import type { ReactNode } from "react";
import { Icon, type IconName } from "./icons";

export const card =
  "rounded-[20px] border border-gray-100 bg-white shadow-theme-md dark:border-white/5 dark:bg-dark-secondary";

export const btnPrimary =
  "gradient-btn inline-flex h-11 items-center justify-center gap-2 rounded-full px-5 text-sm font-medium text-white";

export const btnSecondary =
  "inline-flex h-11 items-center justify-center gap-2 rounded-full border border-gray-200 bg-white px-5 text-sm font-medium text-gray-700 transition hover:bg-gray-50 dark:border-gray-700 dark:bg-white/5 dark:text-gray-300 dark:hover:bg-white/10";

export const inputPill =
  "h-12 w-full rounded-full border border-gray-300 bg-transparent px-5 text-sm text-gray-800 shadow-theme-xs placeholder:text-gray-400 focus:border-primary-300 focus:outline-0 focus:ring-3 focus:ring-primary-300/20 dark:border-gray-700 dark:text-white/90 dark:placeholder:text-white/30";

export const TONES = {
  violet: "bg-primary-50 text-primary-700 dark:bg-primary-500/15 dark:text-primary-300",
  blue: "bg-[#EEF2FF] text-[#3B55E6] dark:bg-[#4E6EFF]/15 dark:text-[#9DB0FF]",
  green: "bg-success-50 text-[#027A48] dark:bg-success-600/15 dark:text-[#6CE9A6]",
  orange: "bg-[#FFFAEB] text-[#B54708] dark:bg-[#F79009]/15 dark:text-[#FEC84B]",
  red: "bg-error-50 text-error-600 dark:bg-error-500/15 dark:text-[#FDA29B]",
  gray: "bg-gray-100 text-gray-700 dark:bg-white/10 dark:text-gray-300",
} as const;

export type Tone = keyof typeof TONES;

export function Badge({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ${TONES[tone]}`}>
      {children}
    </span>
  );
}

export const SOURCE_TYPES = {
  pdf: ["PDF", "bg-error-50 text-error-500 dark:bg-error-500/15"],
  web: ["Web", "bg-[#EEF2FF] text-[#4E6EFF] dark:bg-[#4E6EFF]/15"],
  figure: ["Figure", "bg-[#E8F5FE] text-[#1C9EF6] dark:bg-[#1C9EF6]/15"],
  video: ["Video", "bg-[#FFF0FB] text-[#E23FB8] dark:bg-[#FF58D5]/15"],
  personal: ["Personal document", "bg-primary-50 text-primary-600 dark:bg-primary-500/15 dark:text-primary-300"],
} as const;

export type SourceType = keyof typeof SOURCE_TYPES;

export function SourceIcon({ type, small = false }: { type: SourceType; small?: boolean }) {
  const [label, cls] = SOURCE_TYPES[type];
  return small ? (
    <span className={`inline-flex size-6 shrink-0 items-center justify-center rounded-lg ${cls}`} title={label}>
      <Icon name={type as IconName} className="size-3.5" />
    </span>
  ) : (
    <span className={`inline-flex size-10 shrink-0 items-center justify-center rounded-xl ${cls}`} title={label}>
      <Icon name={type as IconName} className="size-5" />
    </span>
  );
}

export function Progress({ value, tone = "bg-primary-500", className = "h-1.5" }: { value: number; tone?: string; className?: string }) {
  return (
    <div
      className={`${className} w-full overflow-hidden rounded-full bg-gray-100 dark:bg-white/10`}
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className={`h-full rounded-full ${tone}`} style={{ width: `${value}%` }} />
    </div>
  );
}
