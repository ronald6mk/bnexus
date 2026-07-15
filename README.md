# B-nexus

Professional client proposal & quote PDFs for freelancers and ICT agencies.

**Live:** https://bnexus-fggr.onrender.com  
**Repo:** https://github.com/ronald6mk/bnexus  

## Local

```bat
run.bat
```

http://127.0.0.1:8787  

## Tests

```bat
python -m pytest tests -q
```

## Deploy

Push to `master` → Render auto-deploy (Docker).  
Service: `bnexus` / `srv-d9bolcnaqgkc739q5s50`

## Env (Render)

| Name | Purpose |
|------|---------|
| `PROPOSALFORGESECRET` | App secret (also accepts `PROPOSALFORGE_SECRET`) |
| `ADMIN_PRO_EMAIL` | Optional auto-Pro email |
| `PAYMENT_LINK_PRO` / `_LIFETIME` / `_DFY` | Optional Lemon checkouts |

## Key routes

| Path | Purpose |
|------|---------|
| `/` | Marketing home |
| `/samples` | Example proposals |
| `/dfy` | Done-for-you service |
| `/status` | Human system status |
| `/api/health` | Machine health (minimal JSON) |
| `/signup` `/dashboard` `/proposals/*` | App |

## Status

**MVP complete** — see `../../docs/reports/05-PROJECT-COMPLETE.md`
