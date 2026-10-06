"use client"

import * as React from "react"
import { Ban, Trash2, Save, Plus, Key, BarChart3, FlaskConical, Eye, EyeOff, Power, Loader2 } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api, type MailboxState, type Suppression } from "@/lib/api"
import { useCampaign } from "@/components/campaign-context"
import { cn } from "@/lib/utils"

const KEY_INFO: Record<string, { label: string; description: string; url: string }> = {
  brave: { label: "Brave Search", description: "Web search for company discovery. Falls back to DuckDuckGo without a key.", url: "https://brave.com/search/api/" },
  groq: { label: "Groq (LLM)", description: "AI-powered keyword generation, intent judging and relevance matching.", url: "https://console.groq.com/keys" },
  gemini: { label: "Google Gemini", description: "Alternative LLM provider. Used as fallback when Groq is unavailable.", url: "https://aistudio.google.com/apikey" },
  hunter: { label: "Hunter.io", description: "Email verification for decision-maker contacts. Falls back to MX-only check.", url: "https://hunter.io/api-keys" },
  places: { label: "Google Places", description: "Rating, review count and opening hours enrichment. 1K free calls/month.", url: "https://console.cloud.google.com/apis/credentials" },
}

/** Shown while the server config is still being checked – so neither the "add" form nor the
 *  "not configured" warning flashes before we actually know the state. */
function CheckingConfig() {
  return (
    <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" /> Checking server configuration…
    </div>
  )
}

/** Soft, informational notice when server-side encryption isn't set up. Replaces the old
 *  bare red line – only rendered after the config check completes and only when it's missing. */
function EncryptionNotice({ what }: { what: string }) {
  return (
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-700 dark:text-amber-400">
      <p className="font-medium">Encryption isn’t set up yet</p>
      <p className="mt-1 text-amber-700/90 dark:text-amber-400/90">
        {what} needs a server-side encryption key so your secrets are stored safely. Set{" "}
        <code className="font-mono text-xs">GTM_ENCRYPTION_KEY</code> in the server environment, then reload this page.
      </p>
    </div>
  )
}

function ApiKeys() {
  const [keys, setKeys] = React.useState<{ key_name: string; created_at: string }[]>([])
  const [encryptionAvailable, setEncryptionAvailable] = React.useState(false)
  const [loading, setLoading] = React.useState(true)
  const [inputs, setInputs] = React.useState<Record<string, string>>({})
  const [visible, setVisible] = React.useState<Record<string, boolean>>({})
  const [testing, setTesting] = React.useState<string | null>(null)
  const [testResult, setTestResult] = React.useState<Record<string, { ok: boolean; message: string }>>({})
  const [saving, setSaving] = React.useState<string | null>(null)

  const configured = React.useMemo(() => new Set(keys.map((k) => k.key_name)), [keys])

  const load = React.useCallback(() => {
    api.listApiKeys().then((r) => { setKeys(r.keys); setEncryptionAvailable(r.encryption_available) })
      .catch(() => {}).finally(() => setLoading(false))
  }, [])
  React.useEffect(() => { load() }, [load])

  const saveKey = async (name: string) => {
    const val = inputs[name]?.trim()
    if (!val) return
    setSaving(name)
    try {
      await api.saveApiKey(name, val)
      setInputs((p) => ({ ...p, [name]: "" }))
      load()
    } catch { /* toast? */ } finally { setSaving(null) }
  }

  const deleteKey = async (name: string) => {
    if (!confirm(`Remove your ${KEY_INFO[name]?.label ?? name} API key?`)) return
    try { await api.deleteApiKey(name); load() } catch { /* */ }
  }

  const testKey = async (name: string) => {
    setTesting(name)
    setTestResult((p) => ({ ...p, [name]: { ok: false, message: "Testing..." } }))
    try {
      const r = await api.testApiKey(name)
      setTestResult((p) => ({ ...p, [name]: r }))
    } catch (e) {
      setTestResult((p) => ({ ...p, [name]: { ok: false, message: (e as Error).message } }))
    } finally { setTesting(null) }
  }

  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle>API Keys</CardTitle>
          <CardDescription>
            Add your own API keys to unlock premium features. All keys are encrypted at rest.
            Without keys, the engine uses free fallbacks (DuckDuckGo, MX-only verification, no LLM refinement).
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          {loading ? <CheckingConfig /> : !encryptionAvailable ? <EncryptionNotice what="Saving your own API keys" /> :
          Object.entries(KEY_INFO).map(([name, info]) => (
            <div key={name} className="rounded-lg border p-4">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <Key className="h-4 w-4 text-muted-foreground" />
                  <span className="font-medium text-sm">{info.label}</span>
                  {configured.has(name)
                    ? <Badge className="text-xs">configured</Badge>
                    : <Badge variant="outline" className="text-xs">not configured</Badge>}
                </div>
                <a href={info.url} target="_blank" rel="noopener noreferrer" className="text-xs text-muted-foreground underline">
                  Get a key
                </a>
              </div>
              <p className="text-xs text-muted-foreground mb-3">{info.description}</p>
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative flex-1 min-w-[200px] max-w-sm">
                  <Input
                    type={visible[name] ? "text" : "password"}
                    placeholder={configured.has(name) ? "••••••••" : "Paste your key"}
                    value={inputs[name] ?? ""}
                    onChange={(e) => setInputs((p) => ({ ...p, [name]: e.target.value }))}
                    disabled={!encryptionAvailable}
                    className="pr-8 font-mono text-xs"
                  />
                  <button
                    type="button"
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground"
                    onClick={() => setVisible((p) => ({ ...p, [name]: !p[name] }))}
                  >
                    {visible[name] ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                  </button>
                </div>
                <Button size="sm" onClick={() => saveKey(name)} disabled={!encryptionAvailable || !inputs[name]?.trim() || saving === name}>
                  <Save className="h-3.5 w-3.5 mr-1" /> Save
                </Button>
                {configured.has(name) && (
                  <>
                    <Button size="sm" variant="outline" onClick={() => testKey(name)} disabled={testing === name}>
                      <FlaskConical className="h-3.5 w-3.5 mr-1" /> Test
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => deleteKey(name)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </>
                )}
              </div>
              {testResult[name] && (
                <p className={cn("text-xs mt-2", testResult[name].ok ? "text-green-600 dark:text-green-400" : "text-destructive")}>
                  {testResult[name].message}
                </p>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

function UsageDashboard() {
  const [usage, setUsage] = React.useState<Record<string, { count: number; limit: number; default_limit: number; max_limit: number }>>({})
  const [editing, setEditing] = React.useState<string | null>(null)
  const [editValue, setEditValue] = React.useState("")
  const [saving, setSaving] = React.useState(false)

  const load = React.useCallback(() => { api.getUsage().then((r) => setUsage(r.usage)).catch(() => {}) }, [])
  React.useEffect(() => { load() }, [load])

  const resources = [
    { key: "brave", label: "Brave Search", unit: "searches" },
    { key: "groq", label: "Groq LLM", unit: "calls" },
    { key: "hunter", label: "Hunter.io", unit: "verifications" },
    { key: "places", label: "Google Places", unit: "lookups" },
  ]

  const startEdit = (key: string) => {
    setEditing(key)
    setEditValue(String(usage[key]?.limit ?? 50))
  }

  const saveLimit = async () => {
    if (!editing) return
    const val = parseInt(editValue, 10)
    if (!val || val < 1) return
    setSaving(true)
    try {
      await api.updateUsageLimit(editing, val)
      setEditing(null)
      load()
    } catch { /* */ } finally { setSaving(false) }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Daily usage</CardTitle>
        <CardDescription>
          Usage resets at midnight UTC each day. Limits keep the free tier sustainable.
          When a limit is reached, the engine falls back to free alternatives automatically.
          You can adjust limits to match your needs.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {resources.map((r) => {
          const u = usage[r.key] ?? { count: 0, limit: 50, default_limit: 50, max_limit: 500 }
          const pct = Math.min(100, Math.round((u.count / u.limit) * 100))
          const isEditing = editing === r.key
          return (
            <div key={r.key}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium">{r.label}</span>
                <div className="flex items-center gap-2">
                  {isEditing ? (
                    <div className="flex items-center gap-1">
                      <input
                        type="number"
                        min={1}
                        max={u.max_limit}
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        className="w-16 rounded border bg-transparent px-1.5 py-0.5 text-xs text-right"
                        autoFocus
                        onKeyDown={(e) => { if (e.key === "Enter") saveLimit(); if (e.key === "Escape") setEditing(null) }}
                      />
                      <span className="text-xs text-muted-foreground">/ {u.max_limit} max</span>
                      <Button size="sm" variant="ghost" className="h-6 px-1.5 text-xs" onClick={saveLimit} disabled={saving}>
                        <Save className="h-3 w-3" />
                      </Button>
                      <button type="button" className="text-xs text-muted-foreground hover:text-foreground" onClick={() => setEditing(null)}>✕</button>
                    </div>
                  ) : (
                    <>
                      <span className="text-xs text-muted-foreground">{u.count} / {u.limit} {r.unit}</span>
                      <button
                        type="button"
                        className="text-xs text-muted-foreground underline hover:text-foreground"
                        onClick={() => startEdit(r.key)}
                      >
                        edit
                      </button>
                    </>
                  )}
                </div>
              </div>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div
                  className={cn("h-full rounded-full transition-all", pct >= 90 ? "bg-destructive" : pct >= 70 ? "bg-yellow-500" : "bg-primary")}
                  style={{ width: `${pct}%` }}
                />
              </div>
              {isEditing && u.limit !== u.default_limit && (
                <p className="text-[11px] text-muted-foreground mt-0.5">Default: {u.default_limit}</p>
              )}
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}

function Suppressions() {
  const [rows, setRows] = React.useState<Suppression[]>([])
  const [value, setValue] = React.useState("")
  const [reason, setReason] = React.useState("")
  const load = React.useCallback(() => { api.suppressions().then(setRows).catch(() => setRows([])) }, [])
  React.useEffect(() => { load() }, [load])
  const add = async () => {
    if (!value.trim()) return
    await api.addSuppression(value.trim(), reason.trim() || undefined)
    setValue(""); setReason(""); load()
  }
  const remove = async (v: string) => {
    if (!confirm(`Allow contacting ${v} again?`)) return
    await api.removeSuppression(v); load()
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>Suppression list</CardTitle>
        <CardDescription>Addresses and domains that are never emailed. Bounces, unsubscribes and "not interested" replies land here automatically.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <Input className="max-w-xs" placeholder="email or domain" value={value} onChange={(e) => setValue(e.target.value)} />
          <Input className="max-w-xs" placeholder="reason (optional)" value={reason} onChange={(e) => setReason(e.target.value)} />
          <Button onClick={add}><Ban data-icon="inline-start" /> Suppress</Button>
        </div>
        <Table>
          <TableHeader>
            <TableRow><TableHead>Value</TableHead><TableHead>Kind</TableHead><TableHead>Reason</TableHead><TableHead>Added</TableHead><TableHead /></TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.value}>
                <TableCell className="font-mono text-xs">{r.value}</TableCell>
                <TableCell><Badge variant="outline">{r.kind}</Badge></TableCell>
                <TableCell className="text-xs text-muted-foreground">{r.reason ?? ""}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{new Date(r.created_at).toLocaleDateString()}</TableCell>
                <TableCell><Button size="icon-xs" variant="ghost" onClick={() => remove(r.value)}><Trash2 /></Button></TableCell>
              </TableRow>
            ))}
            {rows.length === 0 && <TableRow><TableCell colSpan={5} className="text-center text-muted-foreground">Nothing suppressed.</TableCell></TableRow>}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

function Mailboxes({ campaignId }: { campaignId: string | null }) {
  const [liveRows, setLiveRows] = React.useState<MailboxState[]>([])
  const [userRows, setUserRows] = React.useState<{ address: string; smtp_host: string; smtp_port: number; sender_name: string | null; daily_limit: number | null; enabled: boolean; created_at: string }[]>([])
  const [encryptionAvailable, setEncryptionAvailable] = React.useState(false)
  const [loading, setLoading] = React.useState(true)
  const [adding, setAdding] = React.useState(false)
  const [addr, setAddr] = React.useState("")
  const [pw, setPw] = React.useState("")
  const [smtpHost, setSmtpHost] = React.useState("smtp.gmail.com")
  const [smtpPort, setSmtpPort] = React.useState("587")
  const [senderName, setSenderName] = React.useState("")
  const [busy, setBusy] = React.useState<string | null>(null)
  const [msg, setMsg] = React.useState<{ ok: boolean; text: string } | null>(null)
  const [showPw, setShowPw] = React.useState(false)

  const loadLive = React.useCallback(() => {
    api.mailboxes(campaignId ?? undefined).then(setLiveRows).catch(() => setLiveRows([]))
  }, [campaignId])
  const loadUser = React.useCallback(() => {
    api.listUserMailboxes().then((r) => { setUserRows(r.mailboxes); setEncryptionAvailable(r.encryption_available) })
      .catch(() => {}).finally(() => setLoading(false))
  }, [])
  React.useEffect(() => { loadLive(); loadUser() }, [loadLive, loadUser])

  const testConn = async () => {
    setBusy("test"); setMsg(null)
    try {
      const r = await api.testUserMailbox({ address: addr, password: pw, smtp_host: smtpHost, smtp_port: Number(smtpPort) || 587 })
      setMsg({ ok: r.ok, text: r.message })
    } catch (e) { setMsg({ ok: false, text: (e as Error).message }) } finally { setBusy(null) }
  }

  const save = async () => {
    if (!addr.trim() || !pw.trim()) { setMsg({ ok: false, text: "Email and password are required." }); return }
    setBusy("save"); setMsg(null)
    try {
      await api.saveUserMailbox({ address: addr.trim(), password: pw.trim(), smtp_host: smtpHost, smtp_port: Number(smtpPort) || 587, sender_name: senderName.trim() || undefined })
      setAddr(""); setPw(""); setSenderName(""); setSmtpHost("smtp.gmail.com"); setSmtpPort("587"); setAdding(false); setMsg(null)
      loadUser(); loadLive()
    } catch (e) { setMsg({ ok: false, text: (e as Error).message }) } finally { setBusy(null) }
  }

  const remove = async (address: string) => {
    if (!confirm(`Remove mailbox ${address}?`)) return
    try { await api.deleteUserMailbox(address); loadUser(); loadLive() } catch (e) { alert((e as Error).message) }
  }

  const toggle = async (address: string) => {
    try { await api.toggleUserMailbox(address); loadUser(); loadLive() } catch (e) { alert((e as Error).message) }
  }

  return (
    <div className="grid gap-4">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <CardTitle>Your mailboxes</CardTitle>
              <CardDescription>Add your Gmail or SMTP account to send outreach emails. Credentials are encrypted at rest. For Gmail, use an <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer" className="underline">App Password</a> (not your regular password).</CardDescription>
            </div>
            {!loading && encryptionAvailable && !adding && (
              <Button size="sm" onClick={() => setAdding(true)}><Plus className="h-3.5 w-3.5 mr-1" /> Add mailbox</Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="grid gap-4">
          {loading ? <CheckingConfig /> : !encryptionAvailable ? <EncryptionNotice what="Storing a mailbox" /> : (
          <>
          {adding && (
            <div className="rounded-lg border p-4 grid gap-3">
              <div className="grid gap-1.5">
                <label className="text-xs font-medium">Email address</label>
                <Input value={addr} onChange={(e) => setAddr(e.target.value)} placeholder="you@gmail.com" />
              </div>
              <div className="grid gap-1.5">
                <label className="text-xs font-medium">App password</label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Input type={showPw ? "text" : "password"} value={pw} onChange={(e) => setPw(e.target.value)} placeholder="xxxx xxxx xxxx xxxx" />
                    <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                      {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="grid gap-1.5">
                  <label className="text-xs font-medium">SMTP host</label>
                  <Input value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)} />
                </div>
                <div className="grid gap-1.5">
                  <label className="text-xs font-medium">Port</label>
                  <Input value={smtpPort} onChange={(e) => setSmtpPort(e.target.value)} />
                </div>
              </div>
              <div className="grid gap-1.5">
                <label className="text-xs font-medium">Sender name (optional)</label>
                <Input value={senderName} onChange={(e) => setSenderName(e.target.value)} placeholder="Your Name" />
              </div>
              {msg && <p className={cn("text-sm", msg.ok ? "text-green-600 dark:text-green-400" : "text-destructive")}>{msg.text}</p>}
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={testConn} disabled={!!busy}>
                  <FlaskConical className="h-3.5 w-3.5 mr-1" />{busy === "test" ? "Testing…" : "Test connection"}
                </Button>
                <Button size="sm" onClick={save} disabled={!!busy}>
                  <Save className="h-3.5 w-3.5 mr-1" />{busy === "save" ? "Saving…" : "Save mailbox"}
                </Button>
                <Button variant="ghost" size="sm" onClick={() => { setAdding(false); setMsg(null) }}>Cancel</Button>
              </div>
            </div>
          )}
          {userRows.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow><TableHead>Address</TableHead><TableHead>SMTP</TableHead><TableHead>Sender</TableHead><TableHead>Status</TableHead><TableHead /></TableRow>
              </TableHeader>
              <TableBody>
                {userRows.map((m) => (
                  <TableRow key={m.address}>
                    <TableCell className="font-mono text-xs">{m.address}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{m.smtp_host}:{m.smtp_port}</TableCell>
                    <TableCell className="text-xs">{m.sender_name ?? "–"}</TableCell>
                    <TableCell>
                      <Badge variant={m.enabled ? "default" : "secondary"}>{m.enabled ? "active" : "paused"}</Badge>
                    </TableCell>
                    <TableCell className="flex gap-1 justify-end">
                      <Button size="icon-xs" variant="ghost" onClick={() => toggle(m.address)} title={m.enabled ? "Pause" : "Enable"}>
                        <Power className="h-3.5 w-3.5" />
                      </Button>
                      <Button size="icon-xs" variant="ghost" onClick={() => remove(m.address)} className="text-muted-foreground hover:text-destructive">
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : !adding && (
            <p className="text-sm text-muted-foreground">No mailboxes added yet. Add one to start sending outreach emails.</p>
          )}
          </>
          )}
        </CardContent>
      </Card>
      {liveRows.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Live mailbox status</CardTitle>
            <CardDescription>Daily send counts, warm-up progress and bounce guard for all active mailboxes.</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow><TableHead>Address</TableHead><TableHead>Auth</TableHead><TableHead>Today</TableHead><TableHead>Warm-up</TableHead><TableHead>Bounced</TableHead><TableHead>State</TableHead></TableRow>
              </TableHeader>
              <TableBody>
                {liveRows.map((m) => (
                  <TableRow key={m.address} className={cn(m.paused_reason && "bg-destructive/5")}>
                    <TableCell className="font-mono text-xs">{m.address}</TableCell>
                    <TableCell><Badge variant="outline">{m.auth_mode}</Badge></TableCell>
                    <TableCell>{m.sent_today}/{m.cap}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{m.days_active ? `day ${m.days_active}` : "never sent"}</TableCell>
                    <TableCell>{m.bounced_today}</TableCell>
                    <TableCell>{m.paused_reason ? <Badge variant="destructive">{m.paused_reason}</Badge> : <Badge>{m.remaining} left</Badge>}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default function SettingsPage() {
  const { campaignId } = useCampaign()
  const [tab, setTab] = React.useState("api-keys")
  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">API keys, usage limits, mailboxes and suppressions.</p>
      </div>
      <Tabs value={tab} onValueChange={(v) => setTab(String(v))}>
        <TabsList>
          <TabsTrigger value="api-keys"><Key className="h-3.5 w-3.5 mr-1" />API Keys</TabsTrigger>
          <TabsTrigger value="usage"><BarChart3 className="h-3.5 w-3.5 mr-1" />Usage</TabsTrigger>
          <TabsTrigger value="mailboxes">Mailboxes</TabsTrigger>
          <TabsTrigger value="suppressions">Suppressions</TabsTrigger>
        </TabsList>
      </Tabs>
      {tab === "api-keys" && <ApiKeys />}
      {tab === "usage" && <UsageDashboard />}
      {tab === "mailboxes" && <Mailboxes campaignId={campaignId} />}
      {tab === "suppressions" && <Suppressions />}
    </div>
  )
}
