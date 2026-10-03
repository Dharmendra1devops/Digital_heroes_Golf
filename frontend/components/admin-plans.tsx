"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";
import { ArrowRight, CreditCard, HeartHandshake, LoaderCircle, ShieldCheck } from "lucide-react";

import {
  ApiError,
  createAdminSubscriptionPlan,
  getAdminSubscriptionPlans,
  getCurrentAccount,
  updateAdminSubscriptionPlan,
  type AdminSubscriptionPlan,
  type SubscriptionPlan,
} from "@/lib/api";

function minorUnits(amount: string, currency: string) {
  const digits = new Intl.NumberFormat("en", { style: "currency", currency }).resolvedOptions().maximumFractionDigits ?? 2;
  return Math.round(Number(amount) * (10 ** digits));
}

function displayAmount(plan: AdminSubscriptionPlan) {
  const digits = new Intl.NumberFormat("en", { style: "currency", currency: plan.currency }).resolvedOptions().maximumFractionDigits ?? 2;
  return new Intl.NumberFormat("en", { style: "currency", currency: plan.currency }).format(plan.amount_minor / (10 ** digits));
}

export function AdminPlans() {
  const [plans, setPlans] = useState<AdminSubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [authorized, setAuthorized] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [interval, setInterval] = useState<SubscriptionPlan["interval"]>("monthly");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [priceId, setPriceId] = useState("");

  useEffect(() => {
    let active = true;
    getCurrentAccount()
      .then(async ({ user }) => {
        if (!active) return;
        if (!user.is_admin) return;
        setAuthorized(true);
        const records = await getAdminSubscriptionPlans();
        if (active) setPlans(records);
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof ApiError && cause.status === 403 ? "Administrator access is required." : "Plan settings are temporarily unavailable.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const plan = await createAdminSubscriptionPlan({
        interval,
        amount_minor: minorUnits(amount, currency),
        currency: currency.toUpperCase(),
        stripe_price_id: priceId.trim(),
        is_active: true,
      });
      setPlans((current) => [...current, plan].sort((left, right) => left.amount_minor - right.amount_minor));
      setAmount("");
      setPriceId("");
      setMessage(`${plan.interval} plan added.`);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The plan could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(plan: AdminSubscriptionPlan) {
    try {
      const updated = await updateAdminSubscriptionPlan(plan.id, { is_active: !plan.is_active });
      setPlans((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The plan status could not be changed.");
    }
  }

  if (loading) return <main className="dashboard-loading"><div><span className="loading-mark"><HeartHandshake size={18} /></span>Loading subscription plans…</div></main>;
  if (!authorized) return <main className="dashboard-loading"><div className="admin-denied"><ShieldCheck size={25} /><h1>Administrator access required</h1><p>{error || "This area is limited to staff accounts."}</p><Link className="button button--forest" href="/dashboard">Return to member space <ArrowRight size={15} /></Link></div></main>;

  const monthlyExists = plans.some((plan) => plan.interval === "monthly");
  const yearlyExists = plans.some((plan) => plan.interval === "yearly");

  return (
    <main className="admin-shell">
      <header className="admin-topbar">
        <Link className="brand-lockup" href="/dashboard"><span className="brand-mark"><HeartHandshake size={18} /></span><span>digital<span className="brand-lockup__light">heroes</span></span></Link>
        <nav><Link href="/admin/charities">Cause directory <ArrowRight size={14} /></Link><Link href="/admin/draws">Draw operations <ArrowRight size={14} /></Link><Link href="/subscribe" target="_blank">View plans <ArrowRight size={14} /></Link></nav>
      </header>
      <section className="admin-content">
        <div className="admin-heading">
          <div><p className="eyebrow">Administrator / billing</p><h1>Membership plans</h1><p>{plans.length} configured · managed by Stripe Price IDs</p></div>
          <span className="membership-tag membership-tag--active"><ShieldCheck size={14} /> Staff access</span>
        </div>
        {error && <p className="auth-error" role="alert">{error}</p>}
        {message && <p className="score-form__message" role="status">{message}</p>}
        <div className="admin-charity-grid">
          <section className="panel">
            <div className="panel-heading"><div><h2>Add a plan</h2><p>Checkout requires a matching active Stripe Price ID.</p></div><CreditCard className="panel-kicker" size={17} /></div>
            <form className="admin-create-form" onSubmit={handleCreate}>
              <label className="field-label" htmlFor="plan-interval">Billing interval
                <select className="field-input" id="plan-interval" value={interval} onChange={(event) => setInterval(event.target.value as SubscriptionPlan["interval"])}>
                  <option value="monthly" disabled={monthlyExists}>Monthly{monthlyExists ? " (configured)" : ""}</option>
                  <option value="yearly" disabled={yearlyExists}>Yearly{yearlyExists ? " (configured)" : ""}</option>
                </select>
              </label>
              <div className="admin-plan-amount-row">
                <label className="field-label" htmlFor="plan-amount">Amount
                  <input className="field-input" id="plan-amount" type="number" min="0.01" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} required />
                </label>
                <label className="field-label" htmlFor="plan-currency">Currency
                  <input className="field-input" id="plan-currency" minLength={3} maxLength={3} value={currency} onChange={(event) => setCurrency(event.target.value.toUpperCase())} required />
                </label>
              </div>
              <label className="field-label" htmlFor="stripe-price-id">Stripe Price ID
                <input className="field-input" id="stripe-price-id" value={priceId} onChange={(event) => setPriceId(event.target.value)} placeholder="price_…" required />
              </label>
              <button className="button button--forest" type="submit" disabled={busy || !amount || !priceId}>{busy ? <LoaderCircle className="spin" size={16} /> : <>Save plan <ArrowRight size={15} /></>}</button>
            </form>
          </section>
          <section className="panel">
            <div className="panel-heading"><div><h2>Configured plans</h2><p>Inactive plans stay available to existing subscribers.</p></div><span className="panel-kicker">{plans.length}</span></div>
            {plans.length ? <div className="admin-plan-list">{plans.map((plan) => (
              <article className="admin-plan-row" key={plan.id}>
                <div><strong>{plan.interval === "monthly" ? "Monthly" : "Yearly"}</strong><span>{displayAmount(plan)} / {plan.interval === "monthly" ? "month" : "year"}</span></div>
                <code>{plan.stripe_price_id || "No Stripe price"}</code>
                <label className="admin-check"><input type="checkbox" checked={plan.is_active} onChange={() => toggleActive(plan)} /> Active</label>
              </article>
            ))}</div> : <div className="score-empty"><CreditCard size={21} /><p>No plans configured.</p></div>}
          </section>
        </div>
      </section>
    </main>
  );
}
