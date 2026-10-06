import Link from "next/link"
import { Mail } from "lucide-react"
import { QualifyrMark } from "@/components/qualifyr-mark"

const columns = [
  {
    title: "Product",
    links: [
      { label: "Features", href: "#features" },
      { label: "How it works", href: "#how-it-works" },
      { label: "Sources", href: "#sources" },
      { label: "FAQ", href: "#faq" },
    ],
  },
  {
    title: "Account",
    links: [
      { label: "Sign in", href: "/sign-in" },
      { label: "Get started free", href: "/sign-up" },
    ],
  },
]

const SUPPORT_EMAIL = "hello@grydin.co";

export function SiteFooter() {
  return (
    <footer className="relative overflow-hidden border-t bg-card">
      {/* faint glow bridging from the CTA above, monochrome */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 -top-20 h-40 opacity-50 blur-3xl"
        style={{ background: "radial-gradient(50% 100% at 50% 0%, var(--brand-muted), transparent 70%)" }}
      />

      <div className="relative mx-auto grid max-w-6xl gap-10 px-4 py-16 sm:px-6 md:grid-cols-[1.6fr_1fr_1fr_1.1fr]">
        <div className="max-w-sm">
          <Link href="/" className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            <span className="flex size-9 items-center justify-center rounded-xl bg-brand shadow-sm">
              <QualifyrMark className="size-5 text-brand-foreground" />
            </span>
            Qualifyr
          </Link>
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
            Describe what you sell and Qualifyr finds the companies that actually need it –
            from various sources, with the reasoning behind every match.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <span className="inline-flex items-center rounded-full border border-border/70 bg-background/50 px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
              Pakistan-focused
            </span>
            <span className="inline-flex items-center rounded-full border border-border/70 bg-background/50 px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
              Qualified leads only
            </span>
          </div>
        </div>

        {columns.map((col) => (
          <div key={col.title}>
            <h2 className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
              {col.title}
            </h2>
            <ul className="mt-4 flex flex-col gap-2.5">
              {col.links.map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}

        <div>
          <h2 className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Get in touch
          </h2>
          <p className="mt-4 text-sm text-muted-foreground">
            Questions or feedback? We usually reply within a day.
          </p>
          <a
            href={`mailto:${SUPPORT_EMAIL}?subject=Qualifyr%20question`}
            className="mt-3 inline-flex items-center gap-2 rounded-lg border border-border/70 bg-background/50 px-3 py-2 text-sm font-medium transition-colors hover:border-border hover:bg-background"
          >
            <Mail className="size-4 text-muted-foreground" />
            {SUPPORT_EMAIL}
          </a>
        </div>
      </div>

      <div className="relative border-t">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 py-6 text-sm text-muted-foreground sm:flex-row sm:px-6">
          <span>© {new Date().getFullYear()} GrydIn Qualifyr. All rights reserved.</span>
          {/* <span className="text-xs">Built on free, public data sources.</span> */}
        </div>
      </div>
    </footer>
  )
}
