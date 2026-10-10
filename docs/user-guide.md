# Digital Heroes User Guide

This guide covers the local application, account roles, page/API URLs, and the current operational limits.

For a step-by-step explanation of account creation, member/subscriber/admin
roles, and page permissions, see [Roles, Accounts, and Access](./roles-and-access.md).

## Sign-in credentials

There are **no seeded demo accounts or shared passwords** in this project. Do not put passwords, Stripe secrets, or Supabase service-role keys in this guide or source control.

- Members create their own account at `http://localhost:3000/register` using an email and password. When active causes are listed, signup also requires a cause choice and a contribution of at least 10%; the choice can be changed later from the dashboard.
- The first administrator creates a staff account interactively from the repository root:

  ```powershell
  & .\.venv\Scripts\python.exe .\backend\manage.py createsuperuser
  ```

- Sign in at `http://localhost:3000/login`. The administrator uses the credentials entered during `createsuperuser`; members use their signup credentials.
- Administrators can also sign in at `http://localhost:3000/admin/login`. This page accepts only staff accounts; regular member accounts are signed back out and denied access.
- Passwords are hashed by Django. Do not share accounts between staff and members.
- See [Roles, Accounts, and Access](./roles-and-access.md) for all roles, account creation steps, and page/API permissions.

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

Open `http://localhost:3000`. The frontend sends `/api/*` through Next.js to Django, so authentication cookies remain same-origin.

## Roles and responsibilities

| Role | Who has it | What they can do |
| --- | --- | --- |
| Public visitor | Not signed in | Browse the home page, charity directory, and membership plans; register or sign in. |
| Registered member | Signed-in account without an active subscription | View the member space and choose a charity/contribution preference. Score entry and draw eligibility require an active paid subscription. |
| Subscriber | Signed-in user with an active subscription whose current period has not ended | Add/edit/delete Stableford scores (1-45; one per date; latest five retained), manage charity preference (10%-100%), view their own draw participation and winnings/payout state, and submit proof for their own eligible claims. |
| Administrator | Django staff account (`is_staff`) | Manage member profiles and scores, plans, charities, draw configurations/simulations/publication, winner verification, payout records, and operational reports. Use staff credentials only. |

Admin API routes use Django's `IsAdminUser`; the browser admin pages also check the signed-in account. A normal member must receive `403` from staff operations.

## Page URLs

| URL | Purpose | Access |
| --- | --- | --- |
| `http://localhost:3000/` | Public home and product overview | Public |
| `http://localhost:3000/charities` | Search/filter the active charity directory | Public |
| `http://localhost:3000/charities/{slug}` | View a cause profile, public website, and upcoming events | Public |
| `http://localhost:3000/draws` | View officially published winning numbers and prize pools | Public |
| `http://localhost:3000/donate` | Make a one-time donation independent of membership | Public; Stripe configured |
| `http://localhost:3000/subscribe` | Monthly/yearly plan selection and hosted checkout entry | Public to view; sign-in required to start checkout |
| `http://localhost:3000/register` | Create a member account | Public |
| `http://localhost:3000/login` | Sign in | Public |
| `http://localhost:3000/admin/login` | Separate staff sign-in; rejects non-staff accounts | Public form; staff account required |
| `http://localhost:3000/dashboard` | Member overview with shortcuts to each workspace area | Signed-in member |
| `http://localhost:3000/dashboard/scores` | Add, edit, and review the member scorecard | Signed-in member |
| `http://localhost:3000/dashboard/causes` | Manage the member's selected cause and contribution | Signed-in member |
| `http://localhost:3000/dashboard/winnings` | Review personal prizes, proofs, and payouts | Signed-in member |
| `http://localhost:3000/dashboard/account` | Update display name and change password | Signed-in member |
| `http://localhost:3000/dashboard/membership` | Review membership, switch plans with test-mode proration, or cancel/resume renewal | Signed-in member; Stripe test mode for billing changes |
| `http://localhost:3000/admin/plans` | Configure monthly/yearly Stripe plan mappings | Administrator |
| `http://localhost:3000/admin/charities` | Create/feature/activate directory entries | Administrator |
| `http://localhost:3000/admin/draws` | Configure, schedule, simulate, and publish draws | Administrator |
| `http://localhost:3000/admin/winners` | Review proof and update payout records | Administrator |
| `http://localhost:3000/admin/users` | Search members, update profile/access, and correct scores | Administrator |
| `http://localhost:3000/admin/reports` | View account, funding, charity, draw, and pool summaries | Administrator |
| `http://127.0.0.1:8000/admin/` | Django model/admin console | Django staff |

The Next.js admin pages and Django admin share the path `/admin` but use different origins/ports. The separate staff sign-in page is `/admin/login`; the staff dashboard pages are listed above.

## Member workflow

1. Register and, when the directory has active causes, choose a cause and contribution percentage. The default contribution is 10%; the selection can be changed later from the dashboard.
2. View available monthly/yearly plans at `/subscribe`. Checkout redirects to Stripe only when a valid Stripe secret and matching active Stripe Price ID have been configured.
3. After Stripe confirms the subscription through a signed webhook, an active subscriber can add scores in `/dashboard`. A newer score keeps the five most recent dates; submitting a date already on the scorecard is rejected, and existing scores can be changed with the edit action.
4. Review or change a charity and contribution percentage in the member space. The allowed range is 10%-100%; earlier selections remain in history.
5. Draw results and winnings appear only when real draw/winner records exist. Simulation results are not published results.
6. A winner can upload their own JPEG, PNG, or WebP proof image (maximum 10 MB). The bucket is private; an administrator reviews it.
7. A one-time donation can be made separately at `/donate`; it does not create a membership or affect draw eligibility.
8. In `/dashboard/account`, members can update their display name and change their password after confirming their current password. Email changes remain disabled because the demo does not yet include an email-verification flow.
9. In `/dashboard/membership`, members can cancel renewal and resume a pending cancellation. Switching between active plans takes effect immediately and uses Stripe test-mode proration; the demo rejects live Stripe keys.

## Administrator workflow

1. Create the initial Django superuser using the command above, then sign in through the app.
2. In `/admin/plans`, add the monthly and yearly plan amounts, currency, and corresponding Stripe Price IDs. To change an existing price, first create a new recurring Price in Stripe for the same product, then use **Edit plan** to update the amount, currency, and Stripe Price ID together. Stripe Prices are immutable; the new price must exactly match the values saved in the admin form. Never put API secrets into the Price ID field.
3. In `/admin/charities`, add/edit descriptions, public HTTPS image URLs, and active/featured status. Cause profiles appear at `/charities/{slug}`. Manage upcoming events in Django admin at `/admin/charities/charity/`; referenced charities should be deactivated, not deleted.
4. In `/admin/draws`, create a versioned random or algorithmic configuration and explicitly set its prize-pool contribution percentage. The tier split is fixed at 40% for 5 matches, 35% for 4 matches, and 25% for 3 matches. Schedule the draw and cutoff, run a simulation, review its results, then publish when ready. Annual invoices contribute one-twelfth of their value per monthly draw. Publishing creates winner and pending payout records; no payout is marked paid automatically.
5. Publish draws in schedule order. An unclaimed 5-match pool rolls into the next published draw's 5-match pool; 3- and 4-match leftovers do not roll over. Mixed-currency funding or a currency change with a carried jackpot prevents publication.
6. In `/admin/winners`, review submitted proof. A payout can be marked paid only after winner approval and entry of a real provider payout reference.
7. In `/admin/users`, search member profiles, deactivate/reactivate member access, correct a score, and cancel/resume a member's Stripe subscription at period end. Staff accounts are excluded and cannot be edited there. Billing actions are sent to Stripe; the UI never edits subscription state directly.
8. In `/admin/reports`, review all-time totals. Money is grouped by currency. Recorded tier-pool amounts include rollover carried between draws, so they are not a sum of unique cash contributions.

## Local demo walkthrough

After administrator sign-in, `/admin` is the overview for member counts, active subscriptions, recent signups, winner-review activity, pending payouts, and draw status. The shared sidebar links to the member manager, searchable subscription register, winners and payouts, draw operations, reports, plan settings, cause directory, and **System administration**. System administration opens Django Admin for the complete underlying record set, including donations, invoices, funding allocations, webhook events, score records, and charity events; sign in there with the Django administrator account if prompted. The subscription register loads member pages as needed; open a member profile to manage test-mode renewal actions.

1. From the repository root, run `& .\.venv\Scripts\python.exe .\backend\manage.py seed_demo_causes` to add two neutral cause categories. They are not real organizations or partnerships; do not invent impact claims or events.
2. Register a fresh member account and select the cause and contribution rate. Complete a test subscription, then add five eligible scores dated on or before the draw cutoff.
3. From the repository root, run `& .\.venv\Scripts\python.exe .\backend\manage.py seed_example_draw` to create an unpublished draft and its standard 5-from-45 configuration. In `/admin/draws`, create a new configuration with an approved prize contribution percentage low enough that it plus each member's charity percentage does not exceed 100%. Schedule the cutoff after the test invoice and scores, simulate, review, then publish.
4. Confirm the published numbers and pool in the public draw view and the member's dashboard. If the member wins, configure private Supabase Storage before testing proof upload and review.
5. Test independent donations from `/donate` in Stripe test mode. Confirm completed donations appear in admin reports only after their signed webhook succeeds.

The cause and example-draw commands create only their own known records; the draw remains a draft and cannot be published until a prize contribution is configured. They do not create score sets, proof-storage credentials, winner records, or payouts. Add only demo-safe content; do not imply a real charity partnership or payout.

## API URL reference

All routes below are served from `http://127.0.0.1:8000` directly or through the same-origin Next.js `/api` proxy.

| Endpoint | Purpose | Access |
| --- | --- | --- |
| `GET /api/auth/csrf/` | Set the CSRF cookie | Public |
| `POST /api/auth/register/` | Register and sign in a member | Public + CSRF |
| `POST /api/auth/login/` | Sign in by email | Public + CSRF |
| `POST /api/auth/logout/` | End the session | Signed in + CSRF |
| `GET/PATCH /api/auth/me/` | Read the signed-in account or update its display name | Signed in |
| `POST /api/auth/me/password/` | Change the signed-in member's password after current-password and Django password-policy checks | Signed in; CSRF protected |
| `GET /api/auth/admin/users/?q={search}&page={n}` | Search paginated member records | Administrator |
| `PATCH /api/auth/admin/users/{user-id}/` | Update member email/name or active status | Administrator |
| `PATCH/DELETE /api/auth/admin/users/{user-id}/scores/{score-id}/` | Correct/remove a member score while preserving score rules | Administrator |
| `GET /api/auth/admin/overview/` | Currency-separated all-time account/funding/draw summaries | Administrator |
| `GET /api/scores/`, `POST /api/scores/` | List/create current user's scores | Active subscriber |
| `PATCH /api/scores/{score-id}/`, `DELETE /api/scores/{score-id}/` | Edit/delete own score | Active subscriber |
| `GET /api/charities/`, `GET /api/charities/{slug}/` | List/search/filter or view an active charity | Public |
| `GET/PUT/DELETE /api/charities/selection/` | Read/change/close own charity selection | Signed in |
| `GET/POST /api/charities/admin/`, `PATCH/DELETE /api/charities/admin/{id}/` | Manage directory entries | Administrator |
| `GET /api/subscriptions/plans/` | List active plans without exposing Stripe Price IDs | Public |
| `POST /api/subscriptions/checkout/` | Create a Stripe-hosted Checkout session | Signed in; Stripe configured |
| `GET /api/subscriptions/me/`, `POST /api/subscriptions/me/cancel/`, `POST /api/subscriptions/me/resume/` | Read subscription or cancel/resume renewal | Signed in; Stripe test mode configured for changes |
| `POST /api/subscriptions/me/change-plan/` | Change the signed-in member's active plan immediately with prorations | Signed in; active subscription and Stripe test mode |
| `GET/POST /api/subscriptions/admin/plans/`, `PATCH /api/subscriptions/admin/plans/{id}/` | Manage monthly/yearly plan mappings | Administrator |
| `POST /api/subscriptions/admin/subscriptions/{id}/action/` | Cancel or resume an in-period member subscription through Stripe using `{"action":"cancel"}` or `{"action":"resume"}` | Administrator; Stripe test mode |
| `GET /api/draws/` | List published draws only | Public |
| `GET /api/draws/me/summary/` | Return the signed-in member's entry, upcoming-draw, winnings, and payout summary | Signed in |
| `GET/POST /api/draws/admin/configurations/`, `GET/POST /api/draws/admin/` | Manage configurations and scheduled draws | Administrator |
| `POST /api/draws/admin/{draw-id}/simulate/` | Run a non-publishing simulation | Administrator |
| `POST /api/draws/admin/{draw-id}/publish/` | Publish the latest simulation and atomically settle pools/winners | Administrator |
| `GET /api/winners/me/`, `GET/POST /api/winners/{winner-id}/proofs/` | View own claims and submit proof | Signed-in claim owner |
| `GET /api/winners/admin/`, `GET /api/winners/admin/proofs/{proof-id}/signed-url/`, `PATCH /api/winners/admin/proofs/{proof-id}/review/` | Review claims and privately inspect proof | Administrator |
| `GET/PATCH /api/winners/admin/payouts/`, `PATCH /api/winners/admin/payouts/{payout-id}/` | Review/update payouts | Administrator |
| `POST /api/payments/stripe/webhook/` | Receive signed Stripe lifecycle/invoice events | Stripe signature required |
| `GET /api/payments/donations/config/`, `POST /api/payments/donations/checkout/` | Read donation limits/configuration or create an independent one-time Checkout | Public; Stripe configured to check out |
| `GET /api/health/` | Confirm the API is running and can reach its database | Public; returns no connection details |

## Configuration required before live use

- **Payments:** `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and active monthly/yearly Stripe Price IDs. Checkout fails closed without them.
- **Direct donations:** The same Stripe keys enable `/donate`. `DONATION_CURRENCY` defaults to `USD`; the amount limits are 100 through 1,000,000 minor units. Successful payments are recognized only from signed webhooks; full refunds update the donation state.
- **Proof storage:** `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_WINNER_PROOF_BUCKET=winner-proofs` in backend-only environment variables. The service-role key must never be sent to the browser.
- **Administrator:** At least one Django staff account must be created; no demo credentials are shipped.
- **Draws:** Configure a positive prize contribution percentage for each draw configuration. Publication uses active, paid subscribers at the eligibility cutoff, and records per-invoice allocations. Ensure the selected contribution percentage and currency are approved before publishing.
- **Prize settlement:** The backend fixes the 40%/35%/25% tier split, divides each tier pool across its winners (minor-unit remainders are distributed deterministically), and carries unclaimed 5-match funds forward. Payouts remain pending until an administrator approves proof and records a provider payout reference.
- **Production security:** Set `DEBUG=False`, a unique high-entropy `SECRET_KEY`, exact `ALLOWED_HOSTS`, HTTPS `CSRF_TRUSTED_ORIGINS`, and a production `MAILER_BACKEND`/SMTP configuration. The Render blueprint enables a one-hour HSTS policy; increase it only after HTTPS is verified. Keep subdomain HSTS and preload disabled unless every affected hostname is HTTPS-ready. Enable `TRUST_PROXY_SSL_HEADER=true` only when the backend is reachable exclusively through a trusted proxy that overwrites `X-Forwarded-Proto`. Run migrations and `manage.py check --deploy` before release. Production payment, storage, domain, and deployment configuration must be supplied and tested by the project owner.

Never paste passwords, Stripe secrets, or the Supabase service-role key into this document, source files, or chat.

## Job-demo deployment (test payments only)

This deployment is an interactive portfolio/demo instance, not a live payments
service. Keep Stripe in test mode. The backend explicitly refuses `sk_live_`
keys, and the demo should use only the existing test-mode monthly/yearly Prices.

The frontend runs on Vercel and Django runs as a separate Render web service.
The current Supabase PostgreSQL database can be reused. The Stripe CLI listener
is for local development only; a deployed demo needs a Stripe **test-mode**
webhook endpoint pointing to the Render URL.

### Deploy Django on Render

1. Push the project branch to GitHub, then create a Render Blueprint from the
   repository and select the root `render.yaml`. It defines the free demo API
   service, installs dependencies, collects Django admin static files, applies
   database migrations on startup, and exposes `/api/health/`.
2. In the Render service environment, enter the existing Supabase PostgreSQL
   connection values for `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and `DB_HOST`.
   Keep the password in Render's environment settings; never add it to
   `render.yaml` or Git.
3. Set `FRONTEND_BASE_URL` to the Vercel site URL, without a trailing slash.
   Set `CSRF_TRUSTED_ORIGINS` to that exact HTTPS origin.
4. Set `STRIPE_SECRET_KEY` to the Stripe **test** secret key from the same
   account that owns the configured test Prices. It must begin with `sk_test_`;
   live keys are rejected by the app.
5. If the demo must exercise proof uploads, configure `SUPABASE_URL` and
   `SUPABASE_SERVICE_ROLE_KEY` in Render only. The service-role key must never
   be put in Vercel or browser code.

### Deploy Next.js on Vercel

1. Import the same GitHub repository into Vercel and set the project root
   directory to `frontend`.
2. Add `DJANGO_API_ORIGIN` as an environment variable for Production, Preview,
   and Development where needed. Its value is the Render API origin, such as
   `https://digital-heroes-demo-api.onrender.com`, with no trailing slash.
   Vercel deployment intentionally fails if this variable is missing.
3. Redeploy after setting the environment variable. The Next.js rewrite proxies
   `/api/*` to Django so member session cookies remain on the Vercel origin.

### Configure Stripe test webhooks

After the Render service is deployed, create a webhook destination in Stripe
**test mode** for:

```text
https://<render-host>/api/payments/stripe/webhook/
```

Subscribe to `customer.subscription.created`,
`customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`,
`invoice.payment_failed`, `checkout.session.completed`,
`checkout.session.async_payment_succeeded`,
`checkout.session.async_payment_failed`, `checkout.session.expired`, and
`charge.refunded`. Save the endpoint's `whsec_...` signing secret in Render as
`STRIPE_WEBHOOK_SECRET`; do not send it through chat or commit it.

### Create a demo administrator

Once the Render service is connected to the intended database, open its Shell
and run:

```sh
python manage.py createsuperuser
```

Use a separate demo account and a strong, unique password. Share those
credentials with the intended reviewers outside the repository. Do not create a
seeded password or commit credentials. After deployment, verify the admin sign
in, public demo pages, test checkout, and the Stripe test webhook on the live
demo URLs. Render's free service may sleep when idle and take a short time to
wake.

This setup does not turn on live payments. Do not switch to live Stripe keys or
live Prices for this job demo.
