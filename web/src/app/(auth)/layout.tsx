import Link from "next/link";
import { QualifyrMark } from "@/components/qualifyr-mark";

/** Split-screen auth chrome: a fixed-dark brand panel on the left, form on the right.
 *
 * The panel is a fixed dark surface (not bg-brand, which inverts to white in dark mode) so
 * the designed illustration - a funnel taking scored lead cards from "noise in" to
 * "qualified intent out" - reads correctly in both themes. It carries the whole message, so
 * only the logo and the free-to-start line overlay it. Top/bottom gradients keep those
 * legible over the artwork. The panel collapses below `lg`: on a phone it would push the
 * form, the only thing anyone came here for, below the fold.
 */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <aside className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-[#050505] p-12 text-white lg:flex">
        {/* Designed illustration, fading in then drifting almost imperceptibly. */}
        <div aria-hidden className="qf-fade pointer-events-none absolute inset-0">
          <div className="qf-kenburns h-full w-full bg-[url('/brand/auth-panel.svg')] bg-cover bg-center" />
        </div>
        {/* Keep the logo and footer legible over the artwork. */}
        <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-[#050505] to-transparent" />
        <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-[#050505] to-transparent" />

        <Link href="/" className="relative z-10 flex items-center gap-2 font-semibold">
          <span className="flex size-8 items-center justify-center rounded-lg bg-white/10">
            <QualifyrMark className="size-5" />
          </span>
          Qualifyr
        </Link>

        <p className="relative z-10 text-sm text-white/60">
          Free &ndash; no credit card required.
        </p>
      </aside>

      <div className="flex w-full flex-col justify-center px-6 py-12 lg:w-1/2 lg:px-16">
        <div className="mx-auto w-full max-w-sm">{children}</div>
      </div>
    </div>
  );
}
