"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, ChartNoAxesColumnIncreasing, HeartHandshake, ShieldCheck, Trophy, Users } from "lucide-react";

import { ApiError, getAdminOverview, type AdminOverview } from "@/lib/api";

function displayMoney(amountMinor: number, currency: string) {
  const formatter = new Intl.NumberFormat("en", { style: "currency", currency });
  const digits = formatter.resolvedOptions().maximumFractionDigits ?? 2;
  return formatter.format(amountMinor / (10 ** digits));
}

export function AdminReports() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getAdminOverview()
      .then((result) => { if (active) setOverview(result); })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof ApiError && cause.status === 403
          ? "Administrator access is required."
          : "Analytics are temporarily unavailable.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  if (loading) return <main className="dashboard-loading"><div><span className="loading-mark"><ChartNoAxesColumnIncreasing size={18} /></span>Loading reports…</div></main>;
  if (!overview) return <p className="auth-error" role="alert">{error || "Analytics could not be loaded."}</p>;

  return (
    <>
      <div className="admin-heading"><div><p className="eyebrow">Administrator / insights</p><h1>Reports &amp; analytics</h1><p>Financial totals are grouped by currency; totals reflect recorded transactions only.</p></div><span className="membership-tag membership-tag--active"><ShieldCheck size={14} /> Staff access</span></div>
      {error && <p className="auth-error" role="alert">{error}</p>}
      <div className="admin-report-cards">
        <article className="panel admin-report-card"><Users size={19} /><span>Member accounts</span><strong>{overview.total_users}</strong><small>Staff accounts excluded</small></article>
        <article className="panel admin-report-card"><ShieldCheck size={19} /><span>Active subscribers</span><strong>{overview.active_subscribers}</strong><small>Active at the time of this report</small></article>
        <article className="panel admin-report-card"><Trophy size={19} /><span>Recorded winners</span><strong>{overview.total_winners}</strong><small>All published prize claims</small></article>
      </div>
      <div className="admin-charity-grid admin-report-grid">
        <section className="panel">
          <div className="panel-heading"><div><h2>Prize-pool funding</h2><p>Recorded invoice allocations</p></div><Trophy className="panel-kicker" size={17} /></div>
          {overview.prize_funding_by_currency.length ? overview.prize_funding_by_currency.map((item) => <div className="admin-report-row" key={item.currency}><span>{item.currency}</span><strong>{displayMoney(item.amount_minor, item.currency)}</strong></div>) : <p className="admin-report-empty">No prize funding allocations recorded.</p>}
        </section>
        <section className="panel">
          <div className="panel-heading"><div><h2>Charity contributions</h2><p>Successful independent donations and recorded allocations</p></div><HeartHandshake className="panel-kicker" size={17} /></div>
          {overview.charity_contributions_by_currency.length ? overview.charity_contributions_by_currency.map((item) => <div className="admin-report-row" key={item.currency}><span>{item.currency}</span><strong>{displayMoney(item.amount_minor, item.currency)}</strong></div>) : <p className="admin-report-empty">No completed charity contributions recorded.</p>}
          {overview.top_charities.length > 0 && <div className="admin-report-subsection"><strong>Most-supported causes by direct donation</strong>{overview.top_charities.map((charity) => <div className="admin-report-row" key={`${charity.id}-${charity.donations__currency}`}><span>{charity.name}</span><strong>{displayMoney(charity.donation_total_minor, charity.donations__currency)}</strong></div>)}</div>}
        </section>
        <section className="panel">
          <div className="panel-heading"><div><h2>Draw operations</h2><p>Draw counts by status</p></div><ChartNoAxesColumnIncreasing className="panel-kicker" size={17} /></div>
          {overview.draws_by_status.length ? overview.draws_by_status.map((item) => <div className="admin-report-row" key={item.status}><span className={`draw-status draw-status--${item.status}`}>{item.status}</span><strong>{item.count}</strong></div>) : <p className="admin-report-empty">No draw records yet.</p>}
          <div className="admin-report-subsection"><strong>Recorded tier-pool amounts</strong>{overview.distributed_pools_by_currency.length ? overview.distributed_pools_by_currency.map((item) => <div className="admin-report-row" key={item.currency}><span>{item.currency}</span><strong>{displayMoney(item.distributed_minor, item.currency)}</strong></div>) : <p className="admin-report-empty">No pools recorded.</p>}</div>
        </section>
      </div>
      <p className="dashboard-footnote">Manage member records and Stableford scores from <Link href="/admin/users">Member management <ArrowRight size={14} /></Link>.</p>
    </>
  );
}
