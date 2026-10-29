"use client";

import Link from "next/link";
import { useState } from "react";
import { Icon } from "@/components/icons";
import { PLANS } from "./data";

const BUTTON = {
  outline: "border border-gray-200 text-gray-800 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-white/5",
  gradient: "gradient-btn",
  dark: "bg-gray-700 text-white hover:bg-gray-800 dark:bg-white/15 dark:hover:bg-white/25",
};

export function Pricing() {
  const [yearly, setYearly] = useState(false);

  const toggle = (on: boolean, label: React.ReactNode, value: boolean) => (
    <button
      type="button"
      aria-pressed={on}
      onClick={() => setYearly(value)}
      className={`h-10 rounded-full px-5 text-sm font-medium transition ${
        on ? "bg-white text-gray-800 shadow-theme-xs dark:bg-white/15 dark:text-white" : "text-gray-500 dark:text-gray-400"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="mt-10">
      <div className="flex justify-center">
        <div className="inline-flex items-center gap-1 rounded-full bg-gray-100 p-1.5 dark:bg-white/5">
          {toggle(!yearly, "Monthly", false)}
          {toggle(
            yearly,
            <>
              Yearly <span className="ml-1 text-xs font-semibold text-primary-500">−20%</span>
            </>,
            true,
          )}
        </div>
      </div>

      <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
        {PLANS.map((plan, i) => {
          const price = plan.monthly === null ? "Custom" : `€${yearly ? plan.yearly : plan.monthly}`;
          return (
            <div
              key={plan.name}
              data-reveal
              style={{ transitionDelay: `${i * 80}ms` }}
              className={`lift-on-hover flex flex-col rounded-[20px] border bg-white p-7 transition hover:shadow-theme-lg dark:bg-dark-secondary ${
                plan.popular ? "border-primary-400 dark:border-primary-500/60" : "border-transparent shadow-theme-md dark:border-white/5"
              }`}
            >
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-gray-800 dark:text-white/90">{plan.name}</h3>
                {plan.popular && (
                  <span className="rounded-full bg-primary-50 px-2.5 py-0.5 text-xs font-medium text-primary-600 dark:bg-primary-500/15 dark:text-primary-300">
                    Popular
                  </span>
                )}
              </div>
              <p className="mt-4 flex items-baseline gap-1.5">
                <span key={`${plan.name}-${yearly}`} className="pop-in text-4xl font-bold text-gray-800 dark:text-white/90">
                  {price}
                </span>
                {plan.monthly ? <span className="text-sm text-gray-500">{yearly ? "per year" : "per month"}</span> : null}
              </p>
              <p className="mt-3 min-h-[40px] text-sm text-gray-500 dark:text-gray-400">{plan.description}</p>
              {plan.monthly === null ? (
                <a
                  href="#contact"
                  className={`mt-5 inline-flex min-h-12 items-center justify-center rounded-full px-5 py-2 text-center text-sm font-semibold transition ${BUTTON[plan.style]}`}
                >
                  {plan.cta}
                </a>
              ) : (
                <Link
                  href="/signup"
                  className={`mt-5 inline-flex min-h-12 items-center justify-center rounded-full px-5 py-2 text-center text-sm font-semibold transition ${BUTTON[plan.style]}`}
                >
                  {plan.cta}
                </Link>
              )}
              <ul className="mt-7 space-y-3">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-sm text-gray-700 dark:text-gray-300">
                    <span className="mt-0.5 text-gray-400">
                      <Icon name="check" className="size-4" />
                    </span>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
      <p className="mt-8 text-center text-xs text-gray-400">Indicative prices — academic prototype</p>
    </div>
  );
}
