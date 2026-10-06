import Link from "next/link"
import { ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"

/** The brand accent is strict black/white, so a `bg-brand` band flips to a full white slab
 *  in dark mode - jarring against an otherwise black page. Instead this is a dark, elevated
 *  panel that belongs to the page, with the button carrying the accent (same treatment as
 *  the nav CTA). Works in both themes: the panel tracks the surface, the button inverts. */
export function FinalCta() {
  return (
    <section className="px-4 py-20 sm:px-6">
      <div className="relative mx-auto max-w-4xl overflow-hidden rounded-[1.75rem] border border-border/60 bg-card px-6 py-16 text-center shadow-2xl shadow-black/20 sm:py-20">
        {/* dotted grid, faded toward the edges – subtle monochrome texture, no colour */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.35] [mask-image:radial-gradient(70%_70%_at_50%_40%,black,transparent)]"
          style={{
            backgroundImage: "radial-gradient(circle at center, var(--border) 1px, transparent 1px)",
            backgroundSize: "22px 22px",
          }}
        />
        {/* soft glow at the top edge */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 -top-24 h-48 opacity-70 blur-3xl"
          style={{ background: "radial-gradient(50% 60% at 50% 0%, var(--brand-muted), transparent 70%)" }}
        />

        <span className="relative inline-flex items-center rounded-full border border-border/70 bg-background/60 px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground backdrop-blur-sm">
          Get started
        </span>
        <h2 className="relative mt-5 text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
          Stop guessing who to reach out to
        </h2>
        <p className="relative mx-auto mt-4 max-w-lg text-pretty text-muted-foreground">
          Describe what you sell. Qualifyr finds the companies that actually need it – and
          explains every match.
        </p>

        <div className="relative mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button
            size="lg"
            nativeButton={false}
            className="group w-full bg-brand text-brand-foreground hover:bg-brand/90 sm:w-auto"
            render={<Link href="/sign-up" />}
          >
            Get started free
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
          </Button>
          <Button
            size="lg"
            variant="outline"
            nativeButton={false}
            className="w-full border-border/70 bg-background/40 sm:w-auto"
            render={<Link href="#how-it-works" />}
          >
            See how it works
          </Button>
        </div>

        <p className="relative mt-6 text-xs text-muted-foreground">
          Free to start · 3 campaigns · no credit card
        </p>
      </div>
    </section>
  )
}
