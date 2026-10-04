"use client";

import { useEffect, useState } from "react";
import { ArrowDownRight, ArrowRight, ArrowUpRight, Check, CreditCard, LoaderCircle, RefreshCw, ShieldCheck } from "lucide-react";

import { ApiError, cancelMySubscription, changeMySubscriptionPlan, createCheckoutSession, getMySubscription, getSubscriptionPlans, resumeMySubscription, type MemberSubscription, type SubscriptionPlan } from "@/lib/api";

function priceLabel(plan: SubscriptionPlan) {
  const digits = new Intl.NumberFormat("en", { style: "currency", currency: plan.currency }).resolvedOptions().maximumFractionDigits ?? 2;
  return new Intl.NumberFormat("en", { style: "currency", currency: plan.currency }).format(plan.amount_minor / (10 ** digits));
}

function memberDate(value: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en", { day: "numeric", month: "long", year: "numeric" }).format(new Date(value));
}

export default function MemberMembershipPage() {
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [subscription, setSubscription] = useState<MemberSubscription | null>(null);
  const [now, setNow] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [busyPlan, setBusyPlan] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([getSubscriptionPlans(), getMySubscription()])
      .then(([availablePlans, result]) => {
        if (!active) return;
        setPlans(availablePlans);
        setSubscription(result.subscription);
        setNow(Date.now());
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : "Membership details could not be loaded.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  const currentlyActive = Boolean(
    now !== null &&
    subscription &&
    ["active", "trialing"].includes(subscription.status) &&
    subscription.current_period_end &&
    new Date(subscription.current_period_end).getTime() > now,
  );

  async function handlePlan(plan: SubscriptionPlan) {
    setBusyPlan(plan.id);
    setError("");
    setMessage("");
    try {
      if (currentlyActive) {
        if (subscription?.cancel_at_period_end) {
          setError("Resume renewal before changing your plan.");
          return;
        }
        if (!window.confirm("Switch plans now? The change takes effect immediately, and a prorated billing adjustment may apply.")) return;
        const result = await changeMySubscriptionPlan(plan.id);
        setSubscription(result.subscription);
        setMessage("Your plan has been changed. A prorated billing adjustment may apply.");
      } else {
        const result = await createCheckoutSession(plan.interval);
        window.location.assign(result.checkout_url);
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Your membership could not be changed.");
    } finally {
      setBusyPlan(null);
    }
  }

  async function handleRenewalAction(action: "cancel" | "resume") {
    if (action === "cancel" && !window.confirm("Cancel renewal? Your membership access will continue until the date shown.")) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = action === "cancel" ? await cancelMySubscription() : await resumeMySubscription();
      setSubscription(result.subscription);
      setMessage(action === "cancel" ? "Renewal cancelled. Your access remains active through the current period." : "Renewal restored. Your membership will renew at the end of the current period.");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Your renewal preference could not be updated.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <div className="member-page member-page--loading"><LoaderCircle className="spin" size={20} />Loading membership details…</div>;
  }

  return (
    <div className="member-page">
      <header className="member-page-heading">
        <div>
          <p className="eyebrow">Membership</p>
          <h1>Plan &amp; billing</h1>
          <p>Review your current access, update your plan, or manage renewal.</p>
        </div>
        <span className="member-heading-icon"><CreditCard size={22} /></span>
      </header>

      {subscription && (
        <section className="member-current-plan">
          <div className="member-current-plan__top">
            <div><span className="member-plan-kicker">Current plan</span><h2>{subscription.plan.interval === "monthly" ? "Monthly membership" : "Yearly membership"}</h2></div>
            <span className={`member-plan-status${currentlyActive ? " member-plan-status--active" : ""}`}><span />{currentlyActive ? subscription.cancel_at_period_end ? "Ending this period" : "Active" : subscription.status.replaceAll("_", " ")}</span>
          </div>
          <div className="member-current-plan__meta">
            <div><span>Billing interval</span><strong>{subscription.plan.interval === "monthly" ? "Monthly" : "Yearly"}</strong></div>
            <div><span>{subscription.cancel_at_period_end ? "Access through" : "Next renewal"}</span><strong>{memberDate(subscription.current_period_end)}</strong></div>
          </div>
          {currentlyActive && <div className="member-current-plan__actions">
            {subscription.cancel_at_period_end
              ? <button className="button button--forest button--small" type="button" disabled={busy} onClick={() => void handleRenewalAction("resume")}>{busy ? "Updating…" : <><RefreshCw size={15} /> Resume renewal</>}</button>
              : <button className="member-text-button" type="button" disabled={busy} onClick={() => void handleRenewalAction("cancel")}>{busy ? "Updating…" : <>Cancel renewal <ArrowRight size={14} /></>}</button>}
          </div>}
        </section>
      )}

      {message && <p className="member-success" role="status"><Check size={15} />{message}</p>}
      {error && <p className="auth-error" role="alert">{error}</p>}

      <div className="member-plans-heading">
        <div><h2>{currentlyActive ? "Available plans" : "Choose your membership"}</h2><p>{currentlyActive ? "Plan changes take effect immediately. A prorated billing adjustment may apply." : "Select a plan to continue to secure checkout."}</p></div>
      </div>
      {plans.length ? <div className="member-plan-grid">
        {plans.map((plan) => {
          const isCurrent = currentlyActive && subscription?.plan.id === plan.id;
          const canCheckout = plan.checkout_available;
          const direction = subscription?.plan.interval === "monthly" && plan.interval === "yearly" ? "up" : "down";
          return (
            <article className={`member-plan-card${isCurrent ? " member-plan-card--current" : ""}`} key={plan.id}>
              <div className="member-plan-card__head">
                <div><span className="member-plan-kicker">{plan.interval === "monthly" ? "Flexible billing" : "Best value"}</span><h3>{plan.interval === "monthly" ? "Monthly" : "Yearly"}</h3></div>
                {isCurrent && <span className="member-current-label">Current</span>}
              </div>
              <p className="member-plan-price">{priceLabel(plan)}<span> / {plan.interval === "monthly" ? "month" : "year"}</span></p>
              <p className="member-plan-description">Full member access, scorecard tools, and eligibility for scheduled prize draws.</p>
              <button className={`button ${isCurrent ? "button--outline" : "button--forest"} member-plan-action`} type="button" disabled={isCurrent || !canCheckout || (currentlyActive && Boolean(subscription?.cancel_at_period_end)) || busyPlan !== null} onClick={() => void handlePlan(plan)}>
                {busyPlan === plan.id ? <><LoaderCircle className="spin" size={15} /> Processing…</>
                  : isCurrent ? "Your current plan"
                    : !canCheckout ? "Not available yet"
                      : currentlyActive ? <>{direction === "up" ? <ArrowUpRight size={15} /> : <ArrowDownRight size={15} />} Switch to {plan.interval}</>
                        : <>Choose {plan.interval} <ArrowRight size={15} /></>}
              </button>
              {!canCheckout && <p className="member-plan-footnote">This plan is currently unavailable. Please contact the administrator.</p>}
            </article>
          );
        })}
      </div> : <div className="plans-empty"><CreditCard size={22} /><h2>No plans available</h2><p>An administrator must activate a membership plan first.</p></div>}
      <p className="member-billing-note"><ShieldCheck size={15} /> Plan changes take effect immediately. A prorated invoice may apply.</p>
    </div>
  );
}
