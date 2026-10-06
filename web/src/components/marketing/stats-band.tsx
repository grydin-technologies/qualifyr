import { ListChecks, ShieldCheck, Ban } from "lucide-react"

const stats = [
  { icon: ListChecks, value: "5", label: "Scored dimensions, every point explained" },
  { icon: ShieldCheck, value: "100%", label: "Outreach drafts reviewed before they send" },
  { icon: Ban, value: "0", label: "Leads sent without a human approving them" },
]

/** A proof band, not a features section - four hard numbers up top before any copy has to
 *  do the convincing. Matches the density of the reference's stat band, adapted to what is
 *  actually true about a buyer-only lead engine rather than a pricing-intelligence tool. */
export function StatsBand() {
  return (
    <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
      <div className="mx-auto grid max-w-4xl grid-cols-1 gap-8 sm:grid-cols-3">
        {stats.map((s) => (
          <div
            key={s.label}
            className="flex flex-col items-center text-center sm:items-start sm:text-left"
          >
            <s.icon className="size-6 text-brand" />
            <p className="mt-3 font-heading text-4xl font-semibold tracking-tight">
              {s.value}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">{s.label}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
