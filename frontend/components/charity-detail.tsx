"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, CalendarDays, ExternalLink, HeartHandshake, LoaderCircle, MapPin } from "lucide-react";

import { ApiError, getCharity, type Charity } from "@/lib/api";

function formatEventDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(value));
}

export function CharityDetail({ slug }: { slug: string }) {
  const [charity, setCharity] = useState<Charity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getCharity(slug)
      .then((result) => { if (active) setCharity(result); })
      .catch((cause: unknown) => {
        if (active) {
          setError(cause instanceof ApiError && cause.status === 404
            ? "This cause is no longer available."
            : "Cause details are temporarily unavailable.");
        }
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [slug]);

  return (
    <main className="directory-page charity-detail-page">
      <header className="public-nav">
        <Link className="brand-lockup" href="/" aria-label="Digital Heroes home">
          <span className="brand-mark"><HeartHandshake size={19} /></span>
          <span>digital<span className="brand-lockup__light">heroes</span></span>
        </Link>
        <nav className="public-nav__links" aria-label="Main navigation">
          <Link href="/charities">All causes</Link>
          <Link href="/#giving">The giving</Link>
          <Link href="/donate">Donate</Link>
        </nav>
        <div className="public-nav__actions">
          <Link className="nav-sign-in" href="/login">Sign in</Link>
          <Link className="button button--lime button--small" href="/register">Join the club <ArrowRight size={15} /></Link>
        </div>
      </header>

      <section className="charity-detail">
        <Link className="text-link charity-detail__back" href="/charities"><ArrowLeft size={15} /> All causes</Link>
        {loading ? (
          <div className="directory-empty" role="status"><LoaderCircle className="spin" size={20} />Loading cause details…</div>
        ) : error || !charity ? (
          <div className="directory-empty" role="alert"><HeartHandshake size={25} /><h1>Cause not found</h1><p>{error || "This cause is no longer available."}</p><Link className="button button--forest" href="/charities">Browse causes</Link></div>
        ) : (
          <>
            <div className="charity-detail__hero">
              {charity.image_path.startsWith("https://") && (
                <div className="charity-detail__image">
                  <Image src={charity.image_path} alt="" fill sizes="(max-width: 760px) 100vw, 520px" unoptimized />
                </div>
              )}
              <div>
                <p className="eyebrow">A cause behind the club{charity.is_featured ? " · Featured" : ""}</p>
                <h1>{charity.name}<span>.</span></h1>
                <p className="charity-detail__description">{charity.description || "A cause supported by the Digital Heroes community."}</p>
                <div className="charity-detail__actions">
                  <Link className="button button--forest" href={`/donate?charity=${encodeURIComponent(charity.id)}`}>Donate to this cause <ArrowRight size={16} /></Link>
                  <Link className="button button--outline" href="/register">Choose through membership <ArrowRight size={16} /></Link>
                  {charity.website && <a className="text-link" href={charity.website} target="_blank" rel="noreferrer">Visit website <ExternalLink size={14} /></a>}
                </div>
              </div>
            </div>

            <section className="charity-detail__events" aria-labelledby="charity-events-title">
              <div className="panel-heading">
                <div><p className="eyebrow">Stay connected</p><h2 id="charity-events-title">Upcoming events</h2></div>
                <CalendarDays size={20} />
              </div>
              {charity.upcoming_events.length ? (
                <div className="charity-event-list">
                  {charity.upcoming_events.map((event) => (
                    <article className="charity-event-card" key={event.id}>
                      <div><h3>{event.title}</h3><p>{event.description || "Join the community and support this cause."}</p></div>
                      <span><CalendarDays size={15} /> {formatEventDate(event.starts_at)}</span>
                      {event.location && <span><MapPin size={15} /> {event.location}</span>}
                    </article>
                  ))}
                </div>
              ) : (
                <p className="charity-detail__empty">No upcoming events have been announced yet.</p>
              )}
            </section>
          </>
        )}
      </section>
      <footer className="site-footer">
        <Link className="brand-lockup" href="/"><span className="brand-mark"><HeartHandshake size={18} /></span><span>digital<span className="brand-lockup__light">heroes</span></span></Link>
        <p>Golf that gives back.</p>
        <div><Link href="/donate">Donate</Link><Link href="/login">Member sign in</Link><span>© Digital Heroes</span></div>
      </footer>
    </main>
  );
}
