"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";
import {
  Activity, ArrowRight, CalendarDays, ChartNoAxesColumnIncreasing, CircleHelp,
  CreditCard, HeartHandshake, LoaderCircle, Plus, ShieldCheck,
  Trophy, Trash2, Upload, X,
} from "lucide-react";

import { useMemberAccount } from "@/components/member-workspace";
import {
  ApiError,
  createScore,
  getCharities,
  getCharitySelection,
  getMyDrawSummary,
  getMyWinners,
  getMySubscription,
  getScores,
  removeScore,
  saveCharitySelection,
  uploadWinnerProof,
  updateScore,
  type Charity,
  type CharitySelection,
  type GolfScore,
  type MemberWinner,
  type MemberDrawSummary,
  type MemberSubscription,
} from "@/lib/api";

function localDateValue() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function displayDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function displayMoney(amountMinor: number, currency: string) {
  const digits = new Intl.NumberFormat("en", { style: "currency", currency }).resolvedOptions().maximumFractionDigits ?? 2;
  return new Intl.NumberFormat("en", { style: "currency", currency }).format(amountMinor / (10 ** digits));
}

type MemberDashboardPage = "overview" | "scores" | "causes" | "winnings";

const pageHeadings: Record<Exclude<MemberDashboardPage, "overview">, { eyebrow: string; title: string; description: string }> = {
  scores: {
    eyebrow: "Your golf activity",
    title: "My scorecard",
    description: "Add, review, and maintain your latest Stableford rounds.",
  },
  causes: {
    eyebrow: "Giving back",
    title: "My cause",
    description: "Choose the cause you support and set your contribution preference.",
  },
  winnings: {
    eyebrow: "Your prize history",
    title: "Winnings & payouts",
    description: "Review verified prizes, submit proof, and follow payout progress.",
  },
};

export function MemberDashboard({ page = "overview" }: { page?: MemberDashboardPage }) {
  const { account } = useMemberAccount();
  const [subscription, setSubscription] = useState<MemberSubscription | null>(null);
  const [scores, setScores] = useState<GolfScore[]>([]);
  const [winners, setWinners] = useState<MemberWinner[]>([]);
  const [drawSummary, setDrawSummary] = useState<MemberDrawSummary | null>(null);
  const [proofFiles, setProofFiles] = useState<Record<string, File>>({});
  const [proofBusyId, setProofBusyId] = useState<string | null>(null);
  const [proofError, setProofError] = useState("");
  const [proofMessage, setProofMessage] = useState("");
  const [charities, setCharities] = useState<Charity[]>([]);
  const [charitySelection, setCharitySelection] = useState<CharitySelection | null>(null);
  const [selectedCharityId, setSelectedCharityId] = useState("");
  const [contributionPercent, setContributionPercent] = useState("10");
  const [charityBusy, setCharityBusy] = useState(false);
  const [charityMessage, setCharityMessage] = useState("");
  const [charityError, setCharityError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [scoreDate, setScoreDate] = useState(localDateValue);
  const [scoreValue, setScoreValue] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [formMessage, setFormMessage] = useState("");
  const [formError, setFormError] = useState("");

  useEffect(() => {
    let active = true;
    async function loadPageData() {
      try {
        if (page === "overview") {
          const [subscriptionResult, memberSummary] = await Promise.all([
            getMySubscription(),
            getMyDrawSummary(),
          ]);
          if (!active) return;
          setSubscription(subscriptionResult.subscription);
          setDrawSummary(memberSummary);
          if (account.is_subscriber) {
            const entries = await getScores();
            if (active) setScores(entries);
          }
        } else if (page === "scores") {
          const subscriptionResult = await getMySubscription();
          if (!active) return;
          setSubscription(subscriptionResult.subscription);
          if (account.is_subscriber) {
            const entries = await getScores();
            if (active) setScores(entries);
          }
        } else if (page === "causes") {
          const [directory, selectionResult] = await Promise.all([
            getCharities(),
            getCharitySelection(),
          ]);
          if (!active) return;
          setCharities(directory);
          setCharitySelection(selectionResult.selection);
          setSelectedCharityId(selectionResult.selection?.charity.id ?? "");
          if (selectionResult.selection) setContributionPercent(String(selectionResult.selection.contribution_bps / 100));
        } else {
          const [winnerRecords, memberSummary] = await Promise.all([
            getMyWinners(),
            getMyDrawSummary(),
          ]);
          if (!active) return;
          setWinners(winnerRecords);
          setDrawSummary(memberSummary);
        }
      } catch {
        if (!active) return;
        setFormError("We could not load your member space. Please refresh and try again.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadPageData();
    return () => { active = false; };
  }, [account.is_subscriber, page]);

  useEffect(() => {
    if (!loading && window.location.hash) {
      const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
      document.getElementById(window.location.hash.slice(1))?.scrollIntoView({ behavior });
    }
  }, [loading]);

  async function handleScoreSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setFormError("");
    setFormMessage("");
    try {
      if (editingId) {
        await updateScore(editingId, { score: Number(scoreValue) });
        setFormMessage("Round updated.");
      } else {
        await createScore({ score_date: scoreDate, score: Number(scoreValue) });
        setFormMessage("Round added to your scorecard.");
      }
      setScores(await getScores());
      setEditingId(null);
      setScoreValue("");
      setScoreDate(localDateValue());
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The round could not be saved. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function handleCharitySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCharityBusy(true);
    setCharityError("");
    setCharityMessage("");
    try {
      const result = await saveCharitySelection({
        charity_id: selectedCharityId,
        contribution_bps: Math.round(Number(contributionPercent) * 100),
      });
      setCharitySelection(result.selection);
      setCharityMessage("Your cause preference is saved.");
    } catch (error) {
      setCharityError(error instanceof ApiError ? error.message : "Your cause preference could not be saved.");
    } finally {
      setCharityBusy(false);
    }
  }

  async function handleProofUpload(winnerId: string) {
    const file = proofFiles[winnerId];
    if (!file) return;
    setProofBusyId(winnerId);
    setProofError("");
    setProofMessage("");
    try {
      const proof = await uploadWinnerProof(winnerId, file);
      setWinners((current) => current.map((winner) => winner.id === winnerId ? { ...winner, proofs: [proof, ...winner.proofs] } : winner));
      setProofFiles((current) => { const next = { ...current }; delete next[winnerId]; return next; });
      setProofMessage("Proof submitted for review.");
    } catch (error) {
      setProofError(error instanceof ApiError ? error.message : "Proof could not be submitted.");
    } finally {
      setProofBusyId(null);
    }
  }

  function startEditing(score: GolfScore) {
    setEditingId(score.id);
    setScoreDate(score.score_date);
    setScoreValue(String(score.score));
    setFormError("");
    setFormMessage("");
  }

  function cancelEditing() {
    setEditingId(null);
    setScoreDate(localDateValue());
    setScoreValue("");
    setFormError("");
    setFormMessage("");
  }

  async function handleDelete(id: string) {
    setBusy(true);
    try {
      await removeScore(id);
      setScores((current) => current.filter((item) => item.id !== id));
      setConfirmDeleteId(null);
      if (editingId === id) cancelEditing();
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The round could not be removed.");
    } finally {
      setBusy(false);
    }
  }

  const average = scores.length
    ? (scores.reduce((total, item) => total + item.score, 0) / scores.length).toFixed(1)
    : "—";
  const firstName = account.display_name.trim().split(/\s+/)[0] || account.email.split("@")[0];

  if (loading) {
    const loadingLabel = {
      overview: "Loading your overview",
      scores: "Loading your scorecard",
      causes: "Loading your cause settings",
      winnings: "Loading your prize history",
    }[page];
    return (
      <div className="member-overview">
        {page === "overview" ? (
          <section className="member-hero">
            <div className="member-hero__copy">
              <p className="eyebrow eyebrow--light">Your member space</p>
              <h1>Good to see you, {firstName}.</h1>
              <p>Your next round can do a little more. Keep your scores current and your cause close.</p>
            </div>
            <span className="member-hero__marker"><HeartHandshake size={36} /></span>
          </section>
        ) : (
          <header className="member-page-heading member-dashboard-page-heading">
            <div>
              <p className="eyebrow">{pageHeadings[page].eyebrow}</p>
              <h1>{pageHeadings[page].title}</h1>
              <p>{pageHeadings[page].description}</p>
            </div>
            <span className="member-heading-icon">
              {page === "scores" ? <ChartNoAxesColumnIncreasing size={22} /> : page === "causes" ? <HeartHandshake size={22} /> : <Trophy size={22} />}
            </span>
          </header>
        )}
        <div className="member-data-loading" role="status" aria-label={loadingLabel}>
          <span className="member-sr-only">{loadingLabel}</span>
          <div className="member-data-loading__skeleton" aria-hidden="true">
            <span /><span /><span />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div id="overview" className="member-overview">
      {page !== "overview" && (
        <header className="member-page-heading member-dashboard-page-heading">
          <div>
            <p className="eyebrow">{pageHeadings[page].eyebrow}</p>
            <h1>{pageHeadings[page].title}</h1>
            <p>{pageHeadings[page].description}</p>
          </div>
          <span className="member-heading-icon">
            {page === "scores" ? <ChartNoAxesColumnIncreasing size={22} /> : page === "causes" ? <HeartHandshake size={22} /> : <Trophy size={22} />}
          </span>
        </header>
      )}
      {page === "overview" && <>
        <section className="member-hero">
          <div className="member-hero__copy">
            <p className="eyebrow eyebrow--light">Your member space</p>
            <h1>Good to see you, {firstName}.</h1>
            <p>Your next round can do a little more. Keep your scores current and your cause close.</p>
          </div>
          <span className="member-hero__marker"><HeartHandshake size={36} /></span>
        </section>

        <section className="summary-strip" aria-label="Score summary">
          <div className="summary-cell"><span>Rounds on record</span><strong>{scores.length} <small>/ 5</small></strong></div>
          <div className="summary-cell"><span>Stableford average</span><strong>{average}</strong></div>
          <div className="summary-cell"><span>Latest round</span><strong>{scores[0] ? displayDate(scores[0].score_date) : "—"}</strong></div>
          <div className="summary-cell"><span>Draws entered</span><strong>{drawSummary?.draws_entered ?? "—"}</strong></div>
          <div className="summary-cell"><span>Prize status</span><strong>{drawSummary?.payouts_by_status.filter((item) => item.status === "pending").reduce((total, item) => total + item.count, 0) ?? "—"} <small>pending</small></strong></div>
        </section>

        <nav className="member-quick-nav" aria-label="Member workspace shortcuts">
          <Link href="/dashboard/scores"><ChartNoAxesColumnIncreasing size={18} /><span><strong>My scorecard</strong><small>Manage your latest rounds</small></span><ArrowRight size={15} /></Link>
          <Link href="/dashboard/causes"><HeartHandshake size={18} /><span><strong>My cause</strong><small>Choose where you give back</small></span><ArrowRight size={15} /></Link>
          <Link href="/dashboard/winnings"><Trophy size={18} /><span><strong>Winnings</strong><small>Review prizes and payouts</small></span><ArrowRight size={15} /></Link>
        </nav>

        <section className="panel participation-panel" aria-labelledby="participation-heading">
          <div className="panel-heading"><div><h2 id="participation-heading">Draw participation</h2><p>Upcoming draws and your entry status</p></div><CalendarDays className="panel-kicker" size={17} /></div>
          <p className="draw-policy-note">Entries are recorded when a draw is simulated. Eligibility requires an active membership and five scores by the draw cutoff.</p>
          {drawSummary?.upcoming_draws.length ? <div className="score-list">{drawSummary.upcoming_draws.map((draw) => (
            <div className="score-row" key={draw.id}>
              <span className="score-row__date">{new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(draw.scheduled_at))}</span>
              <span className={`draw-status draw-status--${draw.entered ? "published" : "draft"}`}>{draw.entered ? "Entry confirmed" : "Entry not recorded"}</span>
            </div>
          ))}</div> : <div className="score-empty"><CalendarDays size={21} /><p>No upcoming draws are scheduled.</p></div>}
        </section>

        <section className="panel membership-panel" id="membership">
          <div className="panel-heading"><div><h2>Membership</h2><p>Billing and access status</p></div><CreditCard className="panel-kicker" size={17} /></div>
          {subscription ? <div className="membership-details">
            <div><span>Plan</span><strong>{subscription.plan.interval === "monthly" ? "Monthly" : "Yearly"}</strong></div>
            <div><span>Status</span><strong className="membership-status">{subscription.cancel_at_period_end ? "Cancels at period end" : subscription.status}</strong></div>
            <div><span>{subscription.cancel_at_period_end ? "Access through" : "Renews"}</span><strong>{subscription.plan && subscription.current_period_end ? displayDate(subscription.current_period_end.slice(0, 10)) : "—"}</strong></div>
          </div> : <div className="membership-empty"><p>No active plan is linked to this account.</p><Link className="text-link" href="/subscribe">View plans <ArrowRight size={14} /></Link></div>}
          <Link className="text-link member-section-link" href="/dashboard/membership">Manage membership <ArrowRight size={14} /></Link>
        </section>

        {!account.is_subscriber && (
          <section className="gate-banner">
            <CreditCard size={19} />
            <div><h2>An active membership opens score entry and draw participation.</h2><p>Your account is ready. <Link href="/subscribe">View membership plans <ArrowRight size={14} /></Link></p></div>
          </section>
        )}

        {formError && !account.is_subscriber && <p className="auth-error" role="alert">{formError}</p>}
      </>}

      {page === "scores" && <>
        <section className="summary-strip member-page-summary" aria-label="Score summary">
          <div className="summary-cell"><span>Rounds on record</span><strong>{scores.length} <small>/ 5</small></strong></div>
          <div className="summary-cell"><span>Stableford average</span><strong>{average}</strong></div>
          <div className="summary-cell"><span>Latest round</span><strong>{scores[0] ? displayDate(scores[0].score_date) : "—"}</strong></div>
        </section>
        {!account.is_subscriber && (
          <section className="gate-banner">
            <CreditCard size={19} />
            <div><h2>An active membership opens score entry and draw participation.</h2><p>Your account is ready. <Link href="/dashboard/membership">Manage membership <ArrowRight size={14} /></Link></p></div>
          </section>
        )}
        {formError && <p className="auth-error" role="alert">{formError}</p>}
        <section className="dashboard-grid" id="scorecard">
          <div className="panel">
            <div className="panel-heading">
              <div><h2>{editingId ? "Edit this round" : "Add a round"}</h2><p>Stableford format · 1 to 45</p></div>
              {editingId ? <button className="icon-action" type="button" onClick={cancelEditing} title="Cancel edit" aria-label="Cancel edit"><X size={17} /></button> : <Plus className="panel-kicker" size={17} />}
            </div>
            <form className="score-form" onSubmit={handleScoreSubmit}>
              <fieldset disabled={!account.is_subscriber || busy}>
                <div className="score-form__row">
                  <label className="field-label" htmlFor="score-date">Round date
                    <span className="date-input-wrap"><CalendarDays size={15} /><input className="field-input" id="score-date" type="date" required value={scoreDate} readOnly={Boolean(editingId)} onChange={(event) => setScoreDate(event.target.value)} /></span>
                  </label>
                  <label className="field-label" htmlFor="score-value">Stableford
                    <input className="field-input" id="score-value" type="number" inputMode="numeric" min={1} max={45} step={1} required value={scoreValue} onChange={(event) => setScoreValue(event.target.value)} placeholder="34" />
                  </label>
                </div>
                <p className="score-form__hint">One score per date. Saving a newer round keeps your latest five.</p>
                <button className="button button--forest" type="submit" disabled={busy || !scoreDate || !scoreValue}>
                  {busy ? <LoaderCircle className="spin" size={16} /> : <>{editingId ? "Update round" : "Save round"} <ArrowRight size={16} /></>}
                </button>
              </fieldset>
              {formMessage && <p className="score-form__message" role="status">{formMessage}</p>}
              {formError && account.is_subscriber && <p className="score-form__message score-form__message--error" role="alert">{formError}</p>}
            </form>
          </div>

          <div className="panel">
            <div className="panel-heading">
              <div><h2>Your latest rounds</h2><p>Most recent first · maximum five</p></div>
              <span className="panel-kicker">{scores.length} / 5</span>
            </div>
            {scores.length ? (
              <div className="score-list">
                {scores.map((score, index) => (
                  <div className="score-row" key={score.id}>
                    <span className="score-row__index">{String(index + 1).padStart(2, "0")}</span>
                    <span className="score-row__date">{displayDate(score.score_date)}</span>
                    <span className="score-row__number">{score.score}</span>
                    {confirmDeleteId === score.id ? (
                      <span className="inline-confirm"><span>Remove?</span><button type="button" disabled={busy} onClick={() => handleDelete(score.id)}>Yes</button><button type="button" onClick={() => setConfirmDeleteId(null)}>No</button></span>
                    ) : (
                      <span className="score-row__actions">
                        <button className="icon-action" type="button" onClick={() => startEditing(score)} aria-label={`Edit score from ${displayDate(score.score_date)}`} title="Edit round"><Activity size={15} /></button>
                        <button className="icon-action icon-action--danger" type="button" onClick={() => setConfirmDeleteId(score.id)} aria-label={`Delete score from ${displayDate(score.score_date)}`} title="Delete round"><Trash2 size={15} /></button>
                      </span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="score-empty">
                {account.is_subscriber ? <><ChartNoAxesColumnIncreasing size={22} /><p>Your scorecard is waiting for its first round.</p></> : <><ShieldCheck size={22} /><p>Your scorecard will be ready when your membership is active.</p></>}
              </div>
            )}
          </div>
        </section>
      </>}

      {page === "causes" && <section className="panel charity-panel member-feature-panel" id="charity-choice">
          <div className="panel-heading">
            <div><h2>Your cause</h2><p>At least 10% of your subscription goes to the charity you choose.</p></div>
            {charitySelection && <span className="membership-tag membership-tag--active">Preference saved</span>}
          </div>
          {charities.length ? (
            <form className="charity-selection-form" onSubmit={handleCharitySubmit}>
              <label className="field-label" htmlFor="selected-charity">Choose a charity
                <select className="field-input" id="selected-charity" value={selectedCharityId} onChange={(event) => setSelectedCharityId(event.target.value)} required>
                  <option value="" disabled>Select a cause</option>
                  {charities.map((charity) => <option value={charity.id} key={charity.id}>{charity.name}</option>)}
                </select>
              </label>
              <label className="field-label" htmlFor="contribution-percent">Contribution
                <span className="percent-input-wrap"><input className="field-input" id="contribution-percent" type="number" min={10} max={100} step={1} value={contributionPercent} onChange={(event) => setContributionPercent(event.target.value)} required /><span>%</span></span>
              </label>
              <button className="button button--forest" type="submit" disabled={charityBusy || !selectedCharityId}>
                {charityBusy ? <LoaderCircle className="spin" size={16} /> : <>Save cause <ArrowRight size={16} /></>}
              </button>
              {charityMessage && <p className="score-form__message" role="status">{charityMessage}</p>}
              {charityError && <p className="score-form__message score-form__message--error" role="alert">{charityError}</p>}
            </form>
          ) : (
            <div className="charity-empty"><HeartHandshake size={21} /><p>No active charities are listed yet.</p><Link href="/charities">Browse the directory <ArrowRight size={14} /></Link></div>
          )}
      </section>}

      {page === "winnings" && <section className="panel winnings-panel member-feature-panel" id="winnings">
          <div className="panel-heading"><div><h2>Your winnings</h2><p>Verified prizes and payment status</p></div><Trophy className="panel-kicker" size={18} /></div>
          {drawSummary?.winnings_by_currency.length ? <div className="summary-strip" aria-label="Winnings totals">{drawSummary.winnings_by_currency.map((item) => <div className="summary-cell" key={item.currency}><span>Total awarded · {item.currency}</span><strong>{displayMoney(item.amount_minor, item.currency)}</strong></div>)}</div> : null}
          {proofMessage && <p className="score-form__message" role="status">{proofMessage}</p>}
          {proofError && <p className="score-form__message score-form__message--error" role="alert">{proofError}</p>}
          {winners.length ? <div className="winner-list">{winners.map((winner) => (
            <article className="winner-row" key={winner.id}>
              <div className="winner-row__summary"><span className="winner-match">{winner.match_count}</span><div><strong>{displayMoney(winner.prize_amount_minor, winner.currency)}</strong><span>{winner.match_count}-match prize · {winner.verification_status}</span></div></div>
              <div className="winner-row__details">
                {winner.proofs.map((proof) => <span className={`draw-status draw-status--${proof.review_status}`} key={proof.id}>Proof {proof.review_status}</span>)}
                {winner.payouts.map((payout) => <span className={`draw-status draw-status--${payout.status}`} key={payout.id}>Payout {payout.status}{payout.paid_at ? ` · ${displayDate(payout.paid_at.slice(0, 10))}` : ""}</span>)}
              </div>
              {winner.verification_status !== "approved" && <form className="winner-proof-form" onSubmit={(event) => { event.preventDefault(); void handleProofUpload(winner.id); }}>
                <label className="field-label" htmlFor={`proof-${winner.id}`}>Golf score proof
                  <input className="field-input" id={`proof-${winner.id}`} type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => { const file = event.target.files?.[0]; if (file) setProofFiles((current) => ({ ...current, [winner.id]: file })); }} />
                </label>
                <button className="button button--forest button--small" type="submit" disabled={!proofFiles[winner.id] || proofBusyId === winner.id}>{proofBusyId === winner.id ? <LoaderCircle className="spin" size={15} /> : <>Submit proof <Upload size={15} /></>}</button>
              </form>}
            </article>
          ))}</div> : <div className="score-empty"><Trophy size={21} /><p>No winnings to show yet.</p></div>}
      </section>}

      {page === "overview" && <>
        <p className="dashboard-footnote"><CircleHelp size={14} /> Need a hand? <Link href="/#how-it-works">See how Digital Heroes works <ArrowRight size={14} /></Link><span className="desktop-only"> · {account.is_admin ? "Administrator account" : "Member account"}</span></p>
      </>}
    </div>
  );
}
