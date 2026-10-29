"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { Icon, type IconName } from "@/components/icons";
import { HeroDemo } from "./hero-demo";

const TITLE = "Your scientific research assistant, grounded in evidence";

type Pill = { bg: string; icon: IconName; text: string };
const PILLS: Record<"article" | "talk" | "figure" | "verified", Pill> = {
  article: { bg: "bg-[#40A9F3]", icon: "pdf", text: "Paper · p. 4" },
  talk: { bg: "bg-primary-500", icon: "video", text: "Talk · 12:20" },
  figure: { bg: "bg-[#FF745E]", icon: "figure", text: "Figure 3" },
  verified: { bg: "bg-success-600", icon: "shield", text: "Verified answer" },
};

function FloatPill({
  pill,
  position,
  anim,
  depth,
  delay,
  size = "large",
}: {
  pill: Pill;
  position: string;
  anim: string;
  depth: number;
  delay: number;
  size?: "large" | "medium";
}) {
  const large = size === "large";
  return (
    <span className={`absolute ${position} ${large ? "hidden wide:block" : "hidden lg:block wide:hidden"}`} data-depth={depth}>
      <span className="pill-pop block" style={{ animationDelay: `${delay}s` }}>
        <span
          className={`${anim} inline-flex items-center gap-2 whitespace-nowrap rounded-full font-semibold text-white shadow-[0_14px_30px_-10px_rgba(16,24,40,0.35)] ${
            large ? "px-5 py-3 text-lg" : "px-4 py-2.5 text-sm"
          } ${pill.bg}`}
        >
          <Icon name={pill.icon} className={large ? "size-5" : "size-4"} />
          {pill.text}
        </span>
      </span>
    </span>
  );
}

export function Hero() {
  const hero = useRef<HTMLElement>(null);

  // Mouse parallax on the floating pills and the glow, as in the prototype.
  useEffect(() => {
    const el = hero.current;
    if (!el || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    const layers = [...el.querySelectorAll<HTMLElement>("[data-depth]")];
    const orb = el.querySelector<HTMLElement>(".hero-orb");
    let raf = 0;
    let tx = 0;
    let ty = 0;
    const onMove = (e: MouseEvent) => {
      const r = el.getBoundingClientRect();
      if (e.clientY > r.bottom) return;
      tx = (e.clientX / window.innerWidth - 0.5) * 2;
      ty = ((e.clientY - r.top) / Math.min(r.height, 800) - 0.5) * 2;
      if (!raf)
        raf = requestAnimationFrame(() => {
          raf = 0;
          layers.forEach((l) => {
            const d = Number(l.dataset.depth);
            l.style.transform = `translate3d(${tx * d * 22}px, ${ty * d * 16}px, 0)`;
          });
          if (orb) orb.style.transform = `translate3d(calc(-50% + ${tx * 30}px), ${ty * 18}px, 0)`;
        });
    };
    window.addEventListener("mousemove", onMove, { passive: true });
    return () => {
      window.removeEventListener("mousemove", onMove);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <section id="hero" ref={hero} className="hero-glow relative">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[640px]" aria-hidden="true">
        <FloatPill pill={PILLS.article} position="left-[4.3%] top-[150px]" anim="float-a" depth={0.5} delay={0.55} />
        <FloatPill pill={PILLS.talk} position="right-[4.1%] top-[208px]" anim="float-b" depth={-0.4} delay={0.7} />
        <FloatPill pill={PILLS.figure} position="left-[10.5%] top-[455px]" anim="float-c" depth={0.7} delay={0.85} />
        <FloatPill pill={PILLS.verified} position="right-[14%] top-[478px]" anim="float-a" depth={-0.6} delay={1} />
      </div>
      <div className="hero-orb pointer-events-none absolute left-1/2 top-[440px] h-[520px] w-[1100px] -translate-x-1/2 rounded-full" aria-hidden="true" />

      <div className="relative mx-auto max-w-[1320px] px-5 pb-16 pt-20 sm:px-8">
        <div className="relative mx-auto max-w-[900px] text-center">
          <div className="relative">
            <FloatPill pill={PILLS.article} position="left-0 -top-2" anim="float-a" depth={0.5} delay={0.55} size="medium" />
            <FloatPill pill={PILLS.talk} position="right-0 top-6" anim="float-b" depth={-0.4} delay={0.7} size="medium" />
            <span className="gradient-chip chip-shine anim-up inline-flex items-center gap-2.5 rounded-full px-5 py-2 text-[17px] text-gray-700 dark:text-gray-200">
              <Icon name="layers" className="size-5 text-primary-500" />
              PDFs, web, figures and videos in one project
            </span>
          </div>

          <h1
            className="mt-9 text-4xl font-bold tracking-tight text-[#344054] dark:text-white/90 sm:text-5xl md:text-[64px] md:leading-[80px]"
            aria-label={TITLE}
          >
            {TITLE.split(" ").map((word, i) => (
              <span key={i} aria-hidden="true">
                <span className="word-in inline-block" style={{ animationDelay: `${0.12 + i * 0.07}s` }}>
                  {word}
                </span>{" "}
              </span>
            ))}
          </h1>

          <p className="anim-up mx-auto mt-7 max-w-[700px] text-lg leading-[30px] text-gray-600 dark:text-gray-300" style={{ animationDelay: ".75s" }}>
            Import your PDFs, web pages, figures and videos. Ask your questions.
            <br className="hidden md:inline" /> Get answers cited down to the page, the figure or the second.
          </p>

          <div className="relative mt-12">
            <FloatPill pill={PILLS.figure} position="left-[2%] -top-3" anim="float-c" depth={0.7} delay={0.85} size="medium" />
            <FloatPill pill={PILLS.verified} position="right-0 top-8" anim="float-a" depth={-0.6} delay={1} size="medium" />
            <div className="anim-up flex flex-wrap items-center justify-center gap-4" style={{ animationDelay: ".9s" }}>
              <Link
                href="/signup"
                className="btn-shine relative inline-flex h-[60px] items-center overflow-hidden rounded-full bg-primary-500 px-8 text-[17px] font-medium text-white shadow-[0_14px_28px_-12px_rgba(122,90,248,0.8)] transition hover:-translate-y-0.5 hover:bg-primary-600"
              >
                Start for free
              </Link>
              <Link
                href="/assistant"
                className="inline-flex h-[60px] items-center gap-2.5 rounded-full border border-gray-200 bg-white px-8 text-[17px] font-medium text-gray-700 transition hover:-translate-y-0.5 hover:border-primary-200 dark:border-gray-700 dark:bg-white/5 dark:text-gray-200"
              >
                <Icon name="video" className="size-5" />
                Watch the demo
              </Link>
            </div>
          </div>

          <div className="mt-10 flex flex-wrap justify-center gap-3 lg:hidden" aria-hidden="true">
            {(
              [
                [PILLS.article, "float-a", 1.0],
                [PILLS.talk, "float-b", 1.1],
                [PILLS.figure, "float-c", 1.2],
                [PILLS.verified, "float-a", 1.3],
              ] as [Pill, string, number][]
            ).map(([pill, anim, delay]) => (
              <span key={pill.text} className="pill-pop" style={{ animationDelay: `${delay}s` }}>
                <span
                  className={`${anim} inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-3.5 py-2 text-xs font-semibold text-white shadow-[0_10px_20px_-8px_rgba(16,24,40,0.35)] ${pill.bg}`}
                >
                  <Icon name={pill.icon} className="size-4" />
                  {pill.text}
                </span>
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="relative px-5 pb-24 pt-10 sm:px-8">
        <div className="anim-up mx-auto max-w-[1250px]" style={{ animationDelay: "1.05s" }}>
          <HeroDemo />
        </div>
      </div>
    </section>
  );
}
