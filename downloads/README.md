# Release packages

| File | Platform |
|------|----------|
| `AHA-mac.zip` | macOS |
| `AHA-win.zip` | Windows |

## Build

```bash
chmod +x scripts/build_release_zip.sh
./scripts/build_release_zip.sh mac    # → downloads/AHA-mac.zip
./scripts/build_release_zip.sh win    # → downloads/AHA-win.zip
./scripts/build_release_zip.sh all
```

Excludes: `.venv`, `.env`, `*adminsdk*.json`, `.git`, large test assets.

## Local dev (`server.py`)

Put zips in this folder. Users download from `/download` after Google sign-in + active subscription.

## Production (Vercel)

`downloads/` is **not** deployed (see `.vercelignore`). Host zips elsewhere and set env vars:

| Variable | Example |
|----------|---------|
| `AHA_DOWNLOAD_MAC_URL` | `https://….supabase.co/storage/v1/object/public/aha-releases/AHA-mac.zip` |
| `AHA_DOWNLOAD_WIN_URL` | same for `AHA-win.zip` |

### Supabase Storage (recommended)

1. Supabase Dashboard → **Storage** → New bucket `aha-releases` → **Public**
2. Upload `AHA-mac.zip` / `AHA-win.zip`
3. Copy public URL → paste into Vercel env vars above
4. Redeploy

Check: `https://www.dailyassist.xyz/api/billing/ready` → `"downloads": {"mac": true, "win": true}`

Users still need a paid license; `/api/download/mac` redirects to your hosted zip.
