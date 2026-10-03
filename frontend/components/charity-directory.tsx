"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { ArrowRight, ExternalLink, HeartHandshake, LoaderCircle, Search } from "lucide-react";

import { getCharities, type Charity } from "@/lib/api";

export function CharityDirectory() {
  const [charities, setCharities] = useState<Charity[]>([]);
  const [search, setSearch] = useState("");
  const [featuredOnly, setFeaturedOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      setLoading(true);
      getCharities(search)
        .then((items) => { if (active) setCharities(items); })
        .catch(() => { if (active) setError("The charity directory is temporarily unavailable."); })
        .finally(() => { if (active) setLoading(false); });
    }, 180);
    return () => { active = false; window.clearTimeout(timer); };
  }, [search]);

  const visibleCharities = featuredOnly ? charities.filter((charity) => charity.is_featured) : charities;

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
  }

  return (
    <main className="directory-page">
      <header className="public-nav">
        <Link className="brand-lockup" href="/" aria-label="Digital Heroes home">
          <span className="brand-mark"><HeartHandshake size={19} /></span>
          <span>digital<span className="brand-lockup__light">heroes</span></span>
        </Link>
        <nav className="public-nav__links" aria-label="Main navigation">
          <Link href="/">How it works</Link>
          <Link href="/#giving">The giving</Link>
        </nav>
        <div className="public-nav__actions">
          <Link className="nav-sign-in" href="/login">Sign in</Link>
          <Link className="button button--lime button--small" href="/register">Join the club <ArrowRight size={15} /></Link>
        </div>
      </header>

      <section className="directory-hero">
        <div>
          <p className="eyebrow">The causes behind the club</p>
          <h1>Good has<br />many names<span>.</span></h1>
        </div>
        <p className="directory-hero__copy">Find a cause that feels like yours. Choose the charity you want your subscription to support from your member space.</p>
      </section>

      <section className="directory-controls" aria-label="Search charities">
        <form className="directory-search" onSubmit={handleSearch}>
          <Search size={18} />
          <label className="sr-only" htmlFor="charity-search">Search charities</label>
          <input id="charity-search" type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search charities or causes" />
        </form>
        <div className="directory-filters" role="group" aria-label="Charity filters">
          <button className={!featuredOnly ? "is-selected" : ""} type="button" onClick={() => setFeaturedOnly(false)}>All causes</button>
          <button className={featuredOnly ? "is-selected" : ""} type="button" onClick={() => setFeaturedOnly(true)}>Featured</button>
        </div>
        <span className="directory-count">{visibleCharities.length} {visibleCharities.length === 1 ? "cause" : "causes"}</span>
      </section>

      {error && <p className="directory-error" role="alert">{error}</p>}
      {loading ? (
        <div className="directory-empty"><LoaderCircle className="spin" size={20} /><span>Finding the causes…</span></div>
      ) : visibleCharities.length ? (
        <section className="charity-list" aria-label="Charity directory">
          {visibleCharities.map((charity, index) => (
            <article className="charity-row" key={charity.id}>
              <span className="charity-row__number">{String(index + 1).padStart(2, "0")}</span>
              <span className="charity-row__mark"><HeartHandshake size={23} /></span>
              <div className="charity-row__body">
                <div className="charity-row__title"><h2>{charity.name}</h2>{charity.is_featured && <span>Featured</span>}</div>
                <p>{charity.description || "A cause supported by the Digital Heroes community."}</p>
                {charity.upcoming_events.length > 0 && (
                  <p className="charity-row__event">Next: {charity.upcoming_events[0].title} · {new Intl.DateTimeFormat("en", { day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(charity.upcoming_events[0].starts_at))}</p>
                )}
              </div>
              <div className="charity-row__actions">
                {charity.website && <a href={charity.website} target="_blank" rel="noreferrer" aria-label={`Visit ${charity.name} website`} title="Visit charity website"><ExternalLink size={16} /></a>}
                <Link href="/login" className="text-link">Choose in member space <ArrowRight size={15} /></Link>
              </div>
            </article>
          ))}
        </section>
      ) : (
        <div className="directory-empty">
          <HeartHandshake size={26} />
          <h2>{search || featuredOnly ? "No matching causes" : "The directory is getting ready"}</h2>
          <p>{search || featuredOnly ? "Try another search or browse all causes." : "Charities will appear here as the directory is curated."}</p>
          {(search || featuredOnly) && <button className="text-link" type="button" onClick={() => { setSearch(""); setFeaturedOnly(false); }}>Reset filters <ArrowRight size={15} /></button>}
        </div>
      )}

      <footer className="site-footer">
        <Link className="brand-lockup" href="/"><span className="brand-mark"><HeartHandshake size={18} /></span><span>digital<span className="brand-lockup__light">heroes</span></span></Link>
        <p>Golf that gives back.</p>
        <div><Link href="/login">Member sign in</Link><span>© Digital Heroes</span></div>
      </footer>
    </main>
  );
}
