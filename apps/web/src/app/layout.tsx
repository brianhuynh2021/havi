import type { Metadata } from "next";
import { Inter, Merriweather } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-body",
  subsets: ["latin", "vietnamese"],
});

const merriweather = Merriweather({
  variable: "--font-display",
  subsets: ["latin", "vietnamese"],
  weight: ["700", "900"],
});

export const metadata: Metadata = {
  title: "Havi",
  description: "AI marketing dashboard for small businesses",
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
      <body>{children}</body>
    </html>
  );
}
