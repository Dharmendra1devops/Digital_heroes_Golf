# Digital Heroes User Guide

This guide covers the local application, account roles, page/API URLs, and the current operational limits.

## Sign-in credentials

There are **no seeded demo accounts or shared passwords** in this project. Do not put passwords, Stripe secrets, or Supabase service-role keys in this guide or source control.

- Members create their own account at `http://127.0.0.1:3000/register` using an email and password.
- The first administrator creates a staff account interactively from the repository root:

  ```powershell
  & .\.venv\Scripts\python.exe .\backend\manage.py createsuperuser
  ```

- Sign in at `http://127.0.0.1:3000/login`. The administrator uses the credentials entered during `createsuperuser`; members use their signup credentials.
- Passwords are hashed by Django. Do not share accounts between staff and members.

## Start locally

Run these in separate PowerShell terminals from the repository root. First configure `backend/.env` as described in the root [README](../README.md).

```powershell
& .\.venv\Scripts\python.exe .\backend\manage.py runserver 127.0.0.1:8000
```

```powershell
Push-Location .\frontend
npm run dev
Pop-Location
```

Open `http://127.0.0.1:3000`. The frontend sends `/api/*` through Next.js to Django, so authentication cookies remain same-origin.

## Roles and responsibilities

| Role | Who has it | What they can do |
| --- | --- | --- |
| Public visitor | Not signed in | Browse the home page, charity directory, and membership plans; register or sign in. |
| Registered member | Signed-in account without an active subscription | View the member space and choose a charity/contribution preference. Score entry and draw eligibility require an active paid subscription. |
| Subscriber | Signed-in user with an active subscription whose current period has not ended | Add/edit/delete Stableford scores (1-45; one per date; latest five retained), manage charity preference (10%-100%), view their own winnings/payout state, and submit proof for their own eligible claims. |
| Administrator | Django staff account (`is_staff`) | Manage plans, charities, draw configurations/simulations, winner verification, and payout records. Use staff credentials only. |

Admin API routes use Django's `IsAdminUser`; the browser admin pages also check the signed-in account. A normal member must receive `403` from staff operations.

## Page URLs

| URL | Purpose | Access |
| --- | --- | --- |
| `http://127.0.0.1:3000/` | Public home and product overview | Public |
| `http://127.0.0.1:3000/charities` | Search/filter the active charity directory | Public |
| `http://127.0.0.1:3000/subscribe` | Monthly/yearly plan selection and hosted checkout entry | Public to view; sign-in required to start checkout |
| `http://127.0.0.1:3000/register` | Create a member account | Public |
| `http://127.0.0.1:3000/login` | Sign in | Public |
| `http://127.0.0.1:3000/dashboard` | Scores, membership, charity selection, and winnings | Signed-in member |
| `http://127.0.0.1:3000/admin/plans` | Configure monthly/yearly Stripe plan mappings | Administrator |
| `http://127.0.0.1:3000/admin/charities` | Create/feature/activate directory entries | Administrator |
| `http://127.0.0.1:3000/admin/draws` | Configure and schedule draws; run simulations | Administrator |
| `http://127.0.0.1:3000/admin/winners` | Review proof and update payout records | Administrator |
| `http://127.0.0.1:8000/admin/` | Django model/admin console | Django staff |

The Next.js admin pages and Django admin share the path `/admin` but use different origins/ports.

## Member workflow

1. Register, then sign in.
2. View available monthly/yearly plans at `/subscribe`. Checkout redirects to Stripe only when a valid Stripe secret and matching active Stripe Price ID have been configured.
3. After Stripe confirms the subscription through a signed webhook, an active subscriber can add scores in `/dashboard`. A newer score keeps the five most recent dates; duplicate dates update the existing score.
4. Choose a charity and contribution percentage in the member space. The allowed range is 10%-100%; earlier selections remain in history.
5. Draw results and winnings appear only when real draw/winner records exist. Simulation results are not published results.
6. A winner can upload their own JPEG, PNG, or WebP proof image (maximum 10 MB). The bucket is private; an administrator reviews it.

## Administrator workflow

1. Create the initial Django superuser using the command above, then sign in through the app.
2. In `/admin/plans`, add the monthly and yearly plan amounts, currency, and corresponding Stripe Price IDs. Create the products/prices in Stripe first; never put API secrets into the Price ID field.
3. In `/admin/charities`, maintain active/featured causes. Referenced charities should be deactivated, not deleted.
4. In `/admin/draws`, create a versioned random or algorithmic configuration, review the 40%/35%/25% prize-tier split, schedule a draw and cutoff, then run a simulation. Simulations do not create payable winners.
5. In `/admin/winners`, review submitted proof. A payout can be marked paid only after winner approval and entry of a real provider payout reference.

## API URL reference

All routes below are served from `http://127.0.0.1:8000` directly or through the same-origin Next.js `/api` proxy.

| Endpoint | Purpose | Access |
| --- | --- | --- |
| `GET /api/auth/csrf/` | Set the CSRF cookie | Public |
| `POST /api/auth/register/` | Register and sign in a member | Public + CSRF |
| `POST /api/auth/login/` | Sign in by email | Public + CSRF |
| `POST /api/auth/logout/` | End the session | Signed in + CSRF |
| `GET /api/auth/me/` | Account and role/subscription summary | Signed in |
| `GET /api/scores/`, `POST /api/scores/` | List/create current user's scores | Active subscriber |
| `PATCH /api/scores/{score-id}/`, `DELETE /api/scores/{score-id}/` | Edit/delete own score | Active subscriber |
| `GET /api/charities/`, `GET /api/charities/{slug}/` | List/search/filter or view an active charity | Public |
| `GET/PUT/DELETE /api/charities/selection/` | Read/change/close own charity selection | Signed in |
| `GET/POST /api/charities/admin/`, `PATCH/DELETE /api/charities/admin/{id}/` | Manage directory entries | Administrator |
| `GET /api/subscriptions/plans/` | List active plans without exposing Stripe Price IDs | Public |
| `POST /api/subscriptions/checkout/` | Create a Stripe-hosted Checkout session | Signed in; Stripe configured |
| `GET /api/subscriptions/me/`, `POST /api/subscriptions/me/cancel/` | Read subscription or cancel at period end | Signed in; Stripe configured for cancellation |
| `GET/POST /api/subscriptions/admin/plans/`, `PATCH /api/subscriptions/admin/plans/{id}/` | Manage monthly/yearly plan mappings | Administrator |
| `GET /api/draws/` | List published draws only | Public |
| `GET/POST /api/draws/admin/configurations/`, `GET/POST /api/draws/admin/` | Manage configurations and scheduled draws | Administrator |
| `POST /api/draws/admin/{draw-id}/simulate/` | Run a non-publishing simulation | Administrator |
| `GET /api/winners/me/`, `GET/POST /api/winners/{winner-id}/proofs/` | View own claims and submit proof | Signed-in claim owner |
| `GET /api/winners/admin/`, `GET /api/winners/admin/proofs/{proof-id}/signed-url/`, `PATCH /api/winners/admin/proofs/{proof-id}/review/` | Review claims and privately inspect proof | Administrator |
| `GET/PATCH /api/winners/admin/payouts/`, `PATCH /api/winners/admin/payouts/{payout-id}/` | Review/update payouts | Administrator |
| `POST /api/payments/stripe/webhook/` | Receive signed Stripe lifecycle/invoice events | Stripe signature required |

## Configuration required before live use

- **Payments:** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and active monthly/yearly Stripe Price IDs. Checkout fails closed without them.
- **Proof storage:** `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_WINNER_PROOF_BUCKET=winner-proofs` in backend-only environment variables. The service-role key must never be sent to the browser.
- **Administrator:** At least one Django staff account must be created; no demo credentials are shipped.
- **Draws:** Create draw configurations and schedules. There is currently no publish/settlement workflow; simulations remain review-only.
- **Prize funding:** The PRD defines the 40%/35%/25% tier split, but not the overall subscription-to-prize contribution. Keep real prize funding disabled until that policy and payout provider are approved.

Never paste passwords, Stripe secrets, or the Supabase service-role key into this document, source files, or chat.
