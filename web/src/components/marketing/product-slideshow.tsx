"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

/** Real HTML/CSS mini-mockups of the actual dashboard views, not screenshots - so this
 *  stays sharp at any zoom, themes with dark mode automatically, and never drifts out of
 *  sync with the real UI the way a screenshot would the moment a table column changes.
 *
 *  Presented as a guided demo: a synthetic cursor walks the tabs, clicks each one, and the
 *  view settles in - the deliberate pacing (read, move, click, read) reads as a product
 *  tour rather than a slideshow. `route` is the real app path, so the address bar matches
 *  the routes in app/(app)/ instead of an invented "/overview". */

function initials(name: string) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase()
}

function Avatar({ name }: { name: string }) {
  return (
    <span className="grid size-8 shrink-0 place-items-center rounded-full bg-brand-muted text-[11px] font-semibold text-brand">
      {initials(name)}
    </span>
  )
}

// High score = confident buyer. Colour the badge by tier so the table reads at a glance.
function scoreTone(s: number) {
  if (s >= 80) return "bg-emerald-500/15 text-emerald-500"
  if (s >= 70) return "bg-brand-muted text-brand"
  return "bg-amber-500/15 text-amber-600 dark:text-amber-400"
}

const frames = [
  {
    label: "Overview",
    route: "dashboard",
    render: () => (
      <div className="flex h-full flex-col gap-3 p-6">
        <div className="grid grid-cols-3 gap-3">
          {[
            { t: "Qualified buyers", v: "42", d: "+12%" },
            { t: "Emails sent", v: "118", d: "+8%" },
            { t: "Replies", v: "9", d: "+3" },
          ].map((s, i) => (
            <div
              key={s.t}
              className="qf-rise rounded-xl border border-border/60 bg-muted/60 p-4"
              style={{ animationDelay: `${i * 70}ms` }}
            >
              <p className="text-[11px] text-muted-foreground">{s.t}</p>
              <div className="mt-1.5 flex items-end justify-between">
                <p className="text-3xl font-semibold leading-none tracking-tight">{s.v}</p>
                <span className="mb-0.5 rounded-full bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-medium text-emerald-500">
                  ▲ {s.d}
                </span>
              </div>
            </div>
          ))}
        </div>
        <div
          className="qf-rise flex flex-1 flex-col rounded-xl border border-border/60 bg-muted/60 p-4"
          style={{ animationDelay: "220ms" }}
        >
          <div className="mb-3 flex items-center justify-between">
            <p className="text-[11px] font-medium">Qualified buyers · last 7 days</p>
            <p className="text-[10px] text-muted-foreground">Mon – Sun</p>
          </div>
          <div className="flex flex-1 items-end gap-2">
            {[30, 55, 40, 70, 92, 60, 45].map((h, i) => (
              <div key={i} className="flex flex-1 flex-col items-center gap-1.5">
                <div
                  className={cn(
                    "w-full rounded-md bg-gradient-to-t transition-colors",
                    h === 92 ? "from-brand to-brand/70" : "from-brand/45 to-brand/20"
                  )}
                  style={{ height: `${h}%` }}
                />
                <span className="text-[9px] text-muted-foreground">{["M", "T", "W", "T", "F", "S", "S"][i]}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    ),
  },
  {
    label: "Campaigns",
    route: "campaigns",
    render: () => (
      <div className="flex h-full flex-col justify-center gap-3 p-6">
        {[
          { name: "Retail & ecommerce", sub: "Islamabad · shops, brands", status: "Running", n: 96 },
          { name: "Live PPRA tenders", sub: "Inventory & supply", status: "Running", n: 24 },
          { name: "Textile & garment", sub: "Karachi · manufacturers", status: "Paused", n: 58 },
        ].map((c, i) => (
          <div
            key={c.name}
            className="qf-rise flex items-center gap-3 rounded-xl border border-border/60 bg-muted/60 px-4 py-3.5"
            style={{ animationDelay: `${i * 90}ms` }}
          >
            <span className={cn("size-2.5 shrink-0 rounded-full", c.status === "Running" ? "bg-emerald-500" : "bg-muted-foreground/40")} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{c.name}</p>
              <p className="truncate text-[11px] text-muted-foreground">{c.sub}</p>
            </div>
            <span className="shrink-0 text-xs text-muted-foreground">{c.n} leads</span>
            <span
              className={cn(
                "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium",
                c.status === "Running" ? "bg-emerald-500/15 text-emerald-500" : "bg-secondary text-muted-foreground"
              )}
            >
              {c.status}
            </span>
          </div>
        ))}
      </div>
    ),
  },
  {
    label: "Leads",
    route: "leads",
    render: () => (
      <div className="flex h-full flex-col justify-center p-6">
        <div className="overflow-hidden rounded-xl border border-border/60">
          <div className="grid grid-cols-[1fr_auto_auto] gap-4 border-b border-border/60 bg-muted/40 px-4 py-2.5 text-[11px] font-medium text-muted-foreground">
            <span>Company</span><span className="text-center">Score</span><span>Type</span>
          </div>
          {[
            { n: "RBS Interiors", city: "Lahore", s: 84 },
            { n: "Ittefaq Electronics", city: "Karachi", s: 77 },
            { n: "Al-Fateh Traders", city: "Faisalabad", s: 71 },
          ].map((l, i) => (
            <div
              key={l.n}
              className="qf-rise grid grid-cols-[1fr_auto_auto] items-center gap-4 border-b border-border/40 bg-muted/20 px-4 py-3 last:border-0"
              style={{ animationDelay: `${i * 90}ms` }}
            >
              <div className="flex min-w-0 items-center gap-3">
                <Avatar name={l.n} />
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{l.n}</p>
                  <p className="truncate text-[11px] text-muted-foreground">{l.city}, Pakistan</p>
                </div>
              </div>
              <span className={cn("justify-self-center rounded-full px-2 py-0.5 text-xs font-semibold", scoreTone(l.s))}>{l.s}</span>
              <span className="rounded-full border border-border/60 px-2 py-0.5 text-[10px] font-medium text-muted-foreground">BUYER</span>
            </div>
          ))}
        </div>
      </div>
    ),
  },
  {
    label: "Outreach",
    route: "outreach",
    render: () => (
      <div className="flex h-full flex-col justify-center gap-3 p-6">
        <div className="flex items-center justify-between rounded-xl border border-border/60 bg-muted/60 px-4 py-3">
          <div className="flex items-center gap-2.5">
            <span className="grid size-6 place-items-center rounded-full bg-brand text-[11px] font-bold text-brand-foreground">3</span>
            <span className="text-sm font-medium">drafts awaiting approval</span>
          </div>
          <span className="rounded-full bg-brand px-3 py-1 text-[11px] font-medium text-brand-foreground">Review</span>
        </div>
        {[
          { to: "Ahmed Raza", co: "RBS Interiors", body: "noticed RBS Interiors is hiring for retail ops – quick idea on sourcing…" },
          { to: "Sana Malik", co: "Ittefaq Electronics", body: "saw Ittefaq just opened a second Lahore branch – congrats. One thought…" },
        ].map((d, i) => (
          <div
            key={d.to}
            className="qf-rise flex items-start gap-3 rounded-xl border border-border/60 bg-muted/30 px-4 py-3"
            style={{ animationDelay: `${(i + 1) * 90}ms` }}
          >
            <Avatar name={d.to} />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium">
                {d.to} <span className="font-normal text-muted-foreground">· {d.co}</span>
              </p>
              <p className="mt-0.5 truncate text-[11px] text-muted-foreground">Hi {d.to.split(" ")[0]}, {d.body}</p>
            </div>
            <span className="mt-0.5 shrink-0 rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-600 dark:text-amber-400">
              Draft
            </span>
          </div>
        ))}
      </div>
    ),
  },
]

// Brisk but still readable: read the view, then the cursor travels and clicks.
const DWELL_MS = 2600      // time to read the current view before moving on
const TRAVEL_MS = 760      // cursor glide to the next tab
const CLICK_MS = 240       // press-and-release before the view switches

export function ProductSlideshow() {
  const [active, setActive] = React.useState(0)
  const [paused, setPaused] = React.useState(false)
  const [clicking, setClicking] = React.useState(false)
  const [cursor, setCursor] = React.useState<{ x: number; y: number } | null>(null)
  const reducedMotion = useReducedMotion()

  const frameRef = React.useRef<HTMLDivElement>(null)
  const tabRefs = React.useRef<(HTMLButtonElement | null)[]>([])
  // Mirrors `active` for the timeout-driven tour to read without re-subscribing. Synced in
  // a layout effect (not during render): it runs before the driver's timers can fire.
  const activeRef = React.useRef(0)
  React.useLayoutEffect(() => { activeRef.current = active }, [active])

  // Centre of a tab, in coordinates local to the demo frame.
  const tabCenter = React.useCallback((i: number) => {
    const tab = tabRefs.current[i]
    const frame = frameRef.current
    if (!tab || !frame) return null
    const t = tab.getBoundingClientRect()
    const f = frame.getBoundingClientRect()
    return { x: t.left - f.left + t.width / 2, y: t.top - f.top + t.height / 2 }
  }, [])

  // Park the cursor on the active tab once laid out, and keep it there on resize.
  React.useLayoutEffect(() => {
    if (reducedMotion) return
    const place = () => {
      const c = tabCenter(activeRef.current)
      if (c) setCursor(c)
    }
    place()
    window.addEventListener("resize", place)
    return () => window.removeEventListener("resize", place)
  }, [tabCenter, reducedMotion])

  // The guided-tour driver: dwell → glide → click → switch → repeat.
  React.useEffect(() => {
    if (paused || reducedMotion) return
    const timers: ReturnType<typeof setTimeout>[] = []
    const after = (ms: number, fn: () => void) => timers.push(setTimeout(fn, ms))

    const step = () => {
      after(DWELL_MS, () => {
        const next = (activeRef.current + 1) % frames.length
        const c = tabCenter(next)
        if (c) setCursor(c)                         // CSS transition glides the cursor
        after(TRAVEL_MS, () => {
          setClicking(true)
          after(CLICK_MS, () => {
            setClicking(false)
            setActive(next)                          // content crossfades/rises in
            step()
          })
        })
      })
    }
    step()
    return () => timers.forEach(clearTimeout)
  }, [paused, reducedMotion, tabCenter])

  const jumpTo = (i: number) => {
    const c = tabCenter(i)
    if (c) setCursor(c)
    setActive(i)
  }

  return (
    <div
      className="relative mx-auto max-w-4xl"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      {/* Soft brand glow so the pane reads as a lit surface, not a flat card. */}
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-x-10 -top-12 bottom-0 -z-10 opacity-70 blur-3xl"
        style={{ background: "radial-gradient(55% 55% at 50% 0%, var(--brand-muted), transparent 70%)" }}
      />

      {/* Browser-chrome frame */}
      <div ref={frameRef} className="relative overflow-hidden rounded-2xl border border-border/60 bg-card shadow-2xl shadow-black/25 ring-1 ring-black/5">
        <div className="flex items-center gap-1.5 border-b border-border/60 bg-muted/50 px-4 py-3">
          <span className="size-3 rounded-full bg-red-400/70" />
          <span className="size-3 rounded-full bg-amber-400/70" />
          <span className="size-3 rounded-full bg-green-400/70" />
          <span className="ml-3 flex flex-1 items-center gap-1.5 truncate rounded-md bg-background px-3 py-1.5 text-[11px] text-muted-foreground">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" className="shrink-0 opacity-70">
              <rect x="5" y="11" width="14" height="9" rx="2" className="fill-current" />
              <path d="M8 11V8a4 4 0 0 1 8 0v3" stroke="currentColor" strokeWidth="2" />
            </svg>
            qualifyr.grydin.co/{frames[active].route}
          </span>
        </div>

        {/* Tab bar - the cursor's targets, and real manual controls. */}
        <div role="tablist" aria-label="Product views" className="flex gap-1 border-b border-border/60 bg-muted/30 px-2.5 py-2">
          {frames.map((f, i) => (
            <button
              key={f.label}
              ref={(el) => { tabRefs.current[i] = el }}
              type="button"
              role="tab"
              aria-selected={i === active}
              onClick={() => jumpTo(i)}
              className={cn(
                "rounded-lg px-3.5 py-2 text-xs font-medium transition-colors",
                i === active ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Content - fixed height so the pane never jumps as views change. */}
        <div className="h-[300px] sm:h-[340px]">
          <div key={active} className="h-full">
            {frames[active].render()}
          </div>
        </div>

        {/* Synthetic cursor. Purely decorative, so hidden from assistive tech and under
            reduced-motion. Travels via a transform transition; a ring pulses on click. */}
        {cursor && !reducedMotion && (
          <div
            aria-hidden
            className="pointer-events-none absolute left-0 top-0 z-20"
            style={{
              transform: `translate(${cursor.x}px, ${cursor.y}px)`,
              transition: `transform ${TRAVEL_MS}ms cubic-bezier(0.5, 0, 0.2, 1)`,
            }}
          >
            <div className="relative -translate-x-[4px] -translate-y-[3px]">
              <span
                className={cn(
                  "absolute left-0 top-0 size-9 -translate-x-1/2 -translate-y-1/2 rounded-full bg-brand/25 transition-all duration-200",
                  clicking ? "scale-100 opacity-100" : "scale-0 opacity-0"
                )}
              />
              <span
                className={cn(
                  "absolute left-0 top-0 size-9 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-brand/60 transition-all duration-300",
                  clicking ? "scale-125 opacity-0" : "scale-50 opacity-0"
                )}
              />
              <svg width="26" height="26" viewBox="0 0 20 20" className={cn("drop-shadow-lg transition-transform duration-150", clicking && "scale-90")}>
                <path d="M3 2l5.5 13 2-5 5-2L3 2z" className="fill-foreground stroke-background" strokeWidth="1.25" strokeLinejoin="round" />
              </svg>
            </div>
          </div>
        )}
      </div>

      {/* Progress dots - reflect the tour, and stay clickable. */}
      <div className="mt-6 flex items-center justify-center gap-2">
        {frames.map((f, i) => (
          <button
            key={f.label}
            type="button"
            onClick={() => jumpTo(i)}
            aria-label={`Show ${f.label}`}
            aria-current={i === active}
            className={cn(
              "h-2 rounded-full transition-all",
              i === active ? "w-7 bg-brand" : "w-2 bg-muted-foreground/30 hover:bg-muted-foreground/50"
            )}
          />
        ))}
      </div>
    </div>
  )
}

function useReducedMotion() {
  const [reduced, setReduced] = React.useState(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  )
  React.useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)")
    const onChange = () => setReduced(mq.matches)
    mq.addEventListener("change", onChange)
    return () => mq.removeEventListener("change", onChange)
  }, [])
  return reduced
}
