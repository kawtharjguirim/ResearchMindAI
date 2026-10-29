"use client";

import Link from "next/link";
import { useState } from "react";
import { Icon } from "@/components/icons";
import { Badge } from "@/components/ui";
import { SourcePill } from "./bits";
import { SOURCE_TABS } from "./data";

type TabKey = keyof typeof SOURCE_TABS;

const Bar = ({ w }: { w: number }) => <div className="h-2.5 rounded-full bg-gray-100 dark:bg-white/10" style={{ width: `${w}%` }} />;

const Highlight = () => (
  <div className="rounded-lg border border-primary-300 bg-primary-50 p-2 dark:border-primary-500/40 dark:bg-primary-500/10">
    <div className="h-2.5 rounded-full bg-primary-300/80" style={{ width: "94%" }} />
    <div className="mt-2 h-2.5 rounded-full bg-primary-300/80" style={{ width: "78%" }} />
  </div>
);

const frame = "rounded-2xl border border-gray-200 bg-white p-5 shadow-theme-xs dark:border-white/10 dark:bg-dark-primary";

function Preview({ tab }: { tab: TabKey }) {
  if (tab === "pdf")
    return (
      <div className={frame}>
        <div className="flex justify-between text-xs text-gray-400">
          <span>Benali et al. (2023)</span>
          <span>p. 4</span>
        </div>
        <p className="mt-3 text-sm font-semibold text-gray-800 dark:text-white/90">3.1 Data</p>
        <div className="mt-4 space-y-2.5">
          <Bar w={100} />
          <Bar w={92} />
          <Highlight />
          <Bar w={88} />
          <Bar w={95} />
          <Bar w={60} />
        </div>
      </div>
    );

  if (tab === "web")
    return (
      <div className={frame}>
        <div className="flex items-center gap-2 rounded-full bg-gray-100 px-3 py-1.5 text-xs text-gray-500 dark:bg-white/5">
          <Icon name="link" className="size-3.5" />
          grading-criteria.org/icdr
        </div>
        <p className="mt-4 text-sm font-semibold text-gray-800 dark:text-white/90">ICDR grading criteria</p>
        <div className="mt-4 space-y-2.5">
          <Bar w={96} />
          <Highlight />
          <Bar w={84} />
        </div>
        <div className="mt-4 flex gap-2">
          <Badge tone="gray">Source kept</Badge>
          <Badge tone="gray">Date: 2024</Badge>
        </div>
      </div>
    );

  if (tab === "figure")
    return (
      <div className={frame}>
        <div className="flex justify-between text-xs text-gray-400">
          <span>Benali et al. (2023)</span>
          <span>Fig. 3</span>
        </div>
        <svg viewBox="0 0 300 150" className="mt-3 w-full" role="img" aria-label="ROC curves">
          <line x1="30" y1="125" x2="290" y2="125" stroke="#D0D5DD" />
          <line x1="30" y1="125" x2="30" y2="10" stroke="#D0D5DD" />
          <line x1="30" y1="125" x2="290" y2="10" stroke="#D0D5DD" strokeDasharray="4 4" />
          <path className="draw-line" d="M30 125 C 38 35, 90 18, 290 13" fill="none" stroke="#7A5AF8" strokeWidth="3" />
          <path className="draw-line draw-delay" d="M30 125 C 50 70, 120 40, 290 26" fill="none" stroke="#1C9EF6" strokeWidth="2.5" />
          <rect x="190" y="84" width="92" height="34" rx="6" fill="#fff" stroke="#EAECF0" />
          <circle cx="200" cy="95" r="3.5" fill="#7A5AF8" />
          <text x="208" y="99" fontSize="10" fill="#344054">EyePACS</text>
          <circle cx="200" cy="109" r="3.5" fill="#1C9EF6" />
          <text x="208" y="113" fontSize="10" fill="#344054">APTOS 2019</text>
        </svg>
        <div className="mt-2 flex gap-2">
          <Badge tone="violet">OCR: axes and legend</Badge>
          <Badge tone="green">2 curves detected</Badge>
        </div>
      </div>
    );

  if (tab === "video")
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-theme-xs dark:border-white/10 dark:bg-dark-primary">
        <div className="relative flex aspect-video items-center justify-center rounded-xl bg-gradient-to-br from-[#1D2939] to-[#4A1FB8]">
          <span className="inline-flex size-11 items-center justify-center rounded-full bg-white/90 text-gray-800">
            <svg viewBox="0 0 24 24" className="ml-0.5 size-5" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
          </span>
          <div className="absolute inset-x-3 bottom-3 h-1 rounded-full bg-white/20">
            <div className="progress-grow h-1 rounded-full bg-primary-400" style={{ width: "38%" }} />
          </div>
          <span className="absolute right-3 top-3 rounded-md bg-black/60 px-1.5 py-0.5 text-xs text-white">12:20</span>
        </div>
        <ul className="mt-3 space-y-1 text-xs">
          {(
            [
              ["05:30", "Problem", false],
              ["12:20", "Methodology", true],
              ["25:40", "Experiments", false],
            ] as [string, string, boolean][]
          ).map(([time, label, on]) => (
            <li
              key={time}
              className={`flex gap-3 rounded-lg px-2 py-1 ${on ? "bg-primary-50 font-medium text-primary-700 dark:bg-primary-500/15 dark:text-primary-200" : "text-gray-500"}`}
            >
              <span className="w-10 tabular-nums">{time}</span>
              {label}
            </li>
          ))}
        </ul>
      </div>
    );

  return (
    <div className={frame}>
      <div className="flex items-center justify-between text-xs text-gray-400">
        <span>Meeting notes · March 12</span>
        <Badge tone="gray">Private</Badge>
      </div>
      <p className="mt-3 text-sm font-semibold text-gray-800 dark:text-white/90">Decisions</p>
      <div className="mt-4 space-y-2.5">
        <Bar w={90} />
        <Highlight />
        <Bar w={70} />
      </div>
      <p className="mt-4 flex items-center gap-2 text-xs font-medium text-success-600">
        <Icon name="shield" className="size-4" />
        Visible only to you
      </p>
    </div>
  );
}

export function SourceTabs() {
  const [active, setActive] = useState<TabKey>("pdf");
  const tab = SOURCE_TABS[active];

  return (
    <div data-reveal className="mt-10">
      <div className="flex justify-center">
        <div className="inline-flex max-w-full gap-1 overflow-x-auto rounded-full bg-gray-100 p-1.5 dark:bg-white/5" role="tablist" aria-label="Source types">
          {(Object.keys(SOURCE_TABS) as TabKey[]).map((key) => {
            const t = SOURCE_TABS[key];
            const on = active === key;
            return (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={on}
                onClick={() => setActive(key)}
                className={`inline-flex h-10 shrink-0 items-center gap-2 rounded-full px-4 text-sm font-medium transition ${
                  on
                    ? "bg-white text-gray-800 shadow-theme-xs dark:bg-white/15 dark:text-white"
                    : "text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-white"
                }`}
              >
                <Icon name={t.icon} className="size-5" />
                {t.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* key forces a remount so the swap-in animations replay on every tab change */}
      <div key={active} className="swap-in mx-auto mt-10 max-w-[860px]" role="tabpanel">
        <div className="rounded-[32px] bg-gradient-to-br from-[#FBD5F1] via-[#E9E3FF] to-[#D6DDFF] p-5 dark:from-[#FF58D5]/20 dark:via-primary-500/15 dark:to-[#4E6EFF]/20">
          <div className="grid items-center gap-6 rounded-[22px] bg-white p-6 dark:bg-dark-secondary md:grid-cols-2 md:p-8">
            <div>
              <Preview tab={active} />
            </div>
            <div className="space-y-4">
              <div className="flex justify-end">
                <p className="max-w-[85%] rounded-2xl bg-primary-500 px-4 py-2.5 text-sm font-medium text-white">{tab.question}</p>
              </div>
              <div className="stagger-2 max-w-[90%] rounded-2xl bg-gray-50 p-4 dark:bg-white/5">
                <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">{tab.answer}</p>
                <div className="mt-3">
                  <SourcePill type={tab.pill[0]} label={tab.pill[1]} className="!text-xs !text-primary-600 dark:!text-primary-300" />
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-8 text-center">
          <h3 className="text-xl font-semibold text-gray-800 dark:text-white/90">{tab.title}</h3>
          <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-gray-500 dark:text-gray-400">{tab.description}</p>
          <Link href="/sources" className="gradient-btn mt-6 inline-flex h-11 items-center rounded-full px-6 text-sm font-medium">
            {tab.cta}
          </Link>
        </div>
      </div>
    </div>
  );
}
