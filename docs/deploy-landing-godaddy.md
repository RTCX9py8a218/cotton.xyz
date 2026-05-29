# Deploy landing page — cotton.xyz (GoDaddy domain)

The landing page is **100% static** — no build step. You can host it on free static hosting and point your GoDaddy domain at it, or upload directly to GoDaddy web hosting if you have a plan.

**Recommended:** Netlify or Cloudflare Pages (free HTTPS, fast, easy updates). Keep the domain registered at GoDaddy; only DNS changes.

---

## Files to deploy

### Landing only (minimum)

```text
index.html
styles.css
script.js
site.webmanifest
robots.txt
sitemap.xml
assets/cotton-logo.png
```

### Landing + trade UI shell (optional)

Also upload `app.html`, `app.css`, `app.js`, `earn.html`, `earn.css`, `earn.js` if shipping the trade + earn UI.
Note: **app.html needs the Python relayer** for live marks — on a static host it will show “Connecting” unless you later point it at a hosted API URL.

Do **not** upload: `backend/`, `docs/`, `node_modules/`, `.venv/`.

---

## Option A — Netlify (recommended, already configured)

This repo includes `netlify.toml` and `_redirects` — ready to deploy.

### 1. Push code to GitHub

If the project is not on GitHub yet:

```bash
cd ~/Projects/cotton-landing
git init
git add index.html styles.css script.js app.html app.css app.js assets/ site.webmanifest robots.txt sitemap.xml netlify.toml _redirects vercel.json
git commit -m "Initial landing page"
# Create repo on GitHub, then:
git remote add origin git@github.com:YOUR_USER/cotton-landing.git
git push -u origin main
```

### 2. Connect Netlify

1. Go to [https://app.netlify.com](https://app.netlify.com) → **Add new site** → **Import from Git**
2. Select the repo
3. Build settings:
   - **Build command:** *(leave empty)*
   - **Publish directory:** `.` (root)
4. Deploy

Your site gets a URL like `https://random-name.netlify.app`.

### 3. Add custom domain in Netlify

1. Netlify → **Site configuration** → **Domain management** → **Add domain**
2. Enter `cotton.xyz` and `www.cotton.xyz`

Netlify shows the DNS records you need.

### 4. GoDaddy DNS

1. Log in to [GoDaddy](https://dcc.godaddy.com) → **My Products** → **cotton.xyz** → **DNS**
2. Add/update records (Netlify docs may vary slightly — use what Netlify shows):

| Type | Name | Value | TTL |
|------|------|-------|-----|
| **A** | `@` | `75.2.60.5` | 600 |
| **CNAME** | `www` | `your-site.netlify.app` | 600 |

3. Remove conflicting old A/CNAME records for `@` and `www` if present.
4. Wait 5–60 minutes for DNS propagation.
5. Netlify will auto-provision **HTTPS** (Let’s Encrypt).

### 5. Verify

- `https://cotton.xyz` loads the landing page
- Logo and styles load (`/assets/cotton-logo.png`)
- “Launch app” → `https://cotton.xyz/app.html` (static shell only until API is hosted)

---

## Option B — Cloudflare Pages (free, excellent DNS)

Good if you want Cloudflare CDN + DNS in one place.

### 1. Cloudflare account

1. [https://dash.cloudflare.com](https://dash.cloudflare.com) → **Add site** → `cotton.xyz`
2. Cloudflare scans existing DNS — continue
3. Cloudflare gives you **two nameservers** (e.g. `ada.ns.cloudflare.com`)

### 2. Point GoDaddy nameservers to Cloudflare

1. GoDaddy → **cotton.xyz** → **Nameservers** → **Change**
2. Select **Custom** → paste Cloudflare nameservers → Save
3. Back in Cloudflare, wait until status is **Active**

### 3. Deploy on Pages

1. Cloudflare → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
2. Select repo, settings:
   - **Framework preset:** None
   - **Build command:** *(empty)*
   - **Build output directory:** `/`
3. Deploy

### 4. Custom domain

1. Pages project → **Custom domains** → add `cotton.xyz` and `www.cotton.xyz`
2. Cloudflare creates DNS records automatically (you’re already on their nameservers)

HTTPS is automatic.

---

## Option C — GoDaddy Web Hosting (cPanel / File Manager)

Use this only if you **already pay** for GoDaddy **Web Hosting** (not domain-only).

### 1. Open File Manager

GoDaddy → **Hosting** → **Manage** → **File Manager** → `public_html`

### 2. Upload files

Upload the landing files listed above into `public_html` (not in a subfolder):

```text
public_html/
  index.html
  styles.css
  script.js
  assets/cotton-logo.png
  ...
```

`index.html` must sit directly in `public_html`.

### 3. Domain

If hosting and domain are on the same GoDaddy account, `cotton.xyz` usually points to this folder automatically.

### 4. HTTPS

Enable **SSL** in GoDaddy hosting panel (free certificate). Force HTTPS in hosting settings if available.

**Downside:** Manual uploads on each update; no Git deploy. Fine for a one-off launch.

---

## Option D — Vercel

Repo includes `vercel.json`. Same idea as Netlify:

1. [https://vercel.com](https://vercel.com) → Import Git repo
2. Root directory `.`, no build command
3. Add domain `cotton.xyz` in Vercel → follow DNS instructions for GoDaddy (usually A + CNAME)

---

## Which option to pick?

| Situation | Pick |
|-----------|------|
| Domain on GoDaddy, want easiest + free HTTPS | **Netlify** or **Cloudflare Pages** |
| Want best DNS/CDN long-term | **Cloudflare Pages** (move nameservers) |
| Already have GoDaddy hosting plan | **Option C** (File Manager) |
| Already use Vercel | **Option D** |

---

## After deploy checklist

- [ ] `https://cotton.xyz` loads (not `http` only)
- [ ] Logo visible (checks `/assets/` path)
- [ ] Mobile layout OK
- [ ] `robots.txt` and `sitemap.xml` reachable
- [ ] Open Graph preview: [https://www.opengraph.xyz](https://www.opengraph.xyz) (optional)
- [ ] Decide `app.html` link: keep as “coming soon” static page or hide until relayer is hosted

---

## Updating the site later

**Netlify / Cloudflare / Vercel:** push to Git → auto redeploys.

**GoDaddy File Manager:** re-upload changed files.

---

## Related

- `docs/project-status.md` — full project status
- Backend / relayer hosting is **separate** (Railway, Fly.io, VPS, etc.) — not needed for landing-only launch

---

*Last updated: 27 May 2026*
