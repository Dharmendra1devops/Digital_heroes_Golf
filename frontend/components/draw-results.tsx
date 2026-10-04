"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, CalendarDays, CircleDollarSign, HeartHandshake, LoaderCircle, Trophy } from "lucide-react";

import { ApiError, getPublicDraws, type DrawRecord } from "@/lib/api";

function formatScheduledAt(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatPrize(amountMinor: number, currency: string) {
  return new Intl.NumberFormat("en", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(amountMinor / 100);
}

export function DrawResults() {
  const [draws, setDraws] = useState<DrawRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getPublicDraws()
      .then((records) => { if (active) setDraws(records); })
      .catch((cause: unknown) => {
        if (active) {
          setError(cause instanceof ApiError
            ? cause.message
            : "Published results are temporarily unavailable.");
        }
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return (
    <main className="directory-page draw-results-page">
      <header className="public-nav">
        <Link className="brand-lockup" href="/" aria-label="Digital Heroes home">
          <span className="brand-mark"><HeartHandshake size={19} /></span>
          <span>digital<span className="brand-lockup__light">heroes</span></span>
        </Link>
        <nav className="public-nav__links" aria-label="Main navigation">
          <Link href="/charities">Charities</Link>
          <Link href="/#giving">The giving</Link>
          <Link href="/donate">Donate</Link>
        </nav>
        <div className="public-nav__actions">
          <Link className="nav-sign-in" href="/login">Sign in</Link>
          <Link className="button button--lime button--small" href="/subscribe">Join the club <ArrowRight size={15} /></Link>
        </div>
      </header>

      <section className="draw-results">
        <div className="draw-results__intro">
          <p className="eyebrow">Transparent by design</p>
          <h1>Every draw,<br />out in the open<span>.</span></h1>
          <p>Published results and prize pools are shown here after an administrator completes the review and publication process.</p>
        </div>
        {error && <p className="auth-error" role="alert">{error}</p>}
        {loading ? (
          <div className="directory-empty" role="status"><LoaderCircle className="spin" size={20} />Loading published results…</div>
        ) : draws.length ? (
          <div className="draw-results__list">
            {draws.map((draw) => (
              <article className="draw-results-card" key={draw.id}>
                <div className="draw-results-card__heading">
                  <span><Trophy size={19} /> Official result</span>
                  <span><CalendarDays size={15} /> {formatScheduledAt(draw.scheduled_at)}</span>
                </div>
                <h2>Winning numbers</h2>
                <div className="draw-results-card__numbers" aria-label={`Winning numbers: ${draw.winning_numbers.join(", ")}`}>
                  {draw.winning_numbers.map((number, index) => <span key={`${draw.id}-${index}`}>{number}</span>)}
                </div>
                <div className="draw-results-card__pools">
                  {draw.prize_pools.map((pool) => (
                    <div key={pool.match_count}>
                      <span>{pool.match_count}-number match</span>
                      <strong>{formatPrize(pool.available_minor, pool.currency)}</strong>
                      {pool.rollover_in_minor > 0 && <small>Includes {formatPrize(pool.rollover_in_minor, pool.currency)} rollover</small>}
                      {pool.rollover_out_minor > 0 && <small>{formatPrize(pool.rollover_out_minor, pool.currency)} jackpot rolls forward</small>}
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="directory-empty draw-results__empty">
            <CircleDollarSign size={27} />
            <h2>No published draws yet</h2>
            <p>Results will appear after a draw is simulated, reviewed, and officially published.</p>
            <Link className="text-link" href="/subscribe">Explore membership <ArrowRight size={15} /></Link>
          </div>
        )}
      </section>
      <footer className="site-footer">
        <Link className="brand-lockup" href="/"><span className="brand-mark"><HeartHandshake size={18} /></span><span>digital<span className="brand-lockup__light">heroes</span></span></Link>
        <p>Golf that gives back.</p>
        <div><Link href="/charities">Causes</Link><Link href="/login">Member sign in</Link><span>© Digital Heroes</span></div>
      </footer>
    </main>
  );
}
