import Link from "next/link";
import { Icon } from "@/components/icons";
import { SourceIcon, type SourceType } from "@/components/ui";
import { LandingLogo, SectionTitle } from "./bits";
import { FAQ, FEATURES, PROFILES } from "./data";

export function SourcesStrip() {
  const items: [SourceType, string][] = [
    ["pdf", "PDF"],
    ["web", "Web"],
    ["figure", "Figures"],
    ["video", "YouTube videos"],
    ["personal", "Personal documents"],
  ];
  return (
    <section className="bg-white py-14 dark:bg-dark-primary">
      <p data-reveal className="px-5 text-center text-lg text-gray-500 dark:text-gray-400">
        All your scientific sources, in a single project
      </p>
      <ul className="mx-auto mt-8 flex max-w-[1100px] flex-wrap items-center justify-center gap-4 px-5">
        {items.map(([type, label], i) => (
          <li
            key={type}
            data-reveal
            style={{ transitionDelay: `${i * 70}ms` }}
            className="inline-flex items-center gap-3 rounded-full border border-gray-200 bg-white py-2 pl-2 pr-6 text-lg font-medium text-gray-700 transition hover:border-primary-200 dark:border-gray-700 dark:bg-white/5 dark:text-gray-200"
          >
            <SourceIcon type={type} />
            {label}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function Features() {
  return (
    <section id="features" className="bg-gray-50 py-24 dark:bg-[#101828]">
      <div className="mx-auto max-w-[1000px] px-5">
        <SectionTitle
          title="Everything a researcher needs, in one place"
          subtitle="Read, retrieve, compare and connect the literature to your own project, without juggling five tools."
        />
        <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(([icon, title, text], i) => (
            <div
              key={title}
              data-reveal
              style={{ transitionDelay: `${(i % 3) * 90}ms` }}
              className="lift-on-hover group rounded-[20px] border border-gray-200 bg-white p-8 transition hover:border-primary-200 hover:shadow-theme-lg dark:border-white/10 dark:bg-dark-primary"
            >
              <span className="feature-icon transition group-hover:scale-105">
                <Icon name={icon} className="size-7 text-white" />
              </span>
              <h3 className="mt-7 text-xl font-semibold text-gray-800 dark:text-white/90">{title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-gray-500 dark:text-gray-400">{text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function Benefits() {
  return (
    <section className="bg-dark-primary py-24">
      <div className="mx-auto max-w-[900px] px-5">
        <SectionTitle title="What you gain every day" subtitle="Less time searching, more time understanding and deciding." light />

        <div className="mt-12 grid gap-6 md:grid-cols-2">
          <div data-reveal className="relative min-h-[300px] overflow-hidden rounded-[20px] bg-primary-500 p-10">
            <h3 className="text-2xl font-bold text-white">Less reading time</h3>
            <p className="mt-3 max-w-sm text-sm leading-relaxed text-white/80">
              Ask a question instead of rereading ten papers: the useful passages come straight to you.
            </p>
            <span className="float-b absolute bottom-16 left-7 inline-flex items-center gap-1.5 rounded-full bg-[#3BA3F5] px-3.5 py-2 text-xs font-semibold text-white shadow-theme-sm">
              <Icon name="search" className="size-3.5" />3 passages found
            </span>
            <span className="float-c absolute bottom-7 right-8 inline-flex items-center gap-1.5 rounded-full bg-[#FF745E] px-3.5 py-2 text-xs font-semibold text-white shadow-theme-sm">
              <Icon name="clock" className="size-3.5" />
              12:20
            </span>
          </div>

          <div
            data-reveal
            style={{ transitionDelay: "90ms" }}
            className="relative min-h-[300px] overflow-hidden rounded-[20px] bg-gradient-to-br from-[#A2E4E4] to-[#1C9EF6] p-10"
          >
            <h3 className="text-2xl font-bold text-white">The origin of every piece of information</h3>
            <p className="mt-3 max-w-sm text-sm leading-relaxed text-white/90">
              No more “I read it somewhere”: page, figure or minute, everything is traced.
            </p>
            <span className="float-a absolute bottom-10 left-10 right-24 inline-flex items-center gap-3 rounded-xl bg-white px-4 py-3 text-xs font-medium text-gray-700 shadow-theme-lg">
              <span className="text-error-500">
                <Icon name="pdf" className="size-4" />
              </span>
              Benali et al. · p. 11 · 6 Limitations
            </span>
          </div>
        </div>

        <div className="mt-6 grid gap-6 md:grid-cols-[1.45fr_1fr]">
          <div data-reveal className="rounded-[20px] border border-white/10 bg-white/[0.04] p-10">
            <h3 className="text-2xl font-bold text-white">Your project, linked to the literature</h3>
            <p className="mt-3 text-sm leading-relaxed text-white/60">
              Methods and limitations found in your sources become suggestions for your Research Twin.
            </p>
            <div className="mt-6 flex flex-wrap gap-2.5">
              {["Question", "Hypotheses", "Methods", "Results", "Research gaps"].map((chip, i) => (
                <span
                  key={chip}
                  className="twin-chip rounded-full border border-white/20 px-3 py-1.5 text-xs font-medium text-white/90"
                  style={{ animationDelay: `${i * 0.6}s` }}
                >
                  {chip}
                </span>
              ))}
            </div>
          </div>
          <div data-reveal style={{ transitionDelay: "90ms" }} className="rounded-[20px] border border-white/10 bg-white/[0.04] p-10">
            <h3 className="text-2xl font-bold text-white">A trace of your progress</h3>
            <p className="mt-3 text-sm leading-relaxed text-white/60">
              Every validated hypothesis, every new result: your research keeps its memory.
            </p>
            <div className="mt-6 space-y-2">
              {["Hypothesis H2 validated", "Method added", "5 sources imported"].map((line, i) => (
                <p key={line} className="trace-line flex items-center gap-2 text-xs text-white/70" style={{ animationDelay: `${i * 0.8}s` }}>
                  <span className="size-2 rounded-full bg-primary-400" />
                  {line}
                </p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function Profiles() {
  return (
    <section className="bg-white py-24 dark:bg-dark-primary">
      <div className="mx-auto max-w-[900px] px-5">
        <SectionTitle title="Built for people who do research" subtitle="Four profiles, one shared need: answers you can rely on." />
        <div className="mt-12 grid gap-5 md:grid-cols-2">
          {PROFILES.map(([initials, role, need, text], i) => (
            <div
              key={role}
              data-reveal
              style={{ transitionDelay: `${(i % 2) * 90}ms` }}
              className="rounded-[20px] border border-gray-200 bg-gray-50 p-6 transition hover:border-primary-200 hover:bg-white dark:border-white/10 dark:bg-white/[0.03]"
            >
              <div className="flex items-center gap-3">
                <span
                  className="inline-flex size-11 items-center justify-center rounded-full bg-primary-100 text-sm font-bold text-primary-600 dark:bg-primary-500/20 dark:text-primary-300"
                  aria-hidden="true"
                >
                  {initials}
                </span>
                <div>
                  <p className="text-sm font-semibold text-gray-800 dark:text-white/90">{role}</p>
                  <p className="text-xs text-primary-500">{need}</p>
                </div>
              </div>
              <p className="mt-4 text-sm leading-relaxed text-gray-600 dark:text-gray-400">{text}</p>
            </div>
          ))}
        </div>
        <p className="mt-6 text-center text-xs text-gray-400">Illustrative profiles</p>
      </div>
    </section>
  );
}

export function Faq() {
  return (
    <section id="faq" className="bg-white py-24 dark:bg-dark-primary">
      <div className="mx-auto max-w-[720px] px-5">
        <SectionTitle title="Frequently asked questions" subtitle="Everything you need to know before importing your first source." />
        <div className="mt-10 space-y-3">
          {FAQ.map(([question, answer], i) => (
            <details
              key={question}
              data-reveal
              style={{ transitionDelay: `${i * 50}ms` }}
              open={i === 0}
              className="faq group rounded-2xl border border-gray-200 bg-white px-5 transition open:border-primary-300 open:bg-primary-50/40 dark:border-white/10 dark:bg-dark-secondary dark:open:border-primary-500/40 dark:open:bg-primary-500/5"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-4 text-sm font-semibold text-gray-800 dark:text-white/90">
                {question}
                <span className="text-gray-400 transition group-open:rotate-180 group-open:text-primary-500">
                  <Icon name="chevronDown" className="size-4" />
                </span>
              </summary>
              <p className="faq-body pb-5 text-sm leading-relaxed text-gray-600 dark:text-gray-300">{answer}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

export function Footer() {
  const product: [string, string][] = [
    ["/assistant", "Research assistant"],
    ["/sources", "Sources"],
    ["/research-twin", "Research Twin"],
    ["/knowledge-graph", "Knowledge Graph"],
  ];
  const link = "text-gray-500 hover:text-primary-600 dark:text-gray-400";
  return (
    <footer id="contact" className="scroll-mt-24 border-t border-gray-100 bg-white pt-14 dark:border-gray-800 dark:bg-dark-primary">
      <div className="mx-auto grid max-w-[1100px] gap-10 px-5 md:grid-cols-[1.7fr_1fr_1fr_1fr]">
        <div>
          <LandingLogo />
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-gray-500 dark:text-gray-400">
            Centralize your sources, get evidence-backed answers, move your research forward.
          </p>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-800 dark:text-white/90">Product</h3>
          <ul className="mt-4 space-y-3 text-sm">
            {product.map(([href, label]) => (
              <li key={href}>
                <Link href={href} className={link}>
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-800 dark:text-white/90">Platform</h3>
          <ul className="mt-4 space-y-3 text-sm">
            <li>
              <a href="#pricing" className={link}>
                Pricing
              </a>
            </li>
            <li>
              <Link href="/signup" className={link}>
                Create an account
              </Link>
            </li>
            <li>
              <Link href="/signin" className={link}>
                Sign in
              </Link>
            </li>
          </ul>
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-800 dark:text-white/90">Resources</h3>
          <ul className="mt-4 space-y-3 text-sm">
            <li>
              <a href="mailto:Kawther.JGUIRIM@esprim.tn" className={link}>
                Contact
              </a>
            </li>
            <li>
              <a href="#faq" className={link}>
                Privacy
              </a>
            </li>
          </ul>
        </div>
      </div>
      <div className="mt-14 border-t border-gray-100 py-6 text-center text-xs text-gray-400 dark:border-gray-800">
        © 2026 ResearchMind AI — Integrated project 5DS2, ESPRIM · DeepMinds team
      </div>
    </footer>
  );
}
