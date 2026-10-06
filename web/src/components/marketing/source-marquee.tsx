/** CSS-only marquee: no JS needed for the scroll, pause-on-hover or the reduced-motion
 *  fallback, so this stays a server component.
 *
 *  Seamless loop: the set is rendered twice and the track animates to translateX(-50%). For
 *  that to land exactly on the second copy (no jump), spacing must be uniform across the seam –
 *  so each item carries its OWN horizontal margin instead of a flex `gap`. A flex gap is omitted
 *  between the two copies, which left the old version short by half a gap every cycle. */
// Each source's own domain, used only to fetch its logo. Google's favicon service needs no API
// key and returns a generic icon on a miss (never a 404). Logo-only: the name lives in
// alt/title for screen readers and hover. No tile behind the logo – the marks sit directly on
// the section so there is no white box on the dark theme.
const sources = [
  { name: "OpenStreetMap", domain: "openstreetmap.org" },
  { name: "Overture Maps", domain: "overturemaps.org" },
  { name: "PPRA tenders", domain: "ppra.org.pk" },
  { name: "KCCI directory", domain: "kcci.com.pk" },
  { name: "GDELT news", domain: "gdeltproject.org" },
  { name: "Greenhouse", domain: "greenhouse.io" },
  { name: "Lever", domain: "lever.co" },
  { name: "GitHub", domain: "github.com" },
]

const favicon = (domain: string) => `https://www.google.com/s2/favicons?domain=${domain}&sz=128`

export function SourceMarquee() {
  return (
    <section id="sources" className="border-y bg-muted/30 py-12">
      <p className="mx-auto max-w-6xl px-4 text-center text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground sm:px-6">
        Built on following sources
      </p>
      <div className="group relative mt-8 overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_6%,black_94%,transparent)]">
        <div className="flex w-max animate-marquee items-center group-hover:[animation-play-state:paused] motion-reduce:animate-none">
          {[...sources, ...sources].map((s, i) => (
            <span
              key={`${s.name}-${i}`}
              title={s.name}
              aria-label={s.name}
              className="mx-4 flex shrink-0 items-center justify-center sm:mx-6"
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- tiny external favicon, not a Next-optimised asset */}
              <img
                src={favicon(s.domain)}
                alt={s.name}
                width={40}
                height={40}
                loading="lazy"
                className="size-10 rounded-xl object-contain opacity-90 transition-all duration-200 hover:scale-110 hover:opacity-100"
              />
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}
