import { Illustration } from "@/components/marketing/illustration"

const steps = [
  {
    n: "01",
    title: "Define your campaign",
    description: "Name what you sell, pick a region, set a company cap. No code, no config file to hand-edit.",
  },
  {
    n: "02",
    title: "We discover and qualify",
    description: "Companies are pulled from various sources, classified buyer vs. vendor, and scored with a written reason for every point.",
  },
  {
    n: "03",
    title: "Approve and send",
    description: "Review the queue, approve what looks right, and outreach goes out from your own mailbox – never automatically.",
  },
]

export function HowItWorks() {
  return (
    <section id="how-it-works" className="border-y bg-muted/30 py-16 sm:py-20">
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <p className="text-center text-xs font-medium uppercase tracking-wide text-brand">The process</p>
        <div className="mx-auto mt-3 max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">From campaign to first reply</h2>
          <p className="mt-4 text-muted-foreground">
            No dashboards to configure before you start &ndash; define a campaign and the
            pipeline runs.
          </p>
        </div>

        <Illustration
          src="/brand/process-three-step.png"
          alt="Three people carrying out the define, discover and approve steps"
          width={1672}
          height={941}
          sizes="(min-width: 1024px) 768px, 100vw"
          className="mx-auto mt-10 aspect-[1672/941] w-full max-w-3xl"
        />

        <div className="relative mt-14 grid gap-10 sm:grid-cols-3 sm:gap-6">
          {/* A single line links the three steps, so they read as a flow, not three cards. */}
          <div aria-hidden className="absolute inset-x-0 top-6 hidden h-px bg-border/60 sm:block" />
          {steps.map((s) => (
            <div key={s.n} className="relative flex flex-col items-center px-2 text-center">
              <span className="flex size-12 items-center justify-center rounded-full border border-border bg-card font-heading text-sm font-semibold text-brand shadow-sm">
                {s.n}
              </span>
              <h3 className="mt-5 font-heading text-lg font-medium">{s.title}</h3>
              <p className="mt-2 max-w-xs text-sm text-muted-foreground">{s.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
