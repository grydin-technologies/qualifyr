function StatusBar() {
  return (
    <div className="flex items-center justify-between px-4 pt-2.5 text-[7px] font-semibold text-foreground/70">
      <span>9:41</span>
      <span className="flex items-center gap-1">
        {/* signal */}
        <svg width="11" height="7" viewBox="0 0 12 8" className="fill-foreground/70">
          <rect x="0" y="5" width="2" height="3" rx="0.5" />
          <rect x="3.3" y="3" width="2" height="5" rx="0.5" />
          <rect x="6.6" y="1.5" width="2" height="6.5" rx="0.5" />
          <rect x="9.9" y="0" width="2" height="8" rx="0.5" />
        </svg>
        {/* battery */}
        <svg width="15" height="8" viewBox="0 0 16 8" className="fill-none">
          <rect x="0.5" y="0.5" width="12.5" height="7" rx="1.6" className="stroke-foreground/40" strokeWidth="1" />
          <rect x="2" y="2" width="8" height="4" rx="0.6" className="fill-foreground/70" />
          <rect x="14.2" y="2.6" width="1.4" height="2.8" rx="0.6" className="fill-foreground/40" />
        </svg>
      </span>
    </div>
  )
}

function PhoneFrame({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative mx-auto w-44">
      {/* Side buttons - the small tells that read "phone" at a glance. */}
      <span className="absolute -left-[2px] top-20 h-7 w-[3px] rounded-l bg-foreground/25" />
      <span className="absolute -left-[2px] top-32 h-11 w-[3px] rounded-l bg-foreground/25" />
      <span className="absolute -right-[2px] top-28 h-14 w-[3px] rounded-r bg-foreground/25" />

      {/* Metallic bezel */}
      <div className="rounded-[2.6rem] bg-gradient-to-b from-foreground/70 to-foreground/90 p-[5px] shadow-2xl shadow-black/40 ring-1 ring-black/20">
        <div className="relative flex aspect-[9/19.5] flex-col overflow-hidden rounded-[2.2rem] bg-background">
          {/* Dynamic island */}
          <div className="absolute left-1/2 top-2 z-10 h-[18px] w-16 -translate-x-1/2 rounded-full bg-foreground/90" />
          <StatusBar />
          <div className="flex flex-1 flex-col justify-center px-1.5 pb-6">{children}</div>
          {/* Home indicator */}
          <div className="absolute bottom-2 left-1/2 h-1 w-12 -translate-x-1/2 rounded-full bg-foreground/35" />
        </div>
      </div>
    </div>
  )
}

const panels = [
  {
    title: "Approve outreach on your phone",
    description: "Review a drafted email and approve it the moment it's ready, wherever you are.",
    frame: (
      <div className="flex flex-col gap-2 px-2">
        <div className="rounded-lg bg-muted px-2.5 py-2 text-[9px] leading-relaxed text-muted-foreground">
          Hi Sana, saw Ittefaq just opened a second Lahore branch – congrats…
        </div>
        <button className="flex items-center justify-center rounded-lg bg-brand px-2.5 py-2 text-[9px] font-medium text-brand-foreground">
          Approve &amp; send
        </button>
      </div>
    ),
  },
  {
    title: "The full lead dashboard",
    description: "Score bands, top buyers and every campaign's status in one place.",
    frame: (
      <div className="flex flex-col gap-2 px-2">
        {[
          { t: "Qualified", v: 42 },
          { t: "Sent", v: 118 },
          { t: "Replies", v: 9 },
        ].map((s) => (
          <div key={s.t} className="flex items-center justify-between rounded-lg bg-muted px-2.5 py-2">
            <span className="text-[9px] text-muted-foreground">{s.t}</span>
            <span className="text-xs font-semibold">{s.v}</span>
          </div>
        ))}
      </div>
    ),
  },
  {
    title: "Every score, explained",
    description: "See exactly why a lead scored what it did, down to the individual reason.",
    frame: (
      <div className="flex flex-col gap-2 px-2">
        <div className="flex items-center justify-between rounded-lg bg-muted px-2.5 py-2">
          <span className="text-[9px] font-medium">RBS Interiors</span>
          <span className="rounded-full bg-emerald-500/15 px-1.5 py-0.5 text-[9px] font-semibold text-emerald-500">84</span>
        </div>
        <div className="rounded-lg bg-muted px-2.5 py-2 text-[8px] leading-relaxed text-muted-foreground">
          + in target city · + decision-maker found · + open growth role
        </div>
      </div>
    ),
  },
]

/** Same panel density as the reference's "see it in action" gallery, reframed around a
 *  responsive web app rather than a native mobile app - the caption says so explicitly so
 *  this never reads as app-store marketing. A header illustration (mobile-approval) was
 *  tried and dropped: its "approve on your phone" scene duplicated the first coded phone
 *  panel below almost exactly, so it added repetition rather than richness. */
export function DeviceMockups() {
  return (
    <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6 sm:py-20">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">See it in action</h2>
        <p className="mt-4 text-muted-foreground">
          The same responsive dashboard on your desk or in your pocket &ndash; there is no
          separate mobile app.
        </p>
      </div>

      <div className="mt-14 grid gap-y-10 sm:grid-cols-3">
        {panels.map((p) => (
          <div key={p.title} className="text-center">
            <PhoneFrame>{p.frame}</PhoneFrame>
            <h3 className="mt-7 font-heading text-base font-medium">{p.title}</h3>
            <p className="mx-auto mt-2 max-w-[15rem] text-sm text-muted-foreground">{p.description}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
