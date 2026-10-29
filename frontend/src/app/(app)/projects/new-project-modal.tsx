"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { FormError } from "@/components/auth-panel";
import { btnPrimary, btnSecondary } from "@/components/ui";
import type { ProjectInput } from "@/lib/api";

const FIELDS: [keyof Fields, string, string, boolean][] = [
  ["title", "Title", "e.g. Early detection of diabetic retinopathy", false],
  ["problem", "Problem statement", "What problem does your research address?", true],
  ["question", "Research question", "State the question that guides the project", true],
  ["objectives", "Objectives", "One objective per line", true],
  ["hypotheses", "Hypotheses", "One hypothesis per line", true],
];

type Fields = { title: string; problem: string; question: string; objectives: string; hypotheses: string };

const fieldCls =
  "w-full border border-gray-300 bg-transparent text-sm text-gray-800 shadow-theme-xs placeholder:text-gray-400 focus:border-primary-300 focus:outline-0 focus:ring-3 focus:ring-primary-300/20 dark:border-gray-700 dark:text-white/90 dark:placeholder:text-white/30";

const lines = (s: string) => s.split("\n").map((l) => l.trim()).filter(Boolean);

export function NewProjectModal({ onClose, onCreate }: { onClose: () => void; onCreate: (body: ProjectInput) => Promise<void> }) {
  const [values, setValues] = useState<Fields>({ title: "", problem: "", question: "", objectives: "", hypotheses: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    titleRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await onCreate({
        title: values.title.trim(),
        problem: values.problem.trim(),
        research_question: values.question.trim(),
        objectives: lines(values.objectives),
        hypotheses: lines(values.hypotheses),
      });
    } catch (err) {
      setError((err as Error).message);
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[60] overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="np-title">
      <div onClick={onClose} className="fixed inset-0 bg-gray-800/70 backdrop-blur-sm" />
      <div className="relative flex min-h-full items-center justify-center p-4">
        <form onSubmit={submit} className="relative w-full max-w-[560px] rounded-3xl bg-white p-6 shadow-theme-lg dark:bg-dark-secondary sm:p-8">
          <h2 id="np-title" className="text-xl font-semibold text-gray-800 dark:text-white/90">
            New project
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            This information initializes your Research Twin. You can edit it later.
          </p>
          <div className="mt-6 space-y-4">
            {error && <FormError message={error} />}
            {FIELDS.map(([name, label, placeholder, multiline]) => (
              <div key={name}>
                <label htmlFor={`f-${name}`} className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {label}
                </label>
                {multiline ? (
                  <textarea
                    id={`f-${name}`}
                    rows={2}
                    placeholder={placeholder}
                    value={values[name]}
                    onChange={(e) => setValues((v) => ({ ...v, [name]: e.target.value }))}
                    className={`${fieldCls} resize-none rounded-2xl px-4 py-2.5`}
                  />
                ) : (
                  <input
                    ref={titleRef}
                    id={`f-${name}`}
                    required
                    maxLength={300}
                    placeholder={placeholder}
                    value={values[name]}
                    onChange={(e) => setValues((v) => ({ ...v, [name]: e.target.value }))}
                    className={`${fieldCls} h-12 rounded-full px-5`}
                  />
                )}
              </div>
            ))}
          </div>
          <div className="mt-8 flex justify-end gap-3">
            <button type="button" onClick={onClose} className={btnSecondary}>
              Cancel
            </button>
            <button type="submit" disabled={saving} className={btnPrimary}>
              {saving ? "Creating…" : "Create project"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
