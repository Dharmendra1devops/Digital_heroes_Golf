"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";
import { ArrowRight, Dice5, HeartHandshake, LoaderCircle, ShieldCheck } from "lucide-react";

import {
  ApiError,
  createAdminDraw,
  createAdminDrawConfiguration,
  getAdminDrawConfigurations,
  getAdminDraws,
  getCurrentAccount,
  simulateAdminDraw,
  type DrawConfiguration,
  type DrawRecord,
  type DrawRun,
} from "@/lib/api";

function dateTimeLocalAfter(days: number) {
  const value = new Date(Date.now() + days * 24 * 60 * 60 * 1000);
  const offset = value.getTimezoneOffset() * 60 * 1000;
  return new Date(value.getTime() - offset).toISOString().slice(0, 16);
}

function displayDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AdminDraws() {
  const [configurations, setConfigurations] = useState<DrawConfiguration[]>([]);
  const [draws, setDraws] = useState<DrawRecord[]>([]);
  const [runs, setRuns] = useState<Record<string, DrawRun>>({});
  const [loading, setLoading] = useState(true);
  const [authorized, setAuthorized] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [mode, setMode] = useState<DrawConfiguration["mode"]>("random");
  const [matchPolicy, setMatchPolicy] = useState("unique");
  const [configurationId, setConfigurationId] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [eligibilityCutoff, setEligibilityCutoff] = useState("");

  useEffect(() => {
    let active = true;
    getCurrentAccount()
      .then(async ({ user }) => {
        if (!active || !user.is_admin) return;
        setAuthorized(true);
        const [configurationList, drawList] = await Promise.all([
          getAdminDrawConfigurations(),
          getAdminDraws(),
        ]);
        if (!active) return;
        setConfigurations(configurationList);
        setDraws(drawList);
        setConfigurationId(configurationList[0]?.id ?? "");
        setScheduledAt(dateTimeLocalAfter(7));
        setEligibilityCutoff(dateTimeLocalAfter(6));
      })
      .catch((cause: unknown) => {
        if (!active) return;
        if (cause instanceof ApiError && (cause.status === 401 || cause.status === 403)) {
          setError("Sign in with an administrator account to access this page.");
        } else {
          setError("The draw manager is temporarily unavailable.");
        }
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  async function handleConfiguration(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const version = Math.max(0, ...configurations.map((configuration) => configuration.version)) + 1;
      const configuration = await createAdminDrawConfiguration({
        version,
        mode,
        candidate_min: 1,
        candidate_max: 45,
        number_count: 5,
        parameters: { duplicate_score_match_policy: matchPolicy },
      });
      setConfigurations((current) => [configuration, ...current]);
      setConfigurationId(configuration.id);
      setMessage(`Draw configuration v${version} created.`);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The configuration could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDrawCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const draw = await createAdminDraw({
        configuration: configurationId,
        scheduled_at: new Date(scheduledAt).toISOString(),
        eligibility_cutoff: new Date(eligibilityCutoff).toISOString(),
      });
      setDraws((current) => [draw, ...current]);
      setMessage("Draw created. You can simulate it for review.");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The draw could not be created.");
    } finally {
      setBusy(false);
    }
  }

  async function handleSimulation(draw: DrawRecord) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await simulateAdminDraw(draw.id);
      setRuns((current) => ({ ...current, [draw.id]: response.run }));
      setDraws((current) => current.map((item) => item.id === draw.id ? { ...item, status: "simulated" } : item));
      setMessage("Simulation completed. Results are not published and no winners or payouts were created.");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Simulation could not be completed.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <main className="dashboard-loading"><div><span className="loading-mark"><HeartHandshake size={18} /></span>Loading draw controls…</div></main>;
  if (!authorized) return <main className="dashboard-loading"><div className="admin-denied"><ShieldCheck size={25} /><h1>Administrator access required</h1><p>{error || "This area is limited to staff accounts."}</p><Link className="button button--forest" href="/dashboard">Return to member space <ArrowRight size={15} /></Link></div></main>;

  return (
    <main className="admin-shell">
      <header className="admin-topbar">
        <Link className="brand-lockup" href="/dashboard"><span className="brand-mark"><HeartHandshake size={18} /></span><span>digital<span className="brand-lockup__light">heroes</span></span></Link>
        <nav><Link href="/admin/plans">Membership plans <ArrowRight size={14} /></Link><Link href="/admin/charities">Cause directory <ArrowRight size={14} /></Link><Link href="/admin/winners">Winners & payouts <ArrowRight size={14} /></Link></nav>
      </header>
      <section className="admin-content">
        <div className="admin-heading"><div><p className="eyebrow">Administrator / draws</p><h1>Draw operations</h1><p>{draws.length} scheduled draws · {configurations.length} configurations</p></div><span className="membership-tag membership-tag--active"><ShieldCheck size={14} /> Staff access</span></div>
        {error && <p className="auth-error" role="alert">{error}</p>}
        {message && <p className="score-form__message" role="status">{message}</p>}
        <p className="draw-policy-note"><Dice5 size={16} /> Simulations are review-only. Publishing and prize settlement remain unavailable until funding rules are configured.</p>

        <div className="admin-charity-grid">
          <section className="panel">
            <div className="panel-heading"><div><h2>Draw configuration</h2><p>New versions preserve existing draw rules.</p></div><Dice5 className="panel-kicker" size={17} /></div>
            <form className="admin-create-form" onSubmit={handleConfiguration}>
              <label className="field-label" htmlFor="draw-mode">Selection mode
                <select className="field-input" id="draw-mode" value={mode} onChange={(event) => setMode(event.target.value as DrawConfiguration["mode"])}><option value="random">Random</option><option value="algorithmic">Algorithmic · score frequency</option></select>
              </label>
              <label className="field-label" htmlFor="match-policy">Repeated Stableford scores
                <select className="field-input" id="match-policy" value={matchPolicy} onChange={(event) => setMatchPolicy(event.target.value)}><option value="unique">Count unique score values</option><option value="frequency">Count repeated values</option></select>
              </label>
              <div className="draw-tier-preview"><div><strong>5 matches</strong><span>40% · jackpot rollover</span></div><div><strong>4 matches</strong><span>35% · no rollover</span></div><div><strong>3 matches</strong><span>25% · no rollover</span></div></div>
              <button className="button button--forest" type="submit" disabled={busy}>{busy ? <LoaderCircle className="spin" size={16} /> : <>Create configuration <ArrowRight size={15} /></>}</button>
            </form>
            <div className="admin-config-list">{configurations.map((configuration) => (
              <button className={`admin-config-option${configuration.id === configurationId ? " is-selected" : ""}`} key={configuration.id} type="button" onClick={() => setConfigurationId(configuration.id)}>
                <span>v{configuration.version} · {configuration.mode}</span><strong>{configuration.number_count} numbers · {configuration.prize_tiers.reduce((total, tier) => total + tier.share_bps, 0) / 100}% tiers</strong>
              </button>
            ))}</div>
          </section>

          <section className="panel">
            <div className="panel-heading"><div><h2>Schedule a draw</h2><p>Only active, paid members with five scores qualify.</p></div><span className="panel-kicker">{configurations.length ? "Ready" : "Needs configuration"}</span></div>
            <form className="admin-create-form" onSubmit={handleDrawCreate}>
              <label className="field-label" htmlFor="draw-configuration">Configuration
                <select className="field-input" id="draw-configuration" value={configurationId} onChange={(event) => setConfigurationId(event.target.value)} required disabled={!configurations.length}>
                  <option value="" disabled>Select a version</option>
                  {configurations.map((configuration) => <option key={configuration.id} value={configuration.id}>v{configuration.version} · {configuration.mode}</option>)}
                </select>
              </label>
              <div className="admin-plan-amount-row">
                <label className="field-label" htmlFor="draw-cutoff">Eligibility cutoff
                  <input className="field-input" id="draw-cutoff" type="datetime-local" value={eligibilityCutoff} onChange={(event) => setEligibilityCutoff(event.target.value)} required />
                </label>
                <label className="field-label" htmlFor="draw-schedule">Draw time
                  <input className="field-input" id="draw-schedule" type="datetime-local" value={scheduledAt} onChange={(event) => setScheduledAt(event.target.value)} required />
                </label>
              </div>
              <button className="button button--forest" type="submit" disabled={busy || !configurationId}>{busy ? <LoaderCircle className="spin" size={16} /> : <>Schedule draw <ArrowRight size={15} /></>}</button>
            </form>
            <div className="admin-draw-list">
              {draws.length ? draws.map((draw) => (
                <article className="admin-draw-row" key={draw.id}>
                  <div><strong>{displayDate(draw.scheduled_at)}</strong><span>Cutoff {displayDate(draw.eligibility_cutoff)}</span></div>
                  <span className={`draw-status draw-status--${draw.status}`}>{draw.status}</span>
                  {draw.status !== "published" && draw.status !== "cancelled" && <button className="button button--outline button--small" type="button" disabled={busy} onClick={() => handleSimulation(draw)}>Simulate</button>}
                  {runs[draw.id] && <div className="draw-result"><p>Simulation #{runs[draw.id].run_number} · {runs[draw.id].result_snapshot.eligible_entry_count} eligible members</p><strong>{runs[draw.id].result_snapshot.winning_numbers.join(" · ")}</strong><span>{runs[draw.id].result_snapshot.matches.filter((item) => item.match_count >= 3).length} prize-tier matches · not published</span></div>}
                </article>
              )) : <div className="score-empty"><Dice5 size={21} /><p>No draws scheduled.</p></div>}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
