import Link from "next/link";
import { useId } from "react";

export function LogoMark({ className = "size-8" }: { className?: string }) {
  const gid = useId().replace(/:/g, "");
  return (
    <svg viewBox="0 0 40 40" className={`${className} shrink-0`} fill="none" aria-hidden="true">
      <defs>
        <linearGradient id={`rmring-${gid}`} x1="8" y1="10" x2="30" y2="32" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#725CFF" />
          <stop offset="1" stopColor="#9B8AFB" />
        </linearGradient>
      </defs>
      <path d="M11 11 15.5 15.5M29 11 24.5 15.5M20 28v4.5" className="stroke-gray-800 dark:stroke-white/80" strokeWidth="2.6" strokeLinecap="round" />
      <circle cx="9" cy="9" r="3" className="stroke-gray-800 dark:stroke-white/80" strokeWidth="2.4" />
      <circle cx="31" cy="9" r="3" className="stroke-gray-800 dark:stroke-white/80" strokeWidth="2.4" />
      <circle cx="20" cy="35" r="3" stroke="#12B76A" strokeWidth="2.4" />
      <circle cx="20" cy="21" r="7.5" stroke={`url(#rmring-${gid})`} strokeWidth="3.4" />
      <circle cx="20" cy="20" r="1.8" fill="#6938EF" />
      <path d="M20 21v3" stroke="#6938EF" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function Logo({ href = "/projects" }: { href?: string }) {
  return (
    <Link href={href} className="flex items-center gap-2" aria-label="ResearchMind AI">
      <LogoMark />
      <span className="text-xl font-semibold tracking-tight">
        <span className="text-gray-800 dark:text-white/90">Research</span>
        <span className="text-primary-500">Mind</span>
      </span>
    </Link>
  );
}
