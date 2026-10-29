"use client";

import Link from "next/link";
import { useEffect } from "react";
import { Icon } from "@/components/icons";
import { ThemeButton } from "@/components/theme";
import { LandingLogo } from "./bits";

const navLink =
  "rounded-full px-3 py-2 text-[15px] font-medium text-gray-600 transition hover:text-primary-600 dark:text-gray-300 dark:hover:text-primary-300 2xl:px-4 2xl:text-[17px]";

const PAGES: [string, string][] = [
  ["/signin", "Sign in"],
  ["/signup", "Sign up"],
  ["/projects", "My projects"],
  ["/sources", "Sources"],
  ["/assistant", "Research assistant"],
  ["/research-twin", "Research Twin"],
  ["/knowledge-graph", "Knowledge Graph"],
];

export function LandingHeader() {
  // Close the dropdown menus when clicking outside them or on one of their links.
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      document.querySelectorAll<HTMLDetailsElement>("details.menu-details[open]").forEach((menu) => {
        if (!menu.contains(target) || target.closest("a")) menu.removeAttribute("open");
      });
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  return (
    <header className="sticky top-0 z-50 border-b border-gray-100 bg-white/90 py-5 backdrop-blur dark:border-gray-800 dark:bg-dark-primary/90">
      <div className="grid w-full grid-cols-[auto_1fr] items-center gap-4 px-5 sm:px-8 xl:grid-cols-[1fr_auto_1fr] xl:px-9">
        <div>
          <LandingLogo big />
        </div>

        <nav className="hidden items-center gap-1 xl:flex 2xl:gap-3" aria-label="Site navigation">
          <Link href="/" aria-current="page" className={`${navLink} !text-primary-500`}>
            Home
          </Link>
          <Link href="/assistant" className={navLink}>
            Assistant
          </Link>
          <a href="#pricing" className={navLink}>
            Pricing
          </a>
          <a href="#contact" className={navLink}>
            Contact
          </a>
          <details className="menu-details relative">
            <summary className={`${navLink} flex cursor-pointer list-none items-center gap-1`}>
              Pages
              <Icon name="chevronDown" className="menu-chevron size-4 transition" />
            </summary>
            <div className="absolute left-1/2 top-12 w-60 -translate-x-1/2 rounded-2xl border border-gray-100 bg-white p-2 shadow-theme-lg dark:border-white/10 dark:bg-dark-secondary">
              {PAGES.map(([href, label]) => (
                <Link
                  key={href}
                  href={href}
                  className="block rounded-xl px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-800 dark:text-gray-300 dark:hover:bg-white/5"
                >
                  {label}
                </Link>
              ))}
            </div>
          </details>
        </nav>

        <div className="flex items-center justify-self-end gap-3 2xl:gap-4">
          <details className="menu-details relative xl:hidden">
            <summary
              className="inline-flex size-11 cursor-pointer list-none items-center justify-center rounded-full border border-gray-200 text-gray-600 dark:border-gray-700 dark:text-gray-300"
              aria-label="Menu"
            >
              <Icon name="menu" />
            </summary>
            <div className="absolute right-0 top-14 w-64 rounded-2xl border border-gray-100 bg-white p-2 shadow-theme-lg dark:border-white/10 dark:bg-dark-secondary">
              <Link href="/" className="block rounded-xl px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-white/5">
                Home
              </Link>
              <Link href="/assistant" className="block rounded-xl px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-white/5">
                Assistant
              </Link>
              <a href="#pricing" className="block rounded-xl px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-white/5">
                Pricing
              </a>
              <a href="#contact" className="block rounded-xl px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-white/5">
                Contact
              </a>
              <p className="px-4 pb-1 pt-3 text-xs text-gray-400">Pages</p>
              {PAGES.map(([href, label]) => (
                <Link key={href} href={href} className="block rounded-xl px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-white/5">
                  {label}
                </Link>
              ))}
            </div>
          </details>
          <ThemeButton variant="outline" />
          <Link href="/signin" className="whitespace-nowrap text-[15px] font-medium text-gray-800 hover:text-primary-500 dark:text-gray-200 2xl:text-[17px]">
            Sign in
          </Link>
          <Link
            href="/signup"
            className="gradient-btn hidden h-11 shrink-0 items-center whitespace-nowrap rounded-full px-5 text-[15px] font-medium sm:inline-flex 2xl:h-[54px] 2xl:px-6 2xl:text-[17px]"
          >
            Start for free
          </Link>
        </div>
      </div>
    </header>
  );
}
