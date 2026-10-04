# Digital Heroes Architecture

## Product overview

Digital Heroes combines golf score tracking, monthly draws, and charitable giving in one premium subscription platform.

## Technical stack

- Frontend: Next.js + TypeScript
- Backend: Django + Django REST Framework
- Database: PostgreSQL / Supabase
- Payments: Stripe
- File storage: Supabase Storage
- Job-demo deployment: Vercel frontend, Render backend, Supabase database; Stripe test mode only

## Backend domains

- accounts
- subscriptions
- scores
- charities
- draws
- winners
- payments
- common

## Core product rules

- Subscribers can enter and manage golf scores.
- A user may only have one score entry per date.
- Only the latest 5 scores are retained.
- Draws are monthly and can be random or algorithmic.
- The prize contribution is explicitly configured for each draw configuration; annual invoices are prorated across 12 monthly draws.
- Prize shares are fixed at 40% / 35% / 25% for 5 / 4 / 3 matches, with unclaimed 5-match funds rolling forward.
- Draw simulations are review-only; publishing atomically records funding, tier pools, winners, and pending payouts.
- Charity contribution minimum is 10%.
- Each paid subscription invoice records the selected charity share once, using the selection effective at the start of that billing period; draw publication rejects a prize-pool rate that would over-allocate alongside that charity share.
- Winners must submit proof and await admin review.
- Admin routes and approvals must be protected.
- Direct one-time donations use server-created Stripe Checkout sessions and signed webhooks; they remain separate from subscriptions.
- Member draw/winnings summaries are scoped to the authenticated user. Admin reports group financial values by currency.
- Production enables HTTPS redirects and secure cookies when `DEBUG=False`; proxy SSL trust and HSTS are explicit deployment settings.

## Design principle

The backend owns business logic. The frontend consumes APIs and focuses on user experience.

## Operational endpoints

- `GET /api/health/` performs a minimal database readiness check and returns only an `ok` or `unavailable` status.
- Staff-only account endpoints provide paginated member management and all-time analytics. Score edits reuse the same transactional five-score rule as member score entry.
- Staff can schedule cancellation or resume renewal through Stripe; the local subscription record changes only after Stripe confirms the request.
- Staff reports include recorded tier-pool amounts; because jackpot rollover is recorded in each draw's pool, this metric can count the same carried funds in multiple draw periods.
