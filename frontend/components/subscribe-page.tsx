"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRight, Check, CreditCard, HeartHandshake, LoaderCircle, ShieldCheck } from "lucide-react";

import {
  ApiError,
  createCheckoutSession,
  getSubscriptionPlans,
  type SubscriptionPlan,
} from "@/lib/api";

function formatPrice(plan: SubscriptionPlan) {
  const digits = new Intl.NumberFormat("en", {
    style: "currency",
    currency: plan.currency,
  }).resolvedOptions().maximumFractionDigits ?? 2;
  return new Intl.NumberFormat("en", {
    style: "currency",
    currency: plan.currency,
    maximumFractionDigits: digits,
  }).format(plan.amount_minor / (10 ** digits));
}

export function SubscribePage({ checkoutCancelled }: { checkoutCancelled: boolean }) {
  const router = useRouter();
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyInterval, setBusyInterval] = useState<SubscriptionPlan["interval"] | null>(null);
  const [error, setError] = useState("");
  const [notice] = useState(checkoutCancelled ? "Checkout was cancelled. Your account has not been charged." : "");

  useEffect(() => {
    let active = true;
    getSubscriptionPlans()
      .then((items) => { if (active) setPlans(items); })
      .catch(() => { if (active) setError("Plans could not be loaded. Please refresh in a moment."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function startCheckout(interval: SubscriptionPlan["interval"]) {
    setBusyInterval(interval);
    setError("");
    try {
      const { checkout_url } = await createCheckoutSession(interval);
      window.location.assign(checkout_url);
    } catch (cause) {
      if (cause instanceof ApiError && (cause.status === 401 || cause.status === 403)) {
        router.push("/login?next=/subscribe");
        return;
      }
      setError(cause instanceof ApiError ? cause.message : "Checkout is temporarily unavailable.");
    } finally {
      setBusyInterval(null);
    }
  }

  const monthly = plans.find((plan) => plan.interval === "monthly");
  const yearly = plans.find((plan) => plan.interval === "yearly");

  return (
    <main className="subscribe-page">
      <header className="public-nav">
        <Link className="brand-lockup" href="/" aria-label="Digital Heroes home">
          <span className="brand-mark"><HeartHandshake size={19} /></span>
          <span>digital<span className="brand-lockup__light">heroes</span></span>
        </Link>
        <div className="public-nav__actions">
          <Link className="nav-sign-in" href="/login">Sign in</Link>
          <Link className="button button--lime button--small" href="/charities">Explore charities <ArrowRight size={15} /></Link>
        </div>
      </header>

      <section className="subscribe-hero">
        <p className="eyebrow eyebrow--light"><span className="eyebrow-dot" /> Member plans</p>
        <h1>Make your<br />round count<span>.</span></h1>
        <p>Membership brings your scorecard, monthly draw entry, and chosen cause together.</p>
      </section>

      <section className="plans-section" aria-label="Subscription plans">
        <div className="plans-intro"><div><p className="eyebrow">Choose your rhythm</p><h2>Good things, on repeat.</h2></div><span><ShieldCheck size={15} /> Secure payment by Stripe</span></div>
        {notice && <p className="score-form__message" role="status">{notice}</p>}
        {error && <p className="auth-error" role="alert">{error}</p>}
        {loading ? (
          <div className="directory-empty"><LoaderCircle className="spin" size={20} /><span>Loading plans…</span></div>
        ) : plans.length ? (
          <div className="plan-grid">
            {[monthly, yearly].filter((plan): plan is SubscriptionPlan => Boolean(plan)).map((plan) => (
              <article className={`plan-panel${plan.interval === "yearly" ? " plan-panel--featured" : ""}`} key={plan.id}>
                {plan.interval === "yearly" && <span className="plan-ribbon">Yearly</span>}
                <p className="plan-interval">{plan.interval} membership</p>
                <p className="plan-price">{formatPrice(plan)}<span> / {plan.interval === "monthly" ? "month" : "year"}</span></p>
                <p className="plan-billing">{plan.interval === "yearly" ? "Billed once each year" : "Billed monthly"}</p>
                <ul className="plan-benefits">
                  <li><Check size={15} /> Your latest five Stableford scores</li>
                  <li><Check size={15} /> Eligible for the monthly draw</li>
                  <li><Check size={15} /> Choose a charity; contribute at least 10%</li>
                </ul>
                <button className={`button ${plan.interval === "yearly" ? "button--lime" : "button--forest"} plan-button`} type="button" disabled={!plan.checkout_available || busyInterval !== null} onClick={() => startCheckout(plan.interval)}>
                  {busyInterval === plan.interval ? <LoaderCircle className="spin" size={16} /> : plan.checkout_available ? <>Continue securely <ArrowRight size={16} /></> : "Checkout not configured"}
                </button>
                {!plan.checkout_available && <p className="plan-not-ready">This plan will be available when its Stripe price is configured.</p>}
              </article>
            ))}
          </div>
        ) : (
          <div className="plans-empty">
            <CreditCard size={24} />
            <h2>Membership plans are being prepared.</h2>
            <p>Plans will appear here once pricing and secure checkout are configured.</p>
            <Link className="text-link" href="/register">Create an account <ArrowRight size={15} /></Link>
          </div>
        )}
        <p className="plans-footnote">No card details are stored by Digital Heroes. Subscription status is confirmed through Stripe webhooks.</p>
      </section>

      <footer className="site-footer">
        <Link className="brand-lockup" href="/"><span className="brand-mark"><HeartHandshake size={18} /></span><span>digital<span className="brand-lockup__light">heroes</span></span></Link>
        <p>Golf that gives back.</p>
        <div><Link href="/charities">Charity directory</Link><span>© Digital Heroes</span></div>
      </footer>
    </main>
  );
}
