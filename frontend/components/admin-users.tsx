"use client";

import { type FormEvent, useEffect, useState } from "react";
import { LoaderCircle, Search, ShieldCheck, Trash2, UserRoundCog } from "lucide-react";

import {
  ApiError,
  deleteAdminUserScore,
  getAdminUsers,
  updateAdminUser,
  updateAdminSubscription,
  updateAdminUserScore,
  type AdminUser,
} from "@/lib/api";

function displayDate(value: string) {
  return new Intl.DateTimeFormat("en", { dateStyle: "medium" }).format(new Date(value));
}

export function AdminUsers() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [query, setQuery] = useState("");
  const [count, setCount] = useState(0);
  const [nextPage, setNextPage] = useState<number | null>(1);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadUsers(search: string, page: number, append = false) {
    const result = await getAdminUsers(search, page);
    setUsers((current) => append ? [...current, ...result.results] : result.results);
    setCount(result.count);
    setNextPage(result.next ? page + 1 : null);
  }

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      setError("");
      getAdminUsers(query)
        .then((result) => {
          if (!active) return;
          setUsers(result.results);
          setCount(result.count);
          setNextPage(result.next ? 2 : null);
        })
        .catch((cause: unknown) => {
          if (active) setError(cause instanceof ApiError
            ? cause.message
            : "Member records are temporarily unavailable.");
        })
        .finally(() => { if (active) setLoading(false); });
    }, query ? 180 : 0);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [query]);

  async function saveProfile(event: FormEvent<HTMLFormElement>, user: AdminUser) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusyId(user.id);
    setError("");
    setMessage("");
    try {
      const updated = await updateAdminUser(user.id, {
        email: String(data.get("email")),
        display_name: String(data.get("display_name")),
      });
      setUsers((current) => current.map((item) => item.id === user.id ? updated : item));
      setMessage("Member profile saved.");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The member profile could not be saved.");
    } finally {
      setBusyId(null);
    }
  }

  async function toggleAccount(user: AdminUser) {
    if (user.is_active && !window.confirm(`Deactivate ${user.email}? They will no longer be able to sign in.`)) return;
    setBusyId(user.id);
    setError("");
    setMessage("");
    try {
      const updated = await updateAdminUser(user.id, { is_active: !user.is_active });
      setUsers((current) => current.map((item) => item.id === user.id ? updated : item));
      setMessage(updated.is_active ? "Member account reactivated." : "Member account deactivated.");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The account status could not be updated.");
    } finally {
      setBusyId(null);
    }
  }

  async function saveScore(user: AdminUser, scoreId: string, value: string) {
    const parsedScore = Number(value);
    if (!Number.isInteger(parsedScore) || parsedScore < 1 || parsedScore > 45) {
      setError("Stableford scores must be a whole number from 1 to 45.");
      return;
    }
    setBusyId(scoreId);
    setError("");
    setMessage("");
    try {
      const updated = await updateAdminUserScore(user.id, scoreId, { score: parsedScore });
      setUsers((current) => current.map((item) => item.id === user.id
        ? { ...item, scores: item.scores.map((score) => score.id === scoreId ? updated : score) }
        : item));
      setMessage("Member score updated.");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The score could not be updated.");
    } finally {
      setBusyId(null);
    }
  }

  async function removeScore(user: AdminUser, scoreId: string) {
    if (!window.confirm("Remove this score from the member record?")) return;
    setBusyId(scoreId);
    setError("");
    try {
      await deleteAdminUserScore(user.id, scoreId);
      setUsers((current) => current.map((item) => item.id === user.id
        ? { ...item, scores: item.scores.filter((score) => score.id !== scoreId) }
        : item));
      setMessage("Member score removed.");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The score could not be removed.");
    } finally {
      setBusyId(null);
    }
  }

  async function changeSubscription(
    user: AdminUser,
    subscription: AdminUser["subscriptions"][number],
    action: "cancel" | "resume",
  ) {
    const actionLabel = action === "cancel" ? "schedule cancellation for" : "resume renewal for";
    if (!window.confirm(`Are you sure you want to ${actionLabel} this ${subscription.plan_interval} subscription?`)) return;
    setBusyId(subscription.id);
    setError("");
    setMessage("");
    try {
      const result = await updateAdminSubscription(subscription.id, action);
      setUsers((current) => current.map((item) => item.id === user.id
        ? {
            ...item,
            subscriptions: item.subscriptions.map((entry) => (
              entry.id === result.subscription.id ? result.subscription : entry
            )),
          }
        : item));
      setMessage(action === "cancel"
        ? "Subscription cancellation was scheduled through Stripe."
        : "Subscription renewal was resumed through Stripe.");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The subscription could not be changed.");
    } finally {
      setBusyId(null);
    }
  }

  if (loading) return <main className="dashboard-loading"><div><span className="loading-mark"><UserRoundCog size={18} /></span>Loading member records…</div></main>;

  return (
    <>
      <div className="admin-heading"><div><p className="eyebrow">Administrator / people</p><h1>Member management</h1><p>{count} member accounts · staff accounts are protected</p></div><span className="membership-tag membership-tag--active"><ShieldCheck size={14} /> Staff access</span></div>
      {error && <p className="auth-error" role="alert">{error}</p>}
      {message && <p className="score-form__message" role="status">{message}</p>}
      <section className="panel">
        <form className="admin-user-search" onSubmit={(event) => event.preventDefault()}>
          <Search size={17} />
          <label className="sr-only" htmlFor="member-search">Search members</label>
          <input id="member-search" className="field-input" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by name or email" />
          <span>{users.length} of {count}</span>
        </form>
        <div className="admin-member-list">
          {users.map((user) => {
            const activeSubscription = user.subscriptions.find((subscription) => subscription.status === "active");
            return (
              <article className="admin-member-card" key={user.id}>
                <button className="admin-member-summary" type="button" aria-expanded={expandedId === user.id} onClick={() => setExpandedId(expandedId === user.id ? null : user.id)}>
                  <span className="account-avatar">{(user.display_name || user.email).slice(0, 1).toUpperCase()}</span>
                  <span><strong>{user.display_name || "Member"}</strong><small>{user.email} · Joined {displayDate(user.date_joined)}</small></span>
                  <span className={`draw-status draw-status--${user.is_active ? "active" : "cancelled"}`}>{user.is_active ? "Active account" : "Deactivated"}</span>
                  <span className="membership-tag">{activeSubscription ? `${activeSubscription.plan_interval} · ${activeSubscription.status}` : "No active plan"}</span>
                  <span>{expandedId === user.id ? "Close" : "Manage"}</span>
                </button>
                {expandedId === user.id && <div className="admin-member-details">
                  <form className="admin-profile-form" onSubmit={(event) => void saveProfile(event, user)}>
                    <label className="field-label" htmlFor={`member-name-${user.id}`}>Display name<input className="field-input" id={`member-name-${user.id}`} name="display_name" defaultValue={user.display_name} maxLength={120} /></label>
                    <label className="field-label" htmlFor={`member-email-${user.id}`}>Email<input className="field-input" id={`member-email-${user.id}`} name="email" type="email" defaultValue={user.email} required /></label>
                    <button className="button button--forest button--small" type="submit" disabled={busyId === user.id}>{busyId === user.id ? <LoaderCircle className="spin" size={15} /> : "Save profile"}</button>
                    <button className="button button--outline button--small" type="button" disabled={busyId === user.id} onClick={() => void toggleAccount(user)}>{user.is_active ? "Deactivate account" : "Reactivate account"}</button>
                  </form>
                  <div className="admin-subscription-summary">
                    <strong>Subscription history</strong>
                    {user.subscriptions.length ? user.subscriptions.map((subscription) => (
                      <div className="admin-managed-subscription" key={subscription.id}>
                        <span>{subscription.plan_interval} · {subscription.status}{subscription.current_period_end ? ` · through ${displayDate(subscription.current_period_end)}` : ""}{subscription.cancel_at_period_end ? " · cancellation scheduled" : ""}</span>
                        {subscription.status === "active" || subscription.status === "trialing" ? (
                          <button
                            className="button button--outline button--small"
                            type="button"
                            disabled={busyId === subscription.id}
                            onClick={() => void changeSubscription(user, subscription, subscription.cancel_at_period_end ? "resume" : "cancel")}
                          >
                            {busyId === subscription.id
                              ? <LoaderCircle className="spin" size={14} />
                              : subscription.cancel_at_period_end ? "Resume renewal" : "Cancel at period end"}
                          </button>
                        ) : null}
                      </div>
                    )) : <span>No subscriptions recorded.</span>}
                    <small>Billing changes are confirmed with the payment provider; subscription state is never edited directly here.</small>
                  </div>
                  <div className="admin-member-scores"><strong>Stableford scores</strong>{user.scores.length ? user.scores.map((score) => <div className="admin-score-edit" key={score.id}><span>{displayDate(score.score_date)}</span><input className="field-input" type="number" min={1} max={45} defaultValue={score.score} aria-label={`Score from ${displayDate(score.score_date)}`} onBlur={(event) => { if (Number(event.target.value) !== score.score) void saveScore(user, score.id, event.target.value); }} /><button className="icon-action icon-action--danger" type="button" disabled={busyId === score.id} aria-label={`Delete score from ${displayDate(score.score_date)}`} onClick={() => void removeScore(user, score.id)}><Trash2 size={15} /></button></div>) : <span>No scores recorded.</span>}</div>
                </div>}
              </article>
            );
          })}
          {!users.length && <div className="score-empty"><UserRoundCog size={22} /><p>No members match this search.</p></div>}
        </div>
        {nextPage && <button className="button button--outline admin-load-more" type="button" onClick={() => {
          const page = nextPage;
          setNextPage(null);
          loadUsers(query, page, true).catch((cause: unknown) => {
            setError(cause instanceof ApiError ? cause.message : "More member records could not be loaded.");
            setNextPage(page);
          });
        }}>Load more members</button>}
      </section>
    </>
  );
}
