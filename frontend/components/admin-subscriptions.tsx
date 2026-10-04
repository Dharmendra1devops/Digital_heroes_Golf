"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowRight, CreditCard, LoaderCircle, Search } from "lucide-react";

import { ApiError, getAdminUsers, type AdminUser } from "@/lib/api";

function displayDate(value: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

export function AdminSubscriptions() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [query, setQuery] = useState("");
  const [count, setCount] = useState(0);
  const [nextPage, setNextPage] = useState<number | null>(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const skipInitialSearch = useRef(true);

  async function loadUsers(search: string, page: number, append = false) {
    const result = await getAdminUsers(search, page);
    setUsers((current) => append ? [...current, ...result.results] : result.results);
    setCount(result.count);
    setNextPage(result.next ? page + 1 : null);
  }

  useEffect(() => {
    let active = true;
    getAdminUsers()
      .then((result) => {
        if (!active) return;
        setUsers(result.results);
        setCount(result.count);
        setNextPage(result.next ? 2 : null);
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof ApiError ? cause.message : "Subscriptions could not be loaded.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (loading) return;
    if (skipInitialSearch.current) {
      skipInitialSearch.current = false;
      return;
    }
    const timer = window.setTimeout(() => {
      setError("");
      setLoadingMore(false);
      loadUsers(query, 1).catch((cause: unknown) => {
        setError(cause instanceof ApiError ? cause.message : "Subscriptions could not be searched.");
      });
    }, 220);
    return () => window.clearTimeout(timer);
  }, [loading, query]);

  const subscriptions = users.flatMap((user) => user.subscriptions.map((subscription) => ({ user, subscription })));

  async function loadMore() {
    if (!nextPage) return;
    const page = nextPage;
    setLoadingMore(true);
    setError("");
    try {
      await loadUsers(query, page, true);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "More subscription records could not be loaded.");
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <div>
      <div className="admin-heading">
        <div><p className="eyebrow">Administrator / billing</p><h1>Subscriptions</h1><p>{count} members · all recorded billing history is included</p></div>
      </div>
      {error && <p className="auth-error" role="alert">{error}</p>}
      <section className="panel admin-subscription-panel">
        <div className="panel-heading">
          <div><h2>Subscription register</h2><p>Search by member name or email. Billing changes are managed from member profiles.</p></div>
          <CreditCard className="panel-kicker" size={18} />
        </div>
        <label className="admin-user-search">
          <Search size={17} />
          <span className="sr-only">Search members</span>
          <input className="field-input" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by name or email" />
          <span>{subscriptions.length} subscriptions shown</span>
        </label>
        {loading ? (
          <div className="admin-page-loading"><LoaderCircle className="spin" size={18} />Loading subscriptions…</div>
        ) : subscriptions.length ? (
          <div className="admin-subscription-table-wrap">
            <table className="admin-subscription-table">
              <thead><tr><th>Member</th><th>Plan</th><th>Status</th><th>Current period</th><th>Renewal</th></tr></thead>
              <tbody>
                {subscriptions.map(({ user, subscription }) => (
                  <tr key={subscription.id}>
                    <td><strong>{user.display_name || "Member"}</strong><small>{user.email}</small></td>
                    <td><span className="admin-plan-name">{subscription.plan_interval === "monthly" ? "Monthly" : "Yearly"}</span></td>
                    <td><span className={`draw-status draw-status--${subscription.status}`}>{subscription.status}</span></td>
                    <td>{displayDate(subscription.current_period_start)} – {displayDate(subscription.current_period_end)}</td>
                    <td>{subscription.cancel_at_period_end ? "Ends this period" : subscription.status === "active" ? "Renews" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="admin-dashboard-empty"><CreditCard size={20} /><span>No subscriptions found for these members.</span></div>
        )}
        {nextPage && <button className="button button--outline admin-load-more" type="button" onClick={() => void loadMore()} disabled={loadingMore}>
          {loadingMore ? <><LoaderCircle className="spin" size={15} /> Loading members…</> : <>Load more members <ArrowRight size={15} /></>}
        </button>}
        <Link className="admin-subscription-manage-link" href="/admin/users">Manage member profiles and billing actions <ArrowRight size={14} /></Link>
      </section>
    </div>
  );
}
