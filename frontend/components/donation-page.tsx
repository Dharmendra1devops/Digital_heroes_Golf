"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { ArrowRight, HeartHandshake, LoaderCircle, ShieldCheck } from "lucide-react";

import {
  ApiError,
  createDonationCheckout,
  getCharities,
  getDonationConfig,
  type Charity,
  type DonationConfig,
} from "@/lib/api";

function currencyDigits(currency: string) {
  return new Intl.NumberFormat("en", { style: "currency", currency })
    .resolvedOptions().maximumFractionDigits ?? 2;
}

export function DonationPage() {
  const searchParams = useSearchParams();
  const [charities, setCharities] = useState<Charity[]>([]);
  const [config, setConfig] = useState<DonationConfig | null>(null);
  const [charityId, setCharityId] = useState("");
  const [amount, setAmount] = useState("25");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const status = searchParams.get("status");
  const notice = status === "success"
    ? "Thank you. Your donation is being confirmed securely by Stripe."
    : status === "cancelled"
      ? "Checkout was cancelled. No donation was taken."
      : "";

  useEffect(() => {
    let active = true;
    Promise.all([getCharities(), getDonationConfig()])
      .then(([directory, donationConfig]) => {
        if (!active) return;
        setCharities(directory);
        setConfig(donationConfig);
        const requestedCharity = new URLSearchParams(window.location.search).get("charity");
        setCharityId(directory.some((charity) => charity.id === requestedCharity)
          ? requestedCharity ?? ""
          : directory[0]?.id ?? "");
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof ApiError ? cause.message : "Donation options could not be loaded.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!config || !charityId) return;
    setBusy(true);
    setError("");
    try {
      const amountMinor = Math.round(Number(amount) * 10 ** currencyDigits(config.currency));
      const result = await createDonationCheckout({ charity_id: charityId, amount_minor: amountMinor });
      window.location.assign(result.checkout_url);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Secure checkout could not be started.");
      setBusy(false);
    }
  }

  const minimum = config ? config.minimum_minor / 10 ** currencyDigits(config.currency) : 1;
  const maximum = config ? config.maximum_minor / 10 ** currencyDigits(config.currency) : 10000;

  return (
    <main className="donation-page">
      <header className="public-nav">
        <Link className="brand-lockup" href="/" aria-label="Digital Heroes home">
          <span className="brand-mark"><HeartHandshake size={19} /></span>
          <span>digital<span className="brand-lockup__light">heroes</span></span>
        </Link>
        <nav className="public-nav__links" aria-label="Main navigation">
          <Link href="/charities">Causes</Link>
          <Link href="/subscribe">Membership</Link>
        </nav>
        <div className="public-nav__actions">
          <Link className="nav-sign-in" href="/login">Sign in</Link>
          <Link className="button button--lime button--small" href="/register">Join the club <ArrowRight size={15} /></Link>
        </div>
      </header>

      <section className="donation-layout">
        <div className="donation-copy">
          <p className="eyebrow">Give directly</p>
          <h1>Support a cause.<br /><span>On your own terms.</span></h1>
          <p>Make a one-time donation directly to a charity in our community. It is separate from membership and does not affect draw participation.</p>
          <div className="donation-assurance"><ShieldCheck size={17} /><span>Secure, one-time checkout through Stripe. Digital Heroes does not store card details.</span></div>
        </div>

        <section className="panel donation-card" aria-labelledby="donation-title">
          <div className="panel-heading"><div><h2 id="donation-title">Make a donation</h2><p>Choose the cause and amount</p></div><HeartHandshake className="panel-kicker" size={18} /></div>
          {notice && <p className="score-form__message" role="status">{notice}</p>}
          {error && <p className="auth-error" role="alert">{error}</p>}
          {loading ? <div className="directory-empty" role="status"><LoaderCircle className="spin" size={19} /> Loading donation options…</div> : (
            <form className="admin-create-form" onSubmit={handleSubmit}>
              <label className="field-label" htmlFor="donation-charity">Choose a cause
                <select className="field-input" id="donation-charity" value={charityId} onChange={(event) => setCharityId(event.target.value)} required disabled={!charities.length}>
                  <option value="" disabled>Select a charity</option>
                  {charities.map((charity) => <option key={charity.id} value={charity.id}>{charity.name}</option>)}
                </select>
              </label>
              <label className="field-label" htmlFor="donation-amount">Donation amount ({config?.currency ?? "USD"})
                <input className="field-input" id="donation-amount" type="number" inputMode="decimal" min={minimum} max={maximum} step={1 / (10 ** (config ? currencyDigits(config.currency) : 2))} value={amount} onChange={(event) => setAmount(event.target.value)} required />
                <span className="field-hint">Minimum {minimum} · maximum {maximum} {config?.currency ?? "USD"}. You can donate without an account.</span>
              </label>
              {!charities.length && <p className="score-form__message score-form__message--error">No active causes are available for donations yet.</p>}
              {config && !config.checkout_available && <p className="draw-policy-note">Secure donations are temporarily unavailable. Please check back later.</p>}
              <button className="button button--forest" type="submit" disabled={busy || !config?.checkout_available || !charityId}>
                {busy ? <LoaderCircle className="spin" size={16} /> : <>Continue to secure checkout <ArrowRight size={16} /></>}
              </button>
            </form>
          )}
        </section>
      </section>

      <footer className="site-footer">
        <Link className="brand-lockup" href="/"><span className="brand-mark"><HeartHandshake size={18} /></span><span>digital<span className="brand-lockup__light">heroes</span></span></Link>
        <p>Golf that gives back.</p>
        <div><Link href="/charities">Explore causes</Link><span>© Digital Heroes</span></div>
      </footer>
    </main>
  );
}
