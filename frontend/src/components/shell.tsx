"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { Icon, type IconName } from "./icons";
import { Logo } from "./logo";
import { ThemeButton } from "./theme";
import { useToast } from "./toast";
import { getSupabase } from "@/lib/supabase/client";

const NAV: [string, string, IconName][] = [
  ["/projects", "My projects", "folder"],
  ["/assistant", "Research assistant", "chat"],
  ["/sources", "Sources", "library"],
  ["/papers", "Library", "book"],
  ["/research-twin", "Research Twin", "layers"],
  ["/knowledge-graph", "Knowledge Graph", "network"],
];

export type ShellUser = { email: string | null; name: string | null };

function initials(user: ShellUser) {
  const base = user.name || user.email || "?";
  const parts = base.split(/[\s@._-]+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
}

export function Shell({ user, children }: { user: ShellUser; children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const toast = useToast();
  const [open, setOpen] = useState(false);

  useEffect(() => setOpen(false), [pathname]);

  async function signOut() {
    await getSupabase().auth.signOut();
    router.replace("/signin");
    router.refresh();
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gray-50 dark:bg-dark-primary">
      <header className="z-50 flex h-[65px] shrink-0 items-center border-b border-gray-100 bg-white px-4 dark:border-gray-800 dark:bg-dark-primary sm:px-6">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <button type="button" onClick={() => setOpen((o) => !o)} className="rounded-md p-1 text-gray-500 lg:hidden" aria-label="Menu">
            <Icon name={open ? "x" : "menu"} className="size-6" />
          </button>
          <Logo />
        </div>
        <div className="flex items-center gap-3">
          <ThemeButton />
          <button
            type="button"
            onClick={() => toast("No new notifications")}
            className="relative inline-flex size-11 items-center justify-center rounded-full border border-gray-200 text-gray-500 hover:bg-gray-100 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-white/5"
            aria-label="Notifications"
          >
            <Icon name="bell" />
            <span className="absolute right-2.5 top-2.5 size-2 rounded-full bg-[#F79009]" />
          </button>
          <button
            type="button"
            onClick={signOut}
            title={`Sign out${user.email ? ` (${user.email})` : ""}`}
            className="inline-flex size-11 items-center justify-center rounded-full bg-primary-100 text-sm font-semibold text-primary-700 dark:bg-primary-500/20 dark:text-primary-200"
          >
            {initials(user)}
          </button>
        </div>
      </header>

      <div className="relative flex min-h-0 flex-1">
        <aside
          className={`z-40 flex w-[280px] shrink-0 flex-col border-r border-gray-100 bg-white transition-transform duration-300 dark:border-gray-800 dark:bg-dark-primary max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:top-[65px] ${
            open ? "translate-x-0" : "max-lg:-translate-x-full"
          }`}
        >
          <div className="custom-scrollbar flex flex-1 flex-col justify-between overflow-y-auto">
            <div className="px-4 py-6">
              <h2 className="px-2 text-xs font-medium tracking-wider text-gray-400">My workspace</h2>
              <nav className="mt-3 space-y-1" aria-label="Main navigation">
                {NAV.map(([href, label, icon]) => {
                  const on = pathname === href || pathname.startsWith(`${href}/`);
                  return (
                    <Link
                      key={href}
                      href={href}
                      aria-current={on ? "page" : undefined}
                      className={`flex h-11 items-center gap-3 rounded-full px-4 text-sm font-medium transition ${
                        on
                          ? "bg-gray-100 text-gray-800 dark:bg-white/5 dark:text-white/90"
                          : "text-gray-500 hover:bg-gray-100 hover:text-gray-800 dark:text-gray-400 dark:hover:bg-white/5 dark:hover:text-white/90"
                      }`}
                    >
                      <Icon name={icon} className={`size-5${on ? " text-primary-500" : ""}`} />
                      {label}
                    </Link>
                  );
                })}
              </nav>
            </div>
            <div className="px-4 pb-6">
              <div className="widget-bg rounded-2xl px-4 pb-4 pt-5">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-gray-800 dark:text-white/90">Student plan</p>
                  <span className="rounded-full bg-white px-2 py-0.5 text-xs font-medium text-[#344054] dark:bg-white/10 dark:text-white/70">Free</span>
                </div>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">Free during the beta</p>
                <button
                  type="button"
                  onClick={() => toast("Researcher plan: unlimited projects and every source type")}
                  className="mt-4 inline-flex text-sm font-medium text-primary-600 hover:text-primary-700 dark:text-primary-300"
                >
                  Upgrade to Researcher plan
                </button>
              </div>
            </div>
          </div>
        </aside>
        {open && (
          <div onClick={() => setOpen(false)} className="fixed inset-0 top-[65px] z-30 bg-gray-800/60 backdrop-blur-sm lg:hidden" />
        )}
        <main id="main" className="custom-scrollbar min-w-0 flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
