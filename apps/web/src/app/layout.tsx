import type { Metadata } from "next";
import { Inter, Merriweather } from "next/font/google";
import { SessionProvider } from "@/lib/auth/session";
import { LanguageProvider } from "@/lib/i18n/language-context";
import "./globals.css";

const inter = Inter({
  variable: "--font-body",
  subsets: ["latin", "vietnamese"],
  fallback: ["system-ui", "-apple-system", "sans-serif"],
  display: "swap",
});

const merriweather = Merriweather({
  variable: "--font-display",
  subsets: ["latin", "vietnamese"],
  weight: ["700", "900"],
  fallback: ["Georgia", "serif"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Havi — Trợ lý Marketing AI",
  description: "Hệ thống tự động hóa marketing dành cho chủ doanh nghiệp",
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="vi"
      className={`${inter.variable} ${merriweather.variable}`}
    >
      <body>
        <SessionProvider>
          <LanguageProvider>{children}</LanguageProvider>
        </SessionProvider>
      </body>
    </html>
  );
}

