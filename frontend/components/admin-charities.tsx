"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";
import {
  ArrowLeft, ArrowRight, ExternalLink, HeartHandshake, LoaderCircle,
  Plus, ShieldCheck, Trash2,
} from "lucide-react";

import {
  ApiError,
  createAdminCharity,
  deleteAdminCharity,
  getAdminCharities,
  getCurrentAccount,
  updateAdminCharity,
  type AdminCharity,
} from "@/lib/api";

export function AdminCharities() {
  const [items, setItems] = useState<AdminCharity[]>([]);
  const [loading, setLoading] = useState(true);
  const [authorized, setAuthorized] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [slug, setSlug] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [website, setWebsite] = useState("");
  const [imagePath, setImagePath] = useState("");
  const [featured, setFeatured] = useState(false);

  useEffect(() => {
    let active = true;
    getCurrentAccount()
      .then(async ({ user }) => {
        if (!active) return;
        if (!user.is_admin) {
          setAuthorized(false);
          return;
        }
        setAuthorized(true);
        const charities = await getAdminCharities();
        if (active) setItems(charities);
      })
      .catch((cause: unknown) => {
        if (!active) return;
        if (cause instanceof ApiError && (cause.status === 401 || cause.status === 403)) {
          setError("Sign in with an administrator account to access this page.");
          return;
        }
        setError("The charity manager is temporarily unavailable.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  function handleNameChange(value: string) {
    setName(value);
    setSlug(value.trim().toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""));
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const created = await createAdminCharity({
        slug,
        name,
        description,
        image_path: imagePath,
        website,
        is_featured: featured,
        is_active: true,
      });
      setItems((current) => [...current, created].sort((left, right) => left.name.localeCompare(right.name)));
      setName("");
      setSlug("");
      setDescription("");
      setWebsite("");
      setImagePath("");
      setFeatured(false);
      setMessage("Charity added to the directory.");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The charity could not be created.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleCharity(charity: AdminCharity, field: "is_active" | "is_featured") {
    setError("");
    try {
      const updated = await updateAdminCharity(charity.id, { [field]: !charity[field] });
      setItems((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The charity could not be updated.");
    }
  }

  async function removeCharity(id: string) {
    setBusy(true);
    try {
      await deleteAdminCharity(id);
      setItems((current) => current.filter((item) => item.id !== id));
      setConfirmDelete(null);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "The charity could not be removed.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <main className="dashboard-loading"><div><span className="loading-mark"><HeartHandshake size={18} /></span>Loading directory records…</div></main>;
  if (!authorized) return <main className="dashboard-loading"><div className="admin-denied"><ShieldCheck size={25} /><h1>Administrator access required</h1><p>{error || "This area is limited to staff accounts."}</p><Link className="button button--forest" href="/dashboard">Return to member space <ArrowRight size={15} /></Link></div></main>;

  return (
    <main className="admin-shell">
      <header className="admin-topbar">
        <Link className="brand-lockup" href="/dashboard"><span className="brand-mark"><HeartHandshake size={18} /></span><span>digital<span className="brand-lockup__light">heroes</span></span></Link>
        <nav><Link href="/dashboard"><ArrowLeft size={15} /> Member space</Link><Link href="/admin/plans">Membership plans <ArrowRight size={14} /></Link><Link href="/admin/draws">Draw operations <ArrowRight size={14} /></Link><Link href="/admin/winners">Winners & payouts <ArrowRight size={14} /></Link><Link href="/charities" target="_blank">View public directory <ExternalLink size={14} /></Link></nav>
      </header>
      <section className="admin-content">
        <div className="admin-heading">
          <div><p className="eyebrow">Administrator / charities</p><h1>Cause directory</h1><p>{items.length} {items.length === 1 ? "listing" : "listings"}</p></div>
          <span className="membership-tag membership-tag--active"><ShieldCheck size={14} /> Staff access</span>
        </div>
        {error && <p className="auth-error" role="alert">{error}</p>}
        {message && <p className="score-form__message" role="status">{message}</p>}

        <div className="admin-charity-grid">
          <section className="panel">
            <div className="panel-heading"><div><h2>Add a charity</h2><p>New listings appear in the public directory.</p></div><Plus className="panel-kicker" size={17} /></div>
            <form className="admin-create-form" onSubmit={handleCreate}>
              <label className="field-label" htmlFor="charity-name">Name
                <input className="field-input" id="charity-name" value={name} onChange={(event) => handleNameChange(event.target.value)} maxLength={180} required />
              </label>
              <label className="field-label" htmlFor="charity-slug">Directory slug
                <input className="field-input" id="charity-slug" value={slug} onChange={(event) => setSlug(event.target.value)} maxLength={160} pattern="[a-zA-Z0-9_-]+" required />
              </label>
              <label className="field-label" htmlFor="charity-description">Description
                <textarea className="field-input admin-textarea" id="charity-description" value={description} onChange={(event) => setDescription(event.target.value)} rows={4} />
              </label>
              <label className="field-label" htmlFor="charity-website">Website
                <input className="field-input" id="charity-website" type="url" value={website} onChange={(event) => setWebsite(event.target.value)} placeholder="https://" />
              </label>
              <label className="field-label" htmlFor="charity-image">Image object path
                <input className="field-input" id="charity-image" value={imagePath} onChange={(event) => setImagePath(event.target.value)} placeholder="charities/example/cover.webp" />
              </label>
              <label className="admin-check" htmlFor="charity-featured"><input id="charity-featured" type="checkbox" checked={featured} onChange={(event) => setFeatured(event.target.checked)} /> Feature in directory</label>
              <button className="button button--forest" type="submit" disabled={busy || !name || !slug}>{busy ? <LoaderCircle className="spin" size={16} /> : <>Add to directory <ArrowRight size={15} /></>}</button>
            </form>
          </section>

          <section className="panel admin-list-panel">
            <div className="panel-heading"><div><h2>Current listings</h2><p>Visibility and spotlight controls</p></div><span className="panel-kicker">{items.length}</span></div>
            {items.length ? <div className="admin-charity-list">{items.map((charity) => (
              <article className="admin-charity-row" key={charity.id}>
                <div className="admin-charity-row__main"><span className="account-avatar"><HeartHandshake size={16} /></span><div><strong>{charity.name}</strong><span>/{charity.slug}</span></div></div>
                <label className="admin-check"><input type="checkbox" checked={charity.is_active} onChange={() => toggleCharity(charity, "is_active")} /> Active</label>
                <label className="admin-check"><input type="checkbox" checked={charity.is_featured} onChange={() => toggleCharity(charity, "is_featured")} /> Featured</label>
                {confirmDelete === charity.id ? <span className="inline-confirm"><span>Remove?</span><button type="button" disabled={busy} onClick={() => removeCharity(charity.id)}>Yes</button><button type="button" onClick={() => setConfirmDelete(null)}>No</button></span> : <button className="icon-action icon-action--danger" type="button" onClick={() => setConfirmDelete(charity.id)} aria-label={`Delete ${charity.name}`} title="Delete charity"><Trash2 size={15} /></button>}
              </article>
            ))}</div> : <div className="score-empty"><HeartHandshake size={21} /><p>No directory listings yet.</p></div>}
          </section>
        </div>
      </section>
    </main>
  );
}
