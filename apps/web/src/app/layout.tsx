import type { Metadata, Viewport } from "next";
import { Inter, Merriweather } from "next/font/google";
import { SessionProvider } from "@/lib/auth/session";
import { LanguageProvider } from "@/lib/i18n/language-context";
import { PwaRegistrar } from "@/components/pwa/pwa-registrar";
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

export const viewport: Viewport = {
  themeColor: "#4F46E5",
  width: "device-width",
  initialScale: 1,
};


export const metadata: Metadata = {
  title: "Havi — Trợ lý Marketing AI Đa Kênh",
  description: "Hệ thống tự động hóa marketing, bắt trend video ngắn và chăm sóc khách hàng tự động",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Havi",
  },
  icons: {
    icon: "/icon-192.png",
    shortcut: "/icon-192.png",
    apple: "/apple-touch-icon.png",
  },
  other: {
    "tiktok-developers-site-verification": "wE8XEvdVAuCMy5jdJv5mfMYn8aPOidGP",
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
        <PwaRegistrar />
      </body>
    </html>
  );
}

