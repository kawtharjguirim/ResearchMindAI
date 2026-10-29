import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider, themeInitScript } from "@/components/theme";
import { ToastProvider } from "@/components/toast";

export const metadata: Metadata = {
  title: { default: "ResearchMind AI", template: "%s | ResearchMind AI" },
  description: "Your evidence-based scientific research assistant.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="light" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="min-h-screen bg-gray-50 font-sans text-gray-800 antialiased dark:bg-dark-primary">
        <ThemeProvider>
          <ToastProvider>{children}</ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
