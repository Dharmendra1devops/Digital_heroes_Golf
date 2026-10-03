# Digital Heroes Architecture

## Product overview

Digital Heroes combines golf score tracking, monthly draws, and charitable giving in one premium subscription platform.

## Technical stack

- Frontend: Next.js + TypeScript
- Backend: Django + Django REST Framework
- Database: PostgreSQL / Supabase
- Payments: Stripe
- File storage: Supabase Storage
- Deployment: Vercel frontend, separate backend deployment

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
- Prize share percentages are configurable.
- Charity contribution minimum is 10%.
- Winners must submit proof and await admin review.
- Admin routes and approvals must be protected.

## Design principle

The backend owns business logic. The frontend consumes APIs and focuses on user experience.
