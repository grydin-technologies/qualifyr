"use client"

import * as React from "react"
import { api, PENDING_MONETIZATION_KEY, PENDING_MONETIZATION_COMMENT_KEY, type Campaign } from "@/lib/api"

interface Ctx {
  campaigns: Campaign[]
  campaignId: string | null
  setCampaignId: (id: string) => void
  refresh: (force?: boolean) => Promise<void>
  loading: boolean
  error: string | null
  keyCount: number
  configuredKeys: Set<string>
  keysLoading: boolean
  refreshKeys: () => void
}

const CampaignContext = React.createContext<Ctx | null>(null)

export function CampaignProvider({ children }: { children: React.ReactNode }) {
  const [campaigns, setCampaigns] = React.useState<Campaign[]>([])
  const [campaignId, setCampaignIdState] = React.useState<string | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const lastFetch = React.useRef(0)
  const [configuredKeys, setConfiguredKeys] = React.useState<Set<string>>(new Set())
  const [keysLoading, setKeysLoading] = React.useState(true)

  const refreshKeys = React.useCallback(() => {
    api.listApiKeys()
      .then((r) => setConfiguredKeys(new Set(r.keys.map((k) => k.key_name))))
      .catch(() => {})
      .finally(() => setKeysLoading(false))
  }, [])

  React.useEffect(() => { refreshKeys() }, [refreshKeys])

  const refresh = React.useCallback(async (force = false) => {
    const now = Date.now()
    if (!force && now - lastFetch.current < 5000) return
    lastFetch.current = now
    try {
      const list = await api.campaigns()
      setCampaigns(list)
      setError(null)
      setCampaignIdState((cur) => {
        if (cur && list.some((c) => c.campaign_id === cur)) return cur
        let saved: string | null = null
        try { saved = localStorage.getItem("qualifyr.campaign") } catch { /* ignore */ }
        const pick = list.find((c) => c.campaign_id === saved) ?? list[0]
        return pick?.campaign_id ?? null
      })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => { refresh(true) }, [refresh])

  // While any campaign has an active run, keep the list fresh so run status and counts stay
  // live across the whole app – a dispatched run must never look like "nothing ran", on any
  // page, after navigating away and back. The provider lives at the app shell, so this poll
  // survives page navigation.
  const anyRunActive = campaigns.some(
    (c) => c.live && !["idle", "completed", "failed"].includes(c.live.stage),
  )
  React.useEffect(() => {
    if (!anyRunActive) return
    const t = setInterval(() => { void refresh(true) }, 4000)
    return () => clearInterval(t)
  }, [anyRunActive, refresh])

  // Flush the sign-up monetization vote once there is an authenticated session (it may have
  // been stashed before e-mail confirmation, when no token existed yet).
  React.useEffect(() => {
    let pending: string | null = null
    try { pending = localStorage.getItem(PENDING_MONETIZATION_KEY) } catch { /* ignore */ }
    if (pending) {
      api.setPreference("monetization_preference", pending)
        .then(() => { try { localStorage.removeItem(PENDING_MONETIZATION_KEY) } catch { /* ignore */ } })
        .catch(() => { /* retried on next load */ })
    }
    let comment: string | null = null
    try { comment = localStorage.getItem(PENDING_MONETIZATION_COMMENT_KEY) } catch { /* ignore */ }
    if (comment) {
      api.setPreference("monetization_comment", comment)
        .then(() => { try { localStorage.removeItem(PENDING_MONETIZATION_COMMENT_KEY) } catch { /* ignore */ } })
        .catch(() => { /* retried on next load */ })
    }
  }, [])

  const setCampaignId = (id: string) => {
    setCampaignIdState(id)
    try { localStorage.setItem("qualifyr.campaign", id) } catch { /* ignore */ }
  }

  return (
    <CampaignContext.Provider value={{ campaigns, campaignId, setCampaignId, refresh, loading, error, keyCount: configuredKeys.size, configuredKeys, keysLoading, refreshKeys }}>
      {children}
    </CampaignContext.Provider>
  )
}

export function useCampaign(): Ctx {
  const ctx = React.useContext(CampaignContext)
  if (!ctx) throw new Error("useCampaign outside CampaignProvider")
  return ctx
}
