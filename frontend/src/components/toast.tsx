"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { Icon } from "./icons";

type Toast = { id: number; message: string; ok: boolean };
const ToastContext = createContext<(message: string, ok?: boolean) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((message: string, ok = true) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message, ok }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 2600);
  }, []);

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-5 right-5 z-[100] flex flex-col items-end gap-2" aria-live="polite">
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className="toast-in flex items-center gap-2 rounded-2xl border border-gray-100 bg-white px-4 py-3 text-sm text-gray-800 shadow-theme-lg dark:border-white/10 dark:bg-dark-secondary dark:text-white/90"
          >
            {t.ok ? (
              <span className="text-success-600">
                <Icon name="check" className="size-4" />
              </span>
            ) : (
              <span className="text-error-500">
                <Icon name="alert" className="size-4" />
              </span>
            )}
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
