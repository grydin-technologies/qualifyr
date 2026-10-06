"use client"

import * as React from "react"
import Link from "next/link"
import {
  Users, ShieldCheck, Send, MessageSquareReply, Target, Gauge,
  MapPin, Layers, Clock, ArrowUpRight, Mail,
} from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"
import { api, type Campaign, type Lead, type Stats } from "@/lib/api"
import { useCampaign } from "@/components/campaign-context"
import { ScoreBadge, StatusBadge, TypeBadge } from "@/components/lead-badges"
import { cn } from "@/lib/utils"

function StatCard({
  title, value, hint, icon: Icon, highlight,
}: { title: string; value: string | number; hint: string; icon: React.ElementType; highlight?: boolean }) {
  return (
    <Card className={cn("transition-shadow hover:shadow-md", highlight && "border-brand/30 bg-brand-muted/40")}>
      <CardContent className="p-5">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-medium text-muted-foreground">{title}</span>
          <span className={cn(
            "flex size-8 shrink-0 items-center justify-center rounded-lg",
            highlight ? "bg-brand text-brand-foreground" : "bg-muted text-muted-foreground",
          )}>
            <Icon className="size-4" />
          </span>
        </div>
        <div className="mt-4 text-3xl font-semibold tracking-tight tabular-nums">{value}</div>
        <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{hint}</p>
      </CardContent>
    </Card>
  )
}

function MetaChip({ icon: Icon, children }: { icon: React.ElementType; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border/70 bg-card px-2.5 py-1 text-xs text-muted-foreground">
      <Icon className="size-3.5 shrink-0" />
      {children}
    </span>
  )
}

function timeAgo(iso?: string | null): string {
  if (!iso) return ""
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return ""
  const s = Math.floor((Date.now() - t) / 1000)
  if (s < 60) return "just now"
  const m = Math.floor(s / 60); if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60); if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24); if (d < 30) return `${d}d ago`
  return new Date(iso).toLocaleDateString()
}

function runDotClass(status?: string): string {
  const s = (status ?? "").toLowerCase()
  if (["completed", "done", "success", "succeeded"].includes(s)) return "bg-green-500"
  if (["running", "dispatched", "pending", "queued"].includes(s)) return "bg-amber-500"
  if (["failed", "error"].includes(s)) return "bg-red-500"
  return "bg-muted-foreground/40"
}

const chartConfig = {
  count: { label: "Leads", theme: { light: "var(--chart-1)", dark: "var(--chart-1)" } },
}

function CampaignMeta({ campaign }: { campaign?: Campaign }) {
  if (!campaign) return null
  const location = [...(campaign.areas ?? []), ...(campaign.cities ?? [])].filter(Boolean)
  const sectors = (campaign.discovery_sectors ?? [])
    .filter((s) => s && s !== "_niche" && s !== "general_retail")
    .map((s) => s.replace(/_/g, " "))
  const run = campaign.last_run
  const runLabel = run ? timeAgo(run.finished_at ?? run.started_at) : null

  return (
    <div className="flex flex-wrap items-center gap-2">
      {location.length > 0 && <MetaChip icon={MapPin}>{location.slice(0, 4).join(", ")}</MetaChip>}
      {sectors.length > 0 && <MetaChip icon={Layers}>{sectors.slice(0, 3).join(" · ")}</MetaChip>}
      <MetaChip icon={Target}>Qualify ≥ {campaign.min_score}</MetaChip>
      <MetaChip icon={Clock}>
        <span className={cn("size-1.5 rounded-full", runDotClass(run?.status))} />
        {runLabel ? `Last run ${runLabel}` : "Not run yet"}
      </MetaChip>
    </div>
  )
}

export default function DashboardPage() {
  const { campaignId, campaigns } = useCampaign()
  const [stats, setStats] = React.useState<Stats | null>(null)
  const [top, setTop] = React.useState<Lead[]>([])

  React.useEffect(() => {
    if (!campaignId) return
    let active = true
    api.stats(campaignId).then((s) => active && setStats(s)).catch(() => active && setStats(null))
    api.leads(campaignId, { company_type: "BUYER", limit: 8 })
      .then((r) => active && setTop(r.items)).catch(() => active && setTop([]))
    return () => { active = false }
  }, [campaignId])

  const campaign = campaigns.find((c) => c.campaign_id === campaignId)
  // While a newly-selected campaign's data is in flight, `stats` still holds the previous
  // campaign's numbers – detect that via the campaign_id it carries and show skeletons instead.
  const loading = !stats || stats.campaign_id !== campaignId

  if (!campaignId) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card className="max-w-md text-center">
          <CardContent className="p-10">
            <div className="mx-auto flex size-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
              <Layers className="size-6" />
            </div>
            <h2 className="mt-5 text-lg font-semibold">No campaign selected</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Create a campaign to start finding companies that need what you sell.
            </p>
            <Button className="mt-6" nativeButton={false} render={<Link href="/campaigns" />}>
              Go to campaigns
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const bands = stats ? Object.entries(stats.score_bands).map(([band, count]) => ({ band, count })) : []
  const qualifiedRate = stats && stats.leads > 0 ? Math.round((stats.qualified / stats.leads) * 100) : null

  return (
    <div className="mx-auto grid max-w-7xl gap-8">
      {/* Header */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="truncate text-2xl font-bold tracking-tight">{campaign?.name ?? campaignId}</h1>
            {campaign?.offer && <p className="mt-1 text-muted-foreground">{campaign.offer}</p>}
          </div>
          <Button variant="outline" size="sm" nativeButton={false} render={<Link href="/leads" />}>
            View all leads
            <ArrowUpRight className="size-4" />
          </Button>
        </div>
        <CampaignMeta campaign={campaign} />
      </div>

      {/* KPIs – pipeline funnel first, then engagement & quality */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {!loading && stats ? (
          <>
            <StatCard title="Companies processed" value={stats.leads} icon={Users}
              hint={`${stats.by_type.BUYER} buyers · ${stats.by_type.VENDOR} vendors · ${stats.by_type.UNKNOWN} unknown`} />
            <StatCard title="With intent" value={stats.with_intent} icon={Target}
              hint="tenders, RFQs or hiring that imply a purchase" />
            <StatCard title="Qualified buyers" value={stats.qualified} icon={ShieldCheck} highlight
              hint={`score ≥ ${campaign?.min_score ?? 70} · ${stats.outreach_ready} outreach-ready`} />
            <StatCard title="Emails sent" value={stats.emails_sent} icon={Send}
              hint={`${stats.by_status.email_1_sent} step 1 · ${stats.by_status.followup_1_sent} step 2 · ${stats.by_status.followup_2_sent} done`} />
            <StatCard title="Replies" value={stats.replied} icon={MessageSquareReply}
              hint={`${stats.bounced} bounced · ${stats.by_status.unsubscribed} unsubscribed`} />
            <StatCard title="Reviewer accuracy"
              value={stats.accuracy === null ? "–" : `${Math.round(stats.accuracy * 100)}%`} icon={Gauge}
              hint={stats.reviewed ? `${stats.correct}/${stats.reviewed} marked correct · target 80%` : "mark leads correct / wrong in the queue"} />
          </>
        ) : (
          Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-[136px] rounded-xl" />)
        )}
      </div>

      {/* Chart + table */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">Score distribution</CardTitle>
            <CardDescription>70+ is outreach-eligible; 50–69 goes to review</CardDescription>
          </CardHeader>
          <CardContent>
            {!loading && stats ? (
              <ChartContainer config={chartConfig} className="h-[220px] w-full">
                <BarChart data={bands} margin={{ left: -16, top: 4 }}>
                  <CartesianGrid vertical={false} strokeDasharray="3 3" className="stroke-border/60" />
                  <XAxis dataKey="band" tickLine={false} axisLine={false} className="text-xs" />
                  <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={32} className="text-xs" />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar dataKey="count" fill="var(--color-count)" radius={[6, 6, 0, 0]} maxBarSize={56} isAnimationActive={false} />
                </BarChart>
              </ChartContainer>
            ) : (
              <Skeleton className="h-[220px] w-full rounded-lg" />
            )}
            {!loading && stats && qualifiedRate !== null && (
              <p className="mt-4 border-t pt-4 text-sm text-muted-foreground">
                <span className="font-semibold text-foreground tabular-nums">{qualifiedRate}%</span> of processed
                companies qualified ({stats.qualified} of {stats.leads}).
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between gap-2">
              <div>
                <CardTitle className="text-base">Top buyers</CardTitle>
                <CardDescription>Highest-scoring companies that need your offer</CardDescription>
              </div>
              <Link href="/leads"><Button variant="outline" size="sm">All leads</Button></Link>
            </div>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead className="w-10 text-center">#</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Contact</TableHead>
                  <TableHead className="text-center">Score</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Sequence</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {!loading && top.map((l, i) => (
                  <TableRow key={l.lead_id} className="group">
                    <TableCell className="text-center text-sm font-medium tabular-nums text-muted-foreground">{i + 1}</TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-medium">{l.company_name}</span>
                        <span className="text-xs text-muted-foreground">
                          {l.domain ?? "no website"} · {l.city}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className={cn("text-sm", !l.contact_name && "text-muted-foreground")}>
                          {l.contact_name ?? "no named contact"}
                        </span>
                        {l.contact_email && (
                          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                            <Mail className="size-3" />{l.contact_email}
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-center"><ScoreBadge score={l.total_score} /></TableCell>
                    <TableCell><TypeBadge type={l.company_type} /></TableCell>
                    <TableCell><StatusBadge status={l.sequence_status} /></TableCell>
                  </TableRow>
                ))}
                {!loading && top.length === 0 && (
                  <TableRow className="hover:bg-transparent">
                    <TableCell colSpan={6} className="py-12 text-center text-sm text-muted-foreground">
                      No qualified buyers yet – run the campaign to populate this list.
                    </TableCell>
                  </TableRow>
                )}
                {loading && Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i} className="hover:bg-transparent">
                    <TableCell colSpan={6}><Skeleton className="h-8 w-full" /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
