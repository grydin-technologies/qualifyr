"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { Eye, EyeOff, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { api, PENDING_MONETIZATION_KEY, PENDING_MONETIZATION_COMMENT_KEY } from "@/lib/api"
import { createClient } from "@/lib/supabase/client"
import { supabaseConfigured } from "@/lib/supabase/config"

const USE_OPTIONS = [
  { value: "own_keys", label: "I'll bring my own API keys (free tier)" },
  { value: "managed_paid", label: "I'd pay for a managed version (no keys needed)" },
  { value: "undecided", label: "Not sure yet" },
]

export function SignUpForm() {
  const router = useRouter()
  const [showPassword, setShowPassword] = React.useState(false)
  const [pending, setPending] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [sent, setSent] = React.useState(false)
  const [usage, setUsage] = React.useState("")
  const [comment, setComment] = React.useState("")

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    if (!usage) {
      setError("Please tell us how you'd like to use Qualifyr.")
      return
    }
    setPending(true)

    const form = new FormData(event.currentTarget)
    const email = String(form.get("email") ?? "")
    const password = String(form.get("password") ?? "")

    try {
      const { data, error } = await createClient().auth.signUp({
        email,
        password,
        options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
      })
      if (error) {
        setError(error.message)
        return
      }
      // Stash the vote (and the optional free-text answer, so an admin can read what people
      // wrote) so both are saved even when the account needs e-mail confirmation first (no
      // session/token yet). They are flushed to the backend on the first authenticated load.
      const trimmedComment = comment.trim()
      try {
        localStorage.setItem(PENDING_MONETIZATION_KEY, usage)
        if (trimmedComment) localStorage.setItem(PENDING_MONETIZATION_COMMENT_KEY, trimmedComment)
      } catch { /* ignore */ }
      // A session on the response means email confirmation is off and this account is
      // already active - otherwise Supabase is waiting on a confirmation link, and there
      // is nothing to sign in to yet.
      if (data.session) {
        try {
          await api.setPreference("monetization_preference", usage)
          localStorage.removeItem(PENDING_MONETIZATION_KEY)
          if (trimmedComment) {
            await api.setPreference("monetization_comment", trimmedComment)
            localStorage.removeItem(PENDING_MONETIZATION_COMMENT_KEY)
          }
        } catch { /* flushed later on first authenticated load */ }
        router.replace("/dashboard")
        router.refresh()
      } else {
        setSent(true)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reach the sign-up service.")
    } finally {
      setPending(false)
    }
  }

  if (!supabaseConfigured) {
    return (
      <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
        Sign-up is not configured: <code>NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
        <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> are missing from this build. On Vercel
        they are inlined at build time, so add them and redeploy.
      </p>
    )
  }

  if (sent) {
    return (
      <p className="rounded-lg border border-border/60 bg-muted/30 p-4 text-sm text-muted-foreground">
        Check your email to confirm your account, then sign in.
      </p>
    )
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          placeholder="you@company.com"
          required
          className="h-10"
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="password">Password</Label>
        <div className="relative">
          <Input
            id="password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="new-password"
            placeholder="At least 8 characters"
            required
            minLength={8}
            className="h-10 pr-10"
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? "sign-up-error" : undefined}
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground hover:text-foreground"
          >
            {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
            <span className="sr-only">{showPassword ? "Hide" : "Show"} password</span>
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <Label>How would you like to use Qualifyr?</Label>
        <div className="grid gap-1.5">
          {USE_OPTIONS.map((opt) => (
            <label key={opt.value} className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="radio"
                name="usage"
                value={opt.value}
                checked={usage === opt.value}
                onChange={() => setUsage(opt.value)}
                className="accent-brand"
              />
              <span>{opt.label}</span>
            </label>
          ))}
        </div>
        <Textarea
          id="usage-comment"
          name="usage-comment"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Anything else you'd like us to know? (optional)"
          rows={3}
          className="mt-1"
        />
      </div>

      {error && (
        <p id="sign-up-error" role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      <Button
        type="submit"
        disabled={pending}
        className="h-10 bg-brand text-brand-foreground hover:bg-brand/90"
      >
        {pending && <Loader2 className="size-4 animate-spin" />}
        {pending ? "Creating account…" : "Create account"}
      </Button>
    </form>
  )
}
