import Link from "next/link";
import { Icon } from "@/components/icons";
import { LogoMark } from "@/components/logo";
import { TYPE_COLOR, typeIcon, type DemoType } from "./data";

export function LandingLogo({ big = false }: { big?: boolean }) {
  return (
    <Link href="/" className="flex items-center gap-2" aria-label="ResearchMind AI — home">
      <LogoMark className={big ? "size-8 2xl:size-10" : "size-8"} />
      <span className={`${big ? "text-xl 2xl:text-[26px]" : "text-xl"} whitespace-nowrap font-semibold tracking-tight`}>
        <span className="text-gray-800 dark:text-white/90">Research</span>
        <span className="text-primary-500">Mind</span>
      </span>
      <span className={`hidden rounded-md bg-primary-500 px-1.5 py-0.5 ${big ? "text-xs 2xl:text-[15px]" : "text-xs"} font-semibold text-white sm:inline`}>
        Beta
      </span>
    </Link>
  );
}

export function MiniIcon({ type }: { type: DemoType }) {
  return (
    <span className={`inline-flex size-7 shrink-0 items-center justify-center rounded-lg ${TYPE_COLOR[type]}`}>
      <Icon name={typeIcon(type)} className="size-4" />
    </span>
  );
}

export function SourcePill({ type, label, className = "" }: { type: DemoType; label: string; className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-3 py-1 text-sm font-medium text-gray-700 dark:border-white/10 dark:bg-white/5 dark:text-gray-200 ${className}`}
    >
      <span className={TYPE_COLOR[type].split(" ")[0]}>
        <Icon name={typeIcon(type)} className="size-4" />
      </span>
      {label}
    </span>
  );
}

export function SectionTitle({ title, subtitle, light = false }: { title: string; subtitle?: string; light?: boolean }) {
  return (
    <div data-reveal className="mx-auto max-w-2xl text-center">
      <h2
        className={`text-3xl font-bold tracking-tight md:text-[40px] md:leading-[48px] ${
          light ? "text-white" : "text-gray-800 dark:text-white/90"
        }`}
      >
        {title}
      </h2>
      {subtitle && <p className={`mt-4 text-base ${light ? "text-white/60" : "text-gray-500 dark:text-gray-400"}`}>{subtitle}</p>}
    </div>
  );
}
