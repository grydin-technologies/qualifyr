import Link from "next/link"
import { Button } from "@/components/ui/button"
import { ProductSlideshow } from "@/components/marketing/product-slideshow"

export function Hero() {
  return (
    <section className="relative overflow-hidden pt-20 pb-16 sm:pt-28">
      {/* Ambient dotted/contour texture, slowly drifting. White-on-dark, so it reads in dark
          mode and stays invisibly faint on the light background. */}
      <div
        aria-hidden
        className="qf-drift pointer-events-none absolute inset-0 -z-20 bg-[url('/brand/hero-backdrop.svg')] bg-cover bg-center opacity-70"
      />
      {/* Soft brand glow behind the headline only - never a full-bleed surface. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[480px] bg-[radial-gradient(ellipse_60%_50%_at_50%_0%,var(--brand-muted),transparent)]"
      />

      <div className="mx-auto max-w-6xl px-4 text-center sm:px-6">
        <span className="qf-rise inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
          Buyer-only lead engine for Pakistan &amp; the GCC
        </span>

        <h1 className="qf-rise mx-auto mt-6 max-w-3xl text-5xl font-semibold tracking-tight sm:text-6xl" style={{ animationDelay: "80ms" }}>
          See who actually <span className="text-brand">buys</span>. Not just who exists.
        </h1>

        <p className="qf-rise mx-auto mt-6 max-w-2xl text-lg text-muted-foreground" style={{ animationDelay: "160ms" }}>
          Qualifyr discovers companies from various sources, rejects the agencies and
          vendors, finds a decision-maker, and scores every lead 0&ndash;100 with clear reasoning.
        </p>

        <div className="qf-rise mt-10 flex items-center justify-center gap-3" style={{ animationDelay: "240ms" }}>
          <Button
            size="lg"
            nativeButton={false}
            className="bg-brand text-brand-foreground hover:bg-brand/90"
            render={<Link href="/sign-up" />}
          >
            Get started free
          </Button>
          <Button size="lg" variant="outline" nativeButton={false} render={<Link href="/sign-in" />}>
            Sign in
          </Button>
        </div>

        <p className="qf-rise mt-4 text-xs text-muted-foreground" style={{ animationDelay: "320ms" }}>
          Free to start &ndash; no credit card required.
        </p>
      </div>

      <div className="mx-auto mt-16 max-w-6xl px-4 sm:px-6">
        <ProductSlideshow />
      </div>
    </section>
  )
}
