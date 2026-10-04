import Link from "next/link";
import { ArrowDown, ArrowRight, ArrowUpRight, HeartHandshake } from "lucide-react";

export default function Home() {
  return (
    <main className="home-page">
      <header className="public-nav">
        <Link className="brand-lockup" href="/" aria-label="Digital Heroes home">
          <span className="brand-mark"><HeartHandshake size={19} strokeWidth={2.2} /></span>
          <span>digital<span className="brand-lockup__light">heroes</span></span>
        </Link>
        <nav className="public-nav__links" aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <Link href="/charities">Charities</Link>
          <Link href="/draws">Draw results</Link>
          <a href="#giving">The giving</a>
          <Link href="/donate">Donate</Link>
        </nav>
        <div className="public-nav__actions">
          <Link className="nav-sign-in" href="/login">Sign in</Link>
          <Link className="button button--lime button--small" href="/subscribe">
            Join the club <ArrowUpRight size={16} />
          </Link>
        </div>
      </header>

      <section className="landing-hero" aria-labelledby="hero-title">
        <div className="landing-hero__veil" />
        <div className="landing-hero__content">
          <p className="eyebrow eyebrow--light"><span className="eyebrow-dot" /> A little golf. A lot of good.
          </p>
          <h1 id="hero-title">Digital<br />Heroes<span className="lime-period">.</span></h1>
          <p className="landing-hero__copy">Play your game. Back a cause. Be part of something bigger than the scorecard.</p>
          <div className="landing-hero__actions">
            <Link className="button button--lime" href="/subscribe">Make your next round count <ArrowRight size={17} /></Link>
            <a className="text-link text-link--light" href="#how-it-works">See how it works <ArrowDown size={16} /></a>
          </div>
        </div>
        <div className="landing-hero__caption"><span>01 / 03</span><span>Good things are in motion</span></div>
      </section>

      <section className="principle-strip" aria-label="Platform principles">
        <p><span className="principle-number">01</span> Your latest five Stableford scores</p>
        <span className="principle-divider" aria-hidden="true" />
        <p><span className="principle-number">02</span> A monthly draw, made for everyone</p>
        <span className="principle-divider" aria-hidden="true" />
        <p><span className="principle-number">03</span> A cause you choose</p>
      </section>

      <section className="how-section" id="how-it-works">
        <div className="section-intro">
          <p className="eyebrow">The short game</p>
          <h2>Three simple steps.<br /><span>One better kind of club.</span></h2>
        </div>
        <div className="step-list">
          <article className="step-item">
            <span className="step-item__number">01</span>
            <div><h3>Keep your score</h3><p>Add your five latest Stableford rounds. New scores roll in; the oldest rolls out.</p></div>
            <span className="step-item__icon">01—05</span>
          </article>
          <article className="step-item">
            <span className="step-item__number">02</span>
            <div><h3>Join the monthly draw</h3><p>Active members are entered into a monthly draw with three prize-match tiers.</p></div>
            <span className="step-item__icon"><ArrowUpRight size={20} /></span>
          </article>
          <article className="step-item">
            <span className="step-item__number">03</span>
            <div><h3>Choose your cause</h3><p>At least 10% of your subscription supports the charity you select.</p></div>
            <span className="step-item__icon"><HeartHandshake size={21} /></span>
          </article>
        </div>
      </section>

      <section className="giving-section" id="giving">
        <div className="giving-section__number">10<span>%</span></div>
        <div className="giving-section__copy">
          <p className="eyebrow eyebrow--light">Your game, doing good</p>
          <h2>A good round<br />goes further.</h2>
          <p>Every subscription sends a minimum of 10% to the charity you choose. Give more whenever you like. Your support is separate from the draw.</p>
          <Link className="text-link text-link--light" href="/register">Find your reason to play <ArrowRight size={17} /></Link>
          <Link className="text-link text-link--light" href="/donate">Make an independent donation <ArrowRight size={17} /></Link>
        </div>
        <div className="giving-section__stamp" aria-hidden="true"><HeartHandshake size={32} /><span>Play<br />with<br />purpose</span></div>
      </section>

      <footer className="site-footer">
        <Link className="brand-lockup" href="/">
          <span className="brand-mark"><HeartHandshake size={18} /></span>
          <span>digital<span className="brand-lockup__light">heroes</span></span>
        </Link>
        <p>Golf that gives back.</p>
        <div><Link href="/donate">Donate</Link><Link href="/login">Member sign in</Link><span>© Digital Heroes</span></div>
      </footer>
    </main>
  );
}
