"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  ChartNoAxesColumnIncreasing,
  CreditCard,
  HeartHandshake,
  LoaderCircle,
  Trophy,
  Users,
} from "lucide-react";

import {
  ApiError,
  getAdminOverview,
  getAdminPayouts,
  getAdminUsers,
  getAdminWinners,
  type AdminOverview,
  type AdminPayout,
  type AdminUser,
  type MemberWinner,
} from "@/lib/api";

function displayDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

export function AdminDashboard() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [members, setMembers] = useState<AdminUser[]>([]);
  const [winners, setWinners] = useState<MemberWinner[]>([]);
  const [payouts, setPayouts] = useState<AdminPayout[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([getAdminOverview(), getAdminUsers(), getAdminWinners(), getAdminPayouts()])
      .then(([report, memberPage, winnerRecords, payoutRecords]) => {
        if (!active) return;
        setOverview(report);
        setMembers(memberPage.results.slice(0, 6));
        setWinners(winnerRecords);
        setPayouts(payoutRecords);
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof ApiError
          ? cause.message
          : "Dashboard information could not be loaded. Refresh to try again.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  if (loading) {
    return <div className="admin-page-loading"><LoaderCircle className="spin" size={20} />Loading your overview…</div>;
  }
  if (!overview) return <p className="auth-error" role="alert">{error || "The dashboard is unavailable."}</p>;

  const pendingProofs = winners.reduce(
    (count, winner) => count + winner.proofs.filter((proof) => proof.review_status === "pending").length,
    0,
  );
  const pendingPayouts = payouts.filter((payout) => payout.status === "pending").length;
  const subscriptionsSeen = members.reduce((count, member) => count + member.subscriptions.length, 0);

  return (
    <div className="admin-dashboard">
      <div className="admin-heading admin-dashboard__heading">
        <div>
          <p className="eyebrow">Administrator / overview</p>
          <h1>Dashboard overview.</h1>
          <p>Your members, subscriptions, and prize operations at a glance.</p>
        </div>
      </div>
      {error && <p className="auth-error" role="alert">{error}</p>}

      <section className="admin-stat-grid" aria-label="Administrator overview">
        <Link className="admin-stat-card" href="/admin/users">
          <span className="admin-stat-card__icon admin-stat-card__icon--green"><Users size={19} /></span>
          <span className="admin-stat-card__label">Member accounts</span>
          <strong>{overview.total_users}</strong>
          <span className="admin-stat-card__hint">View and manage members <ArrowRight size={13} /></span>
        </Link>
        <Link className="admin-stat-card" href="/admin/subscriptions">
          <span className="admin-stat-card__icon admin-stat-card__icon--blue"><CreditCard size={19} /></span>
          <span className="admin-stat-card__label">Active subscriptions</span>
          <strong>{overview.active_subscribers}</strong>
          <span className="admin-stat-card__hint">{subscriptionsSeen} records among newest members <ArrowRight size={13} /></span>
        </Link>
        <Link className="admin-stat-card" href="/admin/winners">
          <span className="admin-stat-card__icon admin-stat-card__icon--gold"><Trophy size={19} /></span>
          <span className="admin-stat-card__label">Recorded winners</span>
          <strong>{overview.total_winners}</strong>
          <span className="admin-stat-card__hint">{pendingProofs} proof reviews · {pendingPayouts} payouts pending <ArrowRight size={13} /></span>
        </Link>
        <Link className="admin-stat-card" href="/admin/draws">
          <span className="admin-stat-card__icon admin-stat-card__icon--coral"><Activity size={19} /></span>
          <span className="admin-stat-card__label">Draws in system</span>
          <strong>{overview.draws_by_status.reduce((total, item) => total + item.count, 0)}</strong>
          <span className="admin-stat-card__hint">Configure and review draws <ArrowRight size={13} /></span>
        </Link>
      </section>

      <section className="admin-dashboard__grid">
        <section className="panel admin-dashboard-panel">
          <div className="panel-heading">
            <div><h2>New members</h2><p>Latest account registrations</p></div>
            <Link className="admin-panel-link" href="/admin/users">All members <ArrowRight size={14} /></Link>
          </div>
          {members.length ? (
            <div className="admin-recent-list">
              {members.map((member) => {
                const activeSubscription = member.subscriptions.find((subscription) => subscription.status === "active");
                return (
                  <Link className="admin-recent-member" href="/admin/users" key={member.id}>
                    <span className="account-avatar">{(member.display_name || member.email).slice(0, 1).toUpperCase()}</span>
                    <span className="admin-recent-member__identity">
                      <strong>{member.display_name || "Member"}</strong>
                      <small>{member.email}</small>
                    </span>
                    <span className={`draw-status draw-status--${activeSubscription ? "active" : "draft"}`}>
                      {activeSubscription ? "Subscribed" : "New"}
                    </span>
                    <time>{displayDate(member.date_joined)}</time>
                  </Link>
                );
              })}
            </div>
          ) : <div className="admin-dashboard-empty"><Users size={20} /><span>No member accounts yet.</span></div>}
        </section>

        <section className="panel admin-dashboard-panel">
          <div className="panel-heading">
            <div><h2>Winner activity</h2><p>Recent claims and review status</p></div>
            <Link className="admin-panel-link" href="/admin/winners">Review winners <ArrowRight size={14} /></Link>
          </div>
          {winners.length ? (
            <div className="admin-recent-winners">
              {winners.slice(0, 5).map((winner) => (
                <div className="admin-recent-winner" key={winner.id}>
                  <span className="winner-match">{winner.match_count}</span>
                  <span><strong>{winner.match_count}-match claim</strong><small>{winner.proofs.length} proof{winner.proofs.length === 1 ? "" : "s"} · {winner.payouts.length} payout record{winner.payouts.length === 1 ? "" : "s"}</small></span>
                  <span className={`draw-status draw-status--${winner.verification_status}`}>{winner.verification_status}</span>
                </div>
              ))}
            </div>
          ) : <div className="admin-dashboard-empty"><Trophy size={20} /><span>No winner records yet. Draw results will appear here.</span></div>}
        </section>
      </section>

      <section className="admin-quick-links" aria-label="Administrator shortcuts">
        <Link href="/admin/subscriptions"><CreditCard size={18} /><span><strong>Subscription register</strong><small>Browse every member billing record</small></span><ArrowRight size={16} /></Link>
        <Link href="/admin/reports"><ChartNoAxesColumnIncreasing size={18} /><span><strong>Reports &amp; analytics</strong><small>Review recorded totals</small></span><ArrowRight size={16} /></Link>
        <Link href="/admin/charities"><HeartHandshake size={18} /><span><strong>Cause directory</strong><small>Manage causes and public content</small></span><ArrowRight size={16} /></Link>
      </section>
    </div>
  );
}
