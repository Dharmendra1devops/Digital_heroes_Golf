# Digital Heroes Roles, Accounts, and Access

This document explains who can use Digital Heroes, how each type of account is
created, where each user signs in, and which pages and actions are available.
For setup and full API details, see the [user guide](./user-guide.md).

## Application addresses

The URLs below are for the local development environment:

| Service | URL | Purpose |
| --- | --- | --- |
| Website | `http://localhost:3000` | Public site and member-facing pages |
| Member sign-in | `http://localhost:3000/login` | Sign in as a member or subscriber |
| Member registration | `http://localhost:3000/register` | Create a member account |
| Administrator sign-in | `http://localhost:3000/admin/login` | Separate sign-in page for staff accounts |
| Django admin | `http://127.0.0.1:8000/admin/` | Django's built-in administration console |
| API readiness | `http://127.0.0.1:8000/api/health/` | Check API/database readiness; does not sign a user in |

For a deployed environment, replace `localhost:3000` and
`127.0.0.1:8000` with the actual frontend and backend domain names.

## Account and access types

There are three signed-in account states. A visitor is not an account.

| Type | How it is obtained | Sign-in page | Access |
| --- | --- | --- | --- |
| **Visitor** | No account or sign-in required | None | Browse public pages, view active charities and plans, and use direct donation checkout when payments are configured. |
| **Member** | Register at `/register` with an email and password | `/login` | Use the dashboard, manage their own charity preference, and view their own draw/winner information. Score entry and draw eligibility are subscription-gated. |
| **Subscriber** | First register as a member; then purchase an active monthly or yearly plan after Stripe is configured and the signed Stripe webhook confirms the subscription | `/login` | Member access plus score entry and eligibility for draws when the subscription is active at the draw cutoff and the member has the required five scores. |
| **Administrator / staff** | A Django superuser is created by an operator, or an existing administrator grants staff status to a trusted account | `/admin/login` | Staff-only member management, reports, charity and plan administration, draw operations, proof review, and payout administration. |

An active subscription is a billing/access state on a member account, not a
second account or a separate username. A user can be a member without being a
subscriber.

A Django superuser created with `createsuperuser` is also marked as staff. Both are administrators
for this application; the superuser additionally has Django's full built-in
administrative permissions. Treat superuser credentials as highly privileged.

## How accounts are created

### Member account

1. Open `http://localhost:3000/register`.
2. Enter an email address, password, optional display name, and—when active causes are listed—select a cause and contribution percentage (10%-100%).
3. The site creates the account and starts a signed-in session.
4. Later, sign in at `http://localhost:3000/login` with the registered email
   and password.

There is no public administrator registration option. Public registration
creates a regular member only. Django validates and hashes passwords; never
share passwords or put them in documentation.

### Subscriber access

1. Register/sign in as a member.
2. Open `http://localhost:3000/subscribe` and choose a plan.
3. Complete hosted Stripe checkout.
4. Subscriber features activate after the backend accepts Stripe's signed
   subscription event and the subscription is active and in-period.

The plan page can be viewed without signing in, but starting checkout requires
a signed-in account. Checkout and subscription changes are unavailable until
the backend Stripe secret, webhook secret, and active plan Price IDs are
configured. A successful browser redirect alone does not grant subscriber
access; the verified webhook is authoritative.

### Administrator access

Create the initial administrator interactively from the repository root:

```powershell
& .\.venv\Scripts\python.exe .\backend\manage.py createsuperuser
```

Use the email and password entered in that command at
`http://localhost:3000/admin/login`.

For an additional administrator, an existing superuser can grant staff status
to a trusted account from `http://127.0.0.1:8000/admin/` by changing that
account's Django user permissions. Grant only the permissions the person
needs. Do not grant administrator status using ordinary public registration.

The `/admin/login` page checks the authenticated account against the backend.
If a non-staff member attempts staff sign-in, the site ends that session and
shows an administrator-access error. The sign-in page is not a substitute for
backend authorization: administrator APIs also enforce staff permissions.

## Page access by role

| Page | Visitor | Member | Subscriber | Administrator |
| --- | --- | --- | --- | --- |
| `/` | Browse | Browse | Browse | Browse |
| `/charities` | Browse active causes | Browse active causes | Browse active causes | Browse active causes |
| `/charities/{slug}` | View cause details/events | Same | Same | Same |
| `/draws` | View published results | Same | Same | Same |
| `/donate` | Start one-time donation if Stripe is configured | Same | Same | Same |
| `/subscribe` | View plans | View plans/start checkout | View plans | View plans |
| `/register` | Create a member account | Not needed | Not needed | Not needed |
| `/login` | Sign in | Sign in | Sign in | Member sign-in is available; use `/admin/login` for staff access |
| `/admin/login` | Staff sign-in form | Rejected unless account is staff | Rejected unless account is staff | Sign in to staff area |
| `/dashboard` | Must sign in | Member dashboard | Dashboard plus subscriber-gated score tools | Dashboard; administration is available separately |
| `/admin/plans` | Staff only | Staff only | Staff only | Manage membership plan/Stripe Price mappings |
| `/admin/charities` | Staff only | Staff only | Staff only | Manage active causes and directory content |
| `/admin/draws` | Staff only | Staff only | Staff only | Configure, schedule, simulate, and publish draws |
| `/admin/winners` | Staff only | Staff only | Staff only | Review winner proof and manage payouts |
| `/admin/users` | Staff only | Staff only | Staff only | Search members, update member profile/access, correct/remove scores, and manage Stripe subscription renewal |
| `/admin/reports` | Staff only | Staff only | Staff only | View account, funding, charity, draw, and pool summaries |
| `http://127.0.0.1:8000/admin/` | Django staff only | Django staff only | Django staff only | Django administration, based on assigned Django permissions |

The member dashboard is for signed-in accounts. Having dashboard access does
not mean every feature is available: score changes and draw eligibility require
an active subscription, and draw entry also depends on the configured cutoff
and score requirements.

## What each signed-in user can do

### Member

- View and update their own charity choice and contribution preference.
- View their own account/subscription information, draw summary, and any own
  winner or payout records.
- Start monthly/yearly Stripe checkout when payment configuration is available.
- Make an optional direct one-time donation; it is separate from membership.
- Cannot manage another account, administer draws, approve proof, or edit
  payout records.

### Subscriber

Subscribers retain all member capabilities and, while their subscription is
active and within its current period, can:

- Add, edit, and remove their own Stableford scores from 1 to 45.
- Keep at most the five most recent dated scores; there is one score per date.
- Qualify for a draw only when all server-side eligibility rules are met.
- Request cancellation of renewal through the billing flow where Stripe is
  configured. Access normally continues until the current paid period ends.

Subscription status is synchronized from Stripe. Administrators should not
manually change local billing state to simulate a payment.

### Administrator / staff

- Configure subscription plans and their Stripe Price IDs.
- Edit the displayed plan amount/currency and point checkout to a replacement Stripe Price ID. Stripe price objects are immutable, so create the matching recurring Price in Stripe first.
- Create and manage charities and their directory information.
- Configure and schedule draws, run simulations, review, and publish results.
- Search and manage non-staff member profiles and scores.
- Review submitted proof and update winner verification.
- Record payout outcomes and provider references after approval.
- Review operational reports.

Staff management excludes staff and superuser accounts from member editing.
Stripe manages billing state. Django's built-in admin is separately controlled
by each account's Django permissions.

## Relevant API access rules

The frontend sends API calls through the same-origin `/api/` proxy. The backend
is the authority for permissions; hiding a page or button does not grant or
revoke API access.

| API area | Access rule |
| --- | --- |
| `/api/auth/register/`, `/api/auth/login/` | Public requests with CSRF protection; registration creates a member |
| `/api/auth/me/`, `/api/auth/logout/` | Signed-in user; account data is limited to the current user |
| `/api/scores/` | Current user with an active subscription |
| `/api/charities/` and `/api/subscriptions/plans/` | Public read access |
| `/api/charities/selection/`, `/api/subscriptions/me/`, `/api/draws/me/summary/`, `/api/winners/me/` | Signed-in current user; records are scoped to that user |
| `/api/subscriptions/checkout/`, `/api/subscriptions/me/cancel/` | Signed-in current user; Stripe must be configured for payment actions |
| `/api/payments/donations/config/`, `/api/payments/donations/checkout/` | Public; checkout requires Stripe configuration |
| `/api/charities/admin/`, `/api/subscriptions/admin/`, `/api/draws/admin/`, `/api/auth/admin/`, `/api/winners/admin/` | Staff account |
| `/api/payments/stripe/webhook/` | Stripe-signed event only; not a user sign-in route |
| `/api/health/` | Public readiness status; no user data or credentials |

For the complete endpoint list, including methods and purposes, see the API
reference in the [user guide](./user-guide.md).

## Sign out and account protection

- Use **Sign out** in the dashboard sidebar to end the web session.
- Use a unique password and do not share member or staff accounts.
- Keep staff and superuser credentials private; use a password manager rather
  than a Markdown file.
- Never put `SECRET_KEY`, database passwords, Stripe secrets, or Supabase
  service-role keys in browser code or public documentation.
- If a member is deactivated in staff member management, that account cannot
  sign in. Deactivation does not change its Stripe subscription.
