import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider, themeScript } from "@/components/theme-provider";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://qualifyr.vercel.app";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Qualifyr – See who actually buys",
    template: "%s · Qualifyr",
  },
  description:
    "Qualifyr discovers companies from free public sources, rejects the agencies and vendors, finds a decision-maker, and scores every lead 0–100 with a reason you can read.",
  openGraph: {
    type: "website",
    siteName: "Qualifyr",
    title: "Qualifyr – See who actually buys",
    description:
      "A buyer-only B2B lead engine for Pakistan and the GCC. Finds companies that buy, rejects the ones that sell, and explains every score.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Qualifyr – See who actually buys",
    description:
      "A buyer-only B2B lead engine for Pakistan and the GCC. Finds companies that buy, rejects the ones that sell, and explains every score.",
  },
};

/** Root layout: fonts, theme, nothing else.
 *
 * Deliberately does NOT render AppShell any more. Each route group brings its own chrome
 * - (marketing) a nav and footer, (auth) a split panel, (app) the dashboard sidebar - so
 * that a public page is not forced to wear the signed-in furniture.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full`} suppressHydrationWarning>
      <head>
        {/* Before first paint: see themeScript's comment. */}
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-full font-sans antialiased">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
