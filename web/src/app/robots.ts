import type { MetadataRoute } from "next"

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "https://qualifyr.vercel.app"

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // No signed-in route should ever be crawled or appear in a search result, and
        // /sign-in is already noindex at the page level – disallow it here too so a
        // crawler never fetches it in the first place.
        disallow: ["/dashboard", "/campaigns", "/leads", "/outreach", "/settings", "/sign-in"],
      },
    ],
    sitemap: `${siteUrl}/sitemap.xml`,
  }
}
