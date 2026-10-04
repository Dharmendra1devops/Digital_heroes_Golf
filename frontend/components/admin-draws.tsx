"use client";

import { type FormEvent, useEffect, useState } from "react";
import { ArrowRight, Dice5, HeartHandshake, LoaderCircle, ShieldCheck } from "lucide-react";

import {
  ApiError,
  createAdminDraw,
  createAdminDrawConfiguration,
  getAdminDrawConfigurations,
  getAdminDraws,
  publishAdminDraw,
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

function displayMinorAmount(amountMinor: number, currency: string) {
  const formatter = new Intl.NumberFormat("en", {
    style: "currency",
    currency,
  });
  const digits = formatter.resolvedOptions().maximumFractionDigits ?? 2;
  return formatter.format(amountMinor / 10 ** digits);
}

export function AdminDraws() {
  const [configurations, setConfigurations] = useState<DrawConfiguration[]>([]);
  const [draws, setDraws] = useState<DrawRecord[]>([]);
  const [runs, setRuns] = useState<Record<string, DrawRun>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [mode, setMode] = useState<DrawConfiguration["mode"]>("random");
  const [matchPolicy, setMatchPolicy] = useState("unique");
  const [prizeContributionPercent, setPrizeContributionPercent] = useState("");
  const [configurationId, setConfigurationId] = useState("");
  const [scheduledAt, setScheduledAt] = useState("");
  const [eligibilityCutoff, setEligibilityCutoff] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([getAdminDrawConfigurations(), getAdminDraws()])
      .then(([configurationList, drawList]) => {
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
        prize_pool_contribution_bps: Math.round(Number(prizeContributionPercent) * 100),
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

  async function handlePublish(draw: DrawRecord) {
    if (!window.confirm("Publish the official draw results and create prize records? This cannot be undone.")) {
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await publishAdminDraw(draw.id);
      setRuns((current) => ({ ...current, [draw.id]: response.run }));
      setDraws((current) => current.map((item) => item.id === draw.id
        ? {
          ...item,
          status: "published",
          published_at: response.run.created_at,
          winning_numbers: response.run.result_snapshot.winning_numbers,
          prize_pools: response.run.result_snapshot.prize_pools ?? [],
        }
        : item));
      setMessage(`Draw published with ${response.run.result_snapshot.winner_count ?? 0} prize winner(s). Payouts remain pending verification.`);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The draw could not be published.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <main className="dashboard-loading"><div><span className="loading-mark"><HeartHandshake size={18} /></span>Loading draw controls…</div></main>;

  return (
    <>
        <div className="admin-heading"><div><p className="eyebrow">Administrator / draws</p><h1>Draw operations</h1><p>{draws.length} scheduled draws · {configurations.length} configurations</p></div><span className="membership-tag membership-tag--active"><ShieldCheck size={14} /> Staff access</span></div>
        {error && <p className="auth-error" role="alert">{error}</p>}
        {message && <p className="score-form__message" role="status">{message}</p>}
        <p className="draw-policy-note"><Dice5 size={16} /> Prize pools use the configured share of each active paid subscription. Annual invoices contribute 1/12 per monthly draw; unclaimed 5-match prizes roll forward.</p>

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
              <label className="field-label" htmlFor="draw-prize-contribution">Prize-pool contribution
                <div className="admin-plan-amount-row">
                  <input className="field-input" id="draw-prize-contribution" type="number" min="0.01" max="100" step="0.01" value={prizeContributionPercent} onChange={(event) => setPrizeContributionPercent(event.target.value)} placeholder="e.g. 10" required />
                  <span className="field-input" aria-hidden="true">%</span>
                </div>
                <span className="field-hint">Annual invoices are prorated across 12 monthly draws.</span>
              </label>
              <div className="draw-tier-preview"><div><strong>5 matches</strong><span>40% · jackpot rollover</span></div><div><strong>4 matches</strong><span>35% · no rollover</span></div><div><strong>3 matches</strong><span>25% · no rollover</span></div></div>
              <button className="button button--forest" type="submit" disabled={busy}>{busy ? <LoaderCircle className="spin" size={16} /> : <>Create configuration <ArrowRight size={15} /></>}</button>
            </form>
            <div className="admin-config-list">{configurations.map((configuration) => (
              <button className={`admin-config-option${configuration.id === configurationId ? " is-selected" : ""}`} key={configuration.id} type="button" onClick={() => setConfigurationId(configuration.id)}>
                <span>v{configuration.version} · {configuration.mode}</span><strong>{configuration.number_count} numbers · {configuration.prize_pool_contribution_bps === null ? "contribution not set" : `${configuration.prize_pool_contribution_bps / 100}% contribution`}</strong>
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
                  {(draw.status === "draft" || draw.status === "simulated") && <button className="button button--outline button--small" type="button" disabled={busy} onClick={() => handleSimulation(draw)}>Simulate</button>}
                  {draw.status === "simulated" && <button className="button button--forest button--small" type="button" disabled={busy} onClick={() => handlePublish(draw)}>Publish results</button>}
                  {draw.status === "published" && <div className="draw-result"><p>Official winning numbers</p><strong>{draw.winning_numbers.join(" · ")}</strong>{draw.prize_pools.map((pool) => <span key={pool.match_count}>{pool.match_count} matches · {displayMinorAmount(pool.available_minor, pool.currency)}{pool.rollover_in_minor ? ` · includes ${displayMinorAmount(pool.rollover_in_minor, pool.currency)} rollover` : ""}{pool.rollover_out_minor ? ` · ${displayMinorAmount(pool.rollover_out_minor, pool.currency)} rolls forward` : ""}</span>)}</div>}
                  {runs[draw.id] && draw.status === "simulated" && <div className="draw-result"><p>Simulation #{runs[draw.id].run_number} · {runs[draw.id].result_snapshot.eligible_entry_count} eligible members</p><strong>{runs[draw.id].result_snapshot.winning_numbers.join(" · ")}</strong><span>{runs[draw.id].result_snapshot.matches.filter((item) => item.match_count >= 3).length} prize-tier matches · not published</span></div>}
                </article>
              )) : <div className="score-empty"><Dice5 size={21} /><p>No draws scheduled.</p></div>}
            </div>
          </section>
        </div>
    </>
  );
}
