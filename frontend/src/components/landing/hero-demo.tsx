"use client";

import { useEffect, useRef } from "react";
import { Icon } from "@/components/icons";
import { MiniIcon, SourcePill } from "./bits";
import { DEMO_PILLS, DEMO_QUESTION, DEMO_SOURCES, DEMO_TOKENS } from "./data";

const reduceMotion = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/**
 * Animated demo: the question is typed, matching sources light up, the answer streams
 * word by word with citations, then the source pills and the verification badge pop in.
 * The animation is imperative (timers + DOM classes) for smoothness, exactly like the prototype.
 */
export function HeroDemo() {
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = root.current;
    if (!el) return;
    const $ = <T extends HTMLElement>(sel: string) => el.querySelector<T>(sel)!;
    const q = $("[data-demo='q']");
    const qt = $("[data-demo='q-text']");
    const a = $("[data-demo='a']");
    const at = $("[data-demo='a-text']");
    const ok = $("[data-demo='ok']");
    const st = $("[data-demo='status']");
    const stText = $("[data-demo='status-text']");
    const pills = [...el.querySelectorAll<HTMLElement>("[data-demo='pill']")];
    const srcs = [...el.querySelectorAll<HTMLElement>(".demo-src")];

    let timers: ReturnType<typeof setTimeout>[] = [];
    const later = (fn: () => void, ms: number) => timers.push(setTimeout(fn, ms));
    const show = (node: HTMLElement) => {
      node.classList.remove("opacity-0");
      node.classList.add("pop-in");
    };
    const reset = () => {
      [q, a, ok, ...pills].forEach((n) => {
        n.classList.add("opacity-0");
        n.classList.remove("pop-in");
      });
      srcs.forEach((s) => s.classList.remove("is-hit"));
      qt.textContent = "";
      at.innerHTML = "";
      st.classList.add("opacity-0");
    };

    const run = () => {
      if (reduceMotion()) {
        qt.textContent = DEMO_QUESTION;
        at.innerHTML = DEMO_TOKENS.join(" ");
        [q, a, ok, ...pills].forEach((n) => n.classList.remove("opacity-0"));
        [0, 3].forEach((i) => srcs[i].classList.add("is-hit"));
        return;
      }
      reset();
      let t = 500;
      later(() => {
        show(q);
        qt.classList.add("caret");
      }, t);
      [...DEMO_QUESTION].forEach((ch, i) => later(() => (qt.textContent += ch), t + 150 + i * 32));
      t += 150 + DEMO_QUESTION.length * 32 + 300;
      later(() => {
        qt.classList.remove("caret");
        st.classList.remove("opacity-0");
        stText.textContent = "Searching 6 sources";
      }, t);
      [0, 1, 3].forEach((idx, k) => later(() => srcs[idx].classList.add("is-hit"), t + 250 + k * 380));
      t += 250 + 3 * 380 + 200;
      later(() => {
        stText.textContent = "Writing the answer";
        srcs[1].classList.remove("is-hit");
        show(a);
      }, t);
      DEMO_TOKENS.forEach((tok, i) => later(() => (at.innerHTML += (i ? " " : "") + tok), t + 200 + i * 75));
      t += 200 + DEMO_TOKENS.length * 75 + 250;
      pills.forEach((p, i) => later(() => show(p), t + i * 160));
      t += pills.length * 160 + 300;
      later(() => {
        show(ok);
        st.classList.add("opacity-0");
      }, t);
      later(run, t + 5200); // loop
    };

    // Start when the demo scrolls into view.
    let observer: IntersectionObserver | null = null;
    if (reduceMotion() || !("IntersectionObserver" in window)) run();
    else {
      observer = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) {
            observer?.disconnect();
            run();
          }
        },
        { threshold: 0.3 },
      );
      observer.observe(el);
    }

    return () => {
      observer?.disconnect();
      timers.forEach(clearTimeout);
      timers = [];
    };
  }, []);

  return (
    <div className="rounded-[28px] border border-white/60 bg-white/30 p-6 shadow-[0_40px_80px_-30px_rgba(74,31,184,0.45)] backdrop-blur-md dark:border-white/10 dark:bg-white/5">
      <div
        ref={root}
        className="overflow-hidden rounded-[20px] bg-white text-left dark:bg-dark-secondary"
        aria-label="Animated demo: a question asked to the assistant and its cited answer"
      >
        <div className="flex items-center gap-2 border-b border-gray-100 px-5 py-4 dark:border-white/10">
          <span className="size-3 rounded-full bg-[#F04438]" />
          <span className="size-3 rounded-full bg-[#F79009]" />
          <span className="size-3 rounded-full bg-success-600" />
          <span className="ml-4 truncate text-sm text-gray-400">Project · Diabetic retinopathy and deep learning</span>
          <span
            data-demo="status"
            className="demo-fade ml-auto hidden items-center gap-2 rounded-full bg-primary-50 px-3 py-1 text-xs font-medium text-primary-600 opacity-0 dark:bg-primary-500/15 dark:text-primary-300 sm:inline-flex"
          >
            <span className="typing-dots">
              <i />
              <i />
              <i />
            </span>
            <span data-demo="status-text">Searching 6 sources</span>
          </span>
        </div>
        <div className="grid md:grid-cols-[250px_1fr]">
          <div className="hidden border-r border-gray-100 p-5 dark:border-white/10 md:block">
            <p className="text-sm text-gray-400">Project sources</p>
            <ul className="mt-3 space-y-1">
              {DEMO_SOURCES.map(([type, label]) => (
                <li key={label} className="demo-src flex items-center gap-3 rounded-xl px-2 py-1.5 text-sm text-gray-700 transition dark:text-gray-300">
                  <MiniIcon type={type} />
                  <span className="truncate">{label}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="flex min-h-[300px] flex-col gap-4 p-6 sm:p-8">
            <div className="flex justify-end">
              <p data-demo="q" className="demo-fade max-w-[85%] rounded-2xl bg-primary-500 px-5 py-3 text-sm font-medium text-white opacity-0 sm:text-base">
                <span data-demo="q-text" />
              </p>
            </div>
            <div data-demo="a" className="demo-fade max-w-[92%] rounded-2xl bg-gray-50 p-5 opacity-0 dark:bg-white/5">
              <p data-demo="a-text" className="min-h-[3em] text-sm leading-relaxed text-gray-700 dark:text-gray-300 sm:text-base" />
              <div className="mt-4 flex flex-wrap gap-2">
                {DEMO_PILLS.map(([type, label]) => (
                  <span key={label} data-demo="pill" className="demo-fade opacity-0">
                    <SourcePill type={type} label={label} />
                  </span>
                ))}
              </div>
            </div>
            <p
              data-demo="ok"
              className="demo-fade inline-flex w-fit items-center gap-2 rounded-full bg-success-50 px-3 py-1.5 text-sm font-medium text-success-600 opacity-0 dark:bg-success-600/15 dark:text-[#6CE9A6]"
            >
              <Icon name="shield" className="size-4" />3 of 3 claims linked to a source
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
