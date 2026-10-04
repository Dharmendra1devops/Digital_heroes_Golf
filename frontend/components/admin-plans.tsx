"use client";

import { type FormEvent, useEffect, useState } from "react";
import { ArrowRight, Check, CreditCard, HeartHandshake, LoaderCircle, Pencil, ShieldCheck, X } from "lucide-react";

import {
  ApiError,
  createAdminSubscriptionPlan,
  getAdminSubscriptionPlans,
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
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [interval, setInterval] = useState<SubscriptionPlan["interval"]>("monthly");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [priceId, setPriceId] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editAmount, setEditAmount] = useState("");
  const [editCurrency, setEditCurrency] = useState("");
  const [editPriceId, setEditPriceId] = useState("");

  useEffect(() => {
    let active = true;
    getAdminSubscriptionPlans()
      .then((records) => { if (active) setPlans(records); })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof ApiError
          ? cause.message
          : "Plan settings are temporarily unavailable.");
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

  function startEditing(plan: AdminSubscriptionPlan) {
    const digits = new Intl.NumberFormat("en", { style: "currency", currency: plan.currency }).resolvedOptions().maximumFractionDigits ?? 2;
    setEditingId(plan.id);
    setEditAmount((plan.amount_minor / 10 ** digits).toFixed(digits));
    setEditCurrency(plan.currency);
    setEditPriceId(plan.stripe_price_id ?? "");
    setError("");
    setMessage("");
  }

  function cancelEditing() {
    setEditingId(null);
    setEditAmount("");
    setEditCurrency("");
    setEditPriceId("");
  }

  async function savePlan(event: FormEvent<HTMLFormElement>, plan: AdminSubscriptionPlan) {
    event.preventDefault();
    const normalizedCurrency = editCurrency.trim().toUpperCase();
    if (!/^[A-Z]{3}$/.test(normalizedCurrency) || !editPriceId.trim() || !Number.isFinite(Number(editAmount)) || Number(editAmount) <= 0) {
      setError("Enter a valid amount, three-letter currency code, and Stripe Price ID.");
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = await updateAdminSubscriptionPlan(plan.id, {
        amount_minor: minorUnits(editAmount, normalizedCurrency),
        currency: normalizedCurrency,
        stripe_price_id: editPriceId.trim(),
      });
      setPlans((current) => current.map((item) => item.id === updated.id ? updated : item));
      cancelEditing();
      setMessage(`${updated.interval} plan updated. Checkout now uses its saved Stripe Price ID.`);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The plan could not be updated.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <main className="dashboard-loading"><div><span className="loading-mark"><HeartHandshake size={18} /></span>Loading subscription plans…</div></main>;

  const monthlyExists = plans.some((plan) => plan.interval === "monthly");
  const yearlyExists = plans.some((plan) => plan.interval === "yearly");

  return (
    <>
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
            <p className="draw-policy-note">To change checkout pricing, create a new recurring Price in Stripe with the same billing interval, amount, and currency, then update this plan with its new Price ID. Stripe Prices cannot be edited after creation.</p>
            {plans.length ? <div className="admin-plan-list">{plans.map((plan) => (
              <article className="admin-plan-row" key={plan.id}>
                <div><strong>{plan.interval === "monthly" ? "Monthly" : "Yearly"}</strong><span>{displayAmount(plan)} / {plan.interval === "monthly" ? "month" : "year"}</span></div>
                {editingId === plan.id ? (
                  <form className="admin-plan-edit" onSubmit={(event) => savePlan(event, plan)}>
                    <label className="field-label" htmlFor={`edit-plan-amount-${plan.id}`}>Amount
                      <input className="field-input" id={`edit-plan-amount-${plan.id}`} type="number" min="0.01" step="0.01" value={editAmount} onChange={(event) => setEditAmount(event.target.value)} required />
                    </label>
                    <label className="field-label" htmlFor={`edit-plan-currency-${plan.id}`}>Currency
                      <input className="field-input" id={`edit-plan-currency-${plan.id}`} minLength={3} maxLength={3} value={editCurrency} onChange={(event) => setEditCurrency(event.target.value.toUpperCase())} required />
                    </label>
                    <label className="field-label" htmlFor={`edit-plan-price-${plan.id}`}>New Stripe Price ID
                      <input className="field-input" id={`edit-plan-price-${plan.id}`} value={editPriceId} onChange={(event) => setEditPriceId(event.target.value)} required />
                    </label>
                    <div className="admin-proof-actions">
                      <button className="button button--forest button--small" type="submit" disabled={busy}><Check size={15} /> Save changes</button>
                      <button className="button button--outline button--small" type="button" onClick={cancelEditing} disabled={busy}><X size={15} /> Cancel</button>
                    </div>
                  </form>
                ) : (
                  <>
                    <code>{plan.stripe_price_id || "No Stripe price"}</code>
                    <div className="admin-plan-actions">
                      <button className="button button--outline button--small" type="button" onClick={() => startEditing(plan)}><Pencil size={14} /> Edit plan</button>
                      <label className="admin-check"><input type="checkbox" checked={plan.is_active} onChange={() => toggleActive(plan)} /> Active</label>
                    </div>
                  </>
                )}
              </article>
            ))}</div> : <div className="score-empty"><CreditCard size={21} /><p>No plans configured.</p></div>}
          </section>
        </div>
    </>
  );
}
