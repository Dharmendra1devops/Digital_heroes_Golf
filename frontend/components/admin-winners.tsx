"use client";

import { useEffect, useState } from "react";
import { ExternalLink, HeartHandshake, LoaderCircle, ShieldCheck, Trophy } from "lucide-react";

import {
  ApiError,
  getAdminPayouts,
  getAdminProofUrl,
  getAdminWinners,
  reviewWinnerProof,
  updateAdminPayout,
  type AdminPayout,
  type MemberWinner,
} from "@/lib/api";

function displayMoney(amountMinor: number, currency: string) {
  const digits = new Intl.NumberFormat("en", { style: "currency", currency }).resolvedOptions().maximumFractionDigits ?? 2;
  return new Intl.NumberFormat("en", { style: "currency", currency }).format(amountMinor / (10 ** digits));
}

function displayDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function AdminWinners() {
  const [winners, setWinners] = useState<MemberWinner[]>([]);
  const [payouts, setPayouts] = useState<AdminPayout[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"verification" | "payouts">("verification");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const [providerRefs, setProviderRefs] = useState<Record<string, string>>({});

  async function loadData() {
    const [winnerRecords, payoutRecords] = await Promise.all([getAdminWinners(), getAdminPayouts()]);
    setWinners(winnerRecords);
    setPayouts(payoutRecords);
  }

  useEffect(() => {
    let active = true;
    Promise.all([getAdminWinners(), getAdminPayouts()])
      .then(([winnerRecords, payoutRecords]) => {
        if (!active) return;
        setWinners(winnerRecords);
        setPayouts(payoutRecords);
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof ApiError && cause.status === 403 ? "Administrator access is required." : "Winner operations are temporarily unavailable.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function previewProof(proofId: string) {
    setBusyId(proofId);
    setError("");
    try {
      const { signed_url } = await getAdminProofUrl(proofId);
      window.location.assign(signed_url);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The private proof could not be opened.");
    } finally {
      setBusyId(null);
    }
  }

  async function review(proofId: string, status: "approved" | "rejected") {
    setBusyId(proofId);
    setError("");
    setMessage("");
    try {
      await reviewWinnerProof(proofId, status, reviewNote);
      await loadData();
      setReviewNote("");
      setMessage(`Proof ${status}.`);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The proof review could not be saved.");
    } finally {
      setBusyId(null);
    }
  }

  async function updatePayout(payout: AdminPayout, status: "paid" | "failed") {
    setBusyId(payout.id);
    setError("");
    setMessage("");
    try {
      const updated = await updateAdminPayout(payout.id, status === "paid"
        ? { status, provider_payout_id: providerRefs[payout.id] ?? "" }
        : { status, failure_reason: "Marked failed by administrator." });
      setPayouts((current) => current.map((item) => item.id === updated.id ? updated : item));
      setMessage(status === "paid" ? "Payout marked paid with provider reference." : "Payout marked failed.");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The payout status could not be updated.");
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <main className="dashboard-loading"><div><span className="loading-mark"><HeartHandshake size={18} /></span>Loading winner operations…</div></main>;

  const pendingWinners = winners.filter((winner) => winner.verification_status !== "approved");
  const pendingPayouts = payouts.filter((payout) => payout.status === "pending");

  return (
    <>
        <div className="admin-heading"><div><p className="eyebrow">Administrator / rewards</p><h1>Winners & payouts</h1><p>{pendingWinners.length} claims to review · {pendingPayouts.length} pending payouts</p></div><span className="membership-tag membership-tag--active"><ShieldCheck size={14} /> Staff access</span></div>
        {error && <p className="auth-error" role="alert">{error}</p>}
        {message && <p className="score-form__message" role="status">{message}</p>}
        <div className="directory-filters admin-tabs" role="tablist" aria-label="Winner operations">
          <button className={tab === "verification" ? "is-selected" : ""} type="button" role="tab" aria-selected={tab === "verification"} onClick={() => setTab("verification")}>Verification <span>{pendingWinners.length}</span></button>
          <button className={tab === "payouts" ? "is-selected" : ""} type="button" role="tab" aria-selected={tab === "payouts"} onClick={() => setTab("payouts")}>Payouts <span>{pendingPayouts.length}</span></button>
        </div>

        {tab === "verification" ? (
          <section className="panel admin-review-list">
            <div className="panel-heading"><div><h2>Winner claims</h2><p>Proof is private and available to staff only.</p></div><Trophy className="panel-kicker" size={18} /></div>
            {winners.length ? winners.map((winner) => (
              <article className="admin-review-row" key={winner.id}>
                <div className="admin-review-row__title"><strong>{winner.match_count}-match winner</strong><span>{displayMoney(winner.prize_amount_minor, winner.currency)} · {winner.verification_status}</span></div>
                {winner.proofs.length ? winner.proofs.map((proof) => (
                  <div className="admin-proof-row" key={proof.id}>
                    <span className={`draw-status draw-status--${proof.review_status}`}>Proof {proof.review_status}</span>
                    <span>{displayDate(proof.submitted_at)}</span>
                    <button className="button button--outline button--small" type="button" disabled={busyId === proof.id} onClick={() => previewProof(proof.id)}>{busyId === proof.id ? <LoaderCircle className="spin" size={14} /> : <>View private proof <ExternalLink size={14} /></>}</button>
                    {proof.review_status === "pending" && <div className="admin-proof-actions"><input className="field-input" value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} placeholder="Review note (optional)" /><button className="button button--forest button--small" type="button" disabled={busyId === proof.id} onClick={() => review(proof.id, "approved")}>Approve</button><button className="button button--outline button--small" type="button" disabled={busyId === proof.id} onClick={() => review(proof.id, "rejected")}>Reject</button></div>}
                  </div>
                )) : <div className="score-empty"><p>No proof submitted for this claim.</p></div>}
              </article>
            )) : <div className="score-empty"><Trophy size={22} /><p>No winner claims yet.</p></div>}
          </section>
        ) : (
          <section className="panel admin-review-list">
            <div className="panel-heading"><div><h2>Payout records</h2><p>A real provider reference is required to mark a payment paid.</p></div></div>
            {payouts.length ? payouts.map((payout) => (
              <article className="admin-payout-row" key={payout.id}>
                <div><strong>{displayMoney(payout.amount_minor, payout.currency)}</strong><span>Attempt {payout.attempt_number} · {payout.status}</span></div>
                {payout.status === "pending" ? <div className="admin-proof-actions"><input className="field-input" value={providerRefs[payout.id] ?? ""} onChange={(event) => setProviderRefs((current) => ({ ...current, [payout.id]: event.target.value }))} placeholder="Provider payout reference" /><button className="button button--forest button--small" type="button" disabled={busyId === payout.id || !providerRefs[payout.id]} onClick={() => updatePayout(payout, "paid")}>Mark paid</button><button className="button button--outline button--small" type="button" disabled={busyId === payout.id} onClick={() => updatePayout(payout, "failed")}>Mark failed</button></div> : <span className="draw-status">{payout.provider_payout_id || payout.failure_reason || payout.status}</span>}
              </article>
            )) : <div className="score-empty"><Trophy size={22} /><p>No payouts recorded.</p></div>}
          </section>
        )}
    </>
  );
}
