# ProposalForge

**AI/template client proposal + quote PDF generator** for freelancers and small ICT agencies.

- Complementary to **InvoiceAI** (proposals, not invoices)
- **Offline demo works without API keys** (rule-based templates)
- Optional LLM later via env — not required for MVP

## Stack

- Python 3.11+
- FastAPI + Jinja2 + static CSS
- SQLite
- PDF via `fpdf2`

## Free public website URL (for Lemon Squeezy)

`localhost` is **not** a public website. Lemon Squeezy needs an **https://** URL.

**Free option we recommend:** [Render.com](https://render.com) free web service → URL like  
`https://proposalforge-xxxx.onrender.com`

Full step-by-step: **`docs/FREE-WEBSITE-URL.md`** (in project `b1`).

Deploy helpers in this folder: `render.yaml`, `Procfile`, `Dockerfile`.

After deploy, set env vars: `PAYMENT_LINK_PRO`, `PAYMENT_LINK_LIFETIME`, `PAYMENT_LINK_DFY`.

## Quick start (Windows)

```bat
cd product\proposalforge
run.bat
```

Or manually:

```bat
cd product\proposalforge
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8787
```

Open **http://127.0.0.1:8787**

Health: **http://127.0.0.1:8787/api/health**

## Tests

```bat
cd product\proposalforge
python -m pip install -r requirements.txt
python -m pytest tests/ -v
```

## Features (MVP)

| Feature | Status |
|--------|--------|
| Landing + pricing ($0 / $15 Pro / $89 lifetime / DFY $49–$99) | Yes |
| Signup / login (PBKDF2 password hash + session cookie) | Yes |
| Dashboard of proposals | Yes |
| New proposal form (industry, services, goals, budget, brand…) | Yes |
| Offline template generator | Yes |
| Edit sections & line items | Yes |
| Branded PDF download (watermark on free) | Yes |
| Free tier: 3 proposals / calendar month | Yes |
| Pro flag removes watermark + limit | Yes |
| `GET /api/health` | Yes |
| Metrics → `ops/metrics.json` | Yes |
| PDF disclaimer: not legal advice | Yes |
| DFY order form → `data/dfy_orders.json` | Yes |

## Environment variables

| Variable | Purpose |
|----------|---------|
| `PAYMENT_LINK_PRO` | Checkout URL for $15/mo Pro (Lemon Squeezy / Stripe) |
| `PAYMENT_LINK_LIFETIME` | Checkout URL for $89 lifetime |
| `PAYMENT_LINK_DFY` | Checkout URL for DFY packages |
| `ADMIN_PRO_EMAIL` | Auto-set `is_pro=1` for this email on login/signup |
| `PRO_UNLOCK_CODE` | Demo unlock code in Settings (default: `proposalforge-pro`) |

Example (PowerShell):

```powershell
$env:PAYMENT_LINK_PRO = "https://your.lemonsqueezy.com/buy/pro"
$env:PAYMENT_LINK_LIFETIME = "https://your.lemonsqueezy.com/buy/lifetime"
$env:PAYMENT_LINK_DFY = "https://your.lemonsqueezy.com/buy/dfy"
$env:ADMIN_PRO_EMAIL = "you@agency.com"
```

### Manual Pro upgrade (SQLite)

```sql
UPDATE users SET is_pro = 1 WHERE email = 'customer@example.com';
```

DB path: `product/proposalforge/data/proposalforge.db`

## First-cash path (no payment processor required)

1. **Self-serve free → Pro later**: users hit free limit, upgrade via payment link placeholders.
2. **DFY orders**: `/dfy` form appends to `data/dfy_orders.json` with package ($49 / $99). Fulfill manually; attach real `PAYMENT_LINK_DFY` when ready.
3. **Lifetime unlock for demos**: Settings → Pro unlock code `proposalforge-pro` (or set `PRO_UNLOCK_CODE`).

## Project layout

```
product/proposalforge/
  app/
    main.py          # FastAPI routes
    db.py            # SQLite
    models.py        # constants / pricing
    generator.py     # offline composer
    pdf_export.py    # fpdf2 branded PDF
    auth.py          # sessions + password hash
    limits.py        # free tier 3/month
    metrics.py       # ops/metrics.json
  templates/         # Jinja2 HTML
  static/css/style.css
  data/              # sqlite + dfy_orders.json
  samples/           # sample proposal text
  tests/test_core.py
  requirements.txt
  run.bat
  README.md
```

## API / routes

- `GET /` — landing + pricing
- `GET|POST /signup`, `/login`, `/logout`
- `GET /dashboard`
- `GET|POST /proposals/new`
- `GET|POST /proposals/{id}` — view/edit
- `GET /proposals/{id}/pdf` — download PDF
- `GET|POST /dfy` — DFY order
- `GET|POST /settings`
- `GET /api/health`

## License / disclaimer

Software is provided as-is for business tooling demos. Generated proposals are **not legal advice** and do not create a binding contract.
