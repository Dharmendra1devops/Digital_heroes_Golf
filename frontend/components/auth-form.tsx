"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Eye, EyeOff, HeartHandshake, LoaderCircle, LockKeyhole } from "lucide-react";

import {
  ApiError,
  getCharities,
  getCurrentAccount,
  logIn,
  logOut,
  registerAccount,
  type Charity,
} from "@/lib/api";

type AuthMode = "login" | "register";
type AuthAudience = "member" | "admin";

export function AuthForm({ mode, audience = "member" }: { mode: AuthMode; audience?: AuthAudience }) {
  const router = useRouter();
  const isRegister = mode === "register";
  const isAdmin = audience === "admin";
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [charities, setCharities] = useState<Charity[]>([]);
  const [charityId, setCharityId] = useState("");
  const [contributionPercent, setContributionPercent] = useState("10");
  const [charitiesLoading, setCharitiesLoading] = useState(isRegister);
  const [charitiesError, setCharitiesError] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isRegister) return;
    let active = true;
    getCharities()
      .then((items) => {
        if (active) setCharities(items);
      })
      .catch(() => {
        if (active) setCharitiesError("Cause choices could not be loaded. Refresh and try again.");
      })
      .finally(() => {
        if (active) setCharitiesLoading(false);
      });
    return () => { active = false; };
  }, [isRegister]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (isRegister) {
        await registerAccount({
          email,
          display_name: displayName,
          password,
          ...(charityId ? {
            charity_id: charityId,
            contribution_bps: Math.round(Number(contributionPercent) * 100),
          } : {}),
        });
      } else {
        await logIn({ email, password });
      }
      if (isAdmin) {
        const { user } = await getCurrentAccount();
        if (!user.is_admin) {
          await logOut();
          setError("This account does not have administrator access. Sign in with a staff account.");
          return;
        }
      }
      const requestedNext = new URLSearchParams(window.location.search).get("next");
      let safeNext = isAdmin ? "/admin" : "/dashboard";
      if (requestedNext?.startsWith("/") && !requestedNext.startsWith("//") && !requestedNext.includes("\\")) {
        const destination = new URL(requestedNext, window.location.origin);
        const isAllowedAdminDestination = !isAdmin
          || destination.pathname === "/admin"
          || destination.pathname.startsWith("/admin/");
        if (destination.origin === window.location.origin && isAllowedAdminDestination) {
          safeNext = `${destination.pathname}${destination.search}${destination.hash}`;
        }
      }
      router.replace(safeNext);
      router.refresh();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "We could not reach the service. Try again shortly.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-story" aria-label="Digital Heroes">
        <Link className="brand-lockup" href="/">
          <span className="brand-mark"><HeartHandshake size={19} /></span>
          <span>digital<span className="brand-lockup__light">heroes</span></span>
        </Link>
        <div className="auth-story__message">
          <p className="eyebrow eyebrow--light"><span className="eyebrow-dot" /> {isAdmin ? "Secure staff access" : "Golf that gives back"}</p>
          <h1>{isAdmin ? "The work behind the good." : isRegister ? "A better reason to play." : "Good to have you back."}</h1>
          <p>{isAdmin ? "Manage the community, oversee draws, and keep every contribution accountable." : "Keep your game close. Keep a good cause closer."}</p>
        </div>
        <p className="auth-story__foot">{isAdmin ? "Administrator accounts are created by authorized staff." : "Your game can go further."}</p>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <Link className="auth-card__toplink" href={isAdmin ? "/login" : "/"}><ArrowLeft size={15} /> {isAdmin ? "Member sign in" : "Back to Digital Heroes"}</Link>
          <p className="eyebrow">{isAdmin ? "Administrator access" : "Member access"}</p>
          <h2>{isAdmin ? "Staff sign in" : isRegister ? "Create your account" : "Welcome back"}</h2>
          <p className="auth-card__intro">{isAdmin ? "Use your authorized staff account to access administration tools." : isRegister ? "Start with the basics. Your profile is yours to shape." : "Sign in to pick up where your last round left off."}</p>

          <form className="form-stack" onSubmit={handleSubmit} aria-busy={busy}>
            {isRegister && (
              <label className="field-label" htmlFor="display-name">
                Name <span className="panel-kicker">Optional</span>
                <input
                  className="field-input"
                  id="display-name"
                  name="name"
                  autoComplete="name"
                  maxLength={120}
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  placeholder="How should we greet you?"
                />
              </label>
            )}
            {isRegister && charities.length > 0 && (
              <>
                <label className="field-label" htmlFor="signup-charity">
                  Choose a cause
                  <select
                    className="field-input"
                    id="signup-charity"
                    value={charityId}
                    onChange={(event) => setCharityId(event.target.value)}
                    required
                  >
                    <option value="">Select a charity</option>
                    {charities.map((charity) => (
                      <option value={charity.id} key={charity.id}>{charity.name}</option>
                    ))}
                  </select>
                </label>
                <label className="field-label" htmlFor="signup-contribution">
                  Subscription contribution
                  <span className="percent-input-wrap">
                    <input
                      className="field-input"
                      id="signup-contribution"
                      type="number"
                      min="10"
                      max="100"
                      step="1"
                      required
                      value={contributionPercent}
                      onChange={(event) => setContributionPercent(event.target.value)}
                    />
                    <span aria-hidden="true">%</span>
                  </span>
                  <span className="auth-form__hint">At least 10% goes to your selected cause. You can change this later.</span>
                </label>
              </>
            )}
            <label className="field-label" htmlFor="email">
              Email address
              <input
                className="field-input"
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                required
                maxLength={254}
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
              />
            </label>
            <label className="field-label" htmlFor="password">
              Password
              <span className="password-field">
                <input
                  className="field-input"
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete={isRegister ? "new-password" : "current-password"}
                  minLength={isRegister ? 8 : undefined}
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder={isRegister ? "At least 8 characters" : "Enter your password"}
                />
                <button
                  className="password-toggle"
                  type="button"
                  onClick={() => setShowPassword((visible) => !visible)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  title={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </span>
            </label>
            {isRegister && <p className="auth-form__hint">Use at least 8 characters. Your password is stored securely.</p>}
            {isRegister && charitiesLoading && <p className="auth-form__hint" role="status">Loading cause choices…</p>}
            {isRegister && charitiesError && <p className="auth-error" role="alert">{charitiesError}</p>}
            {error && <p className="auth-error" role="alert">{error}</p>}
            <button className="button button--forest auth-submit" type="submit" disabled={busy || charitiesLoading || Boolean(charitiesError)}>
              {busy
                ? <><LoaderCircle className="spin" size={17} /><span>{isRegister ? "Creating account…" : "Signing in…"}</span></>
                : <>{isRegister ? "Create account" : "Sign in"} <ArrowRight size={16} /></>}
            </button>
          </form>

          <p className="auth-card__switch">
            {isAdmin
              ? <>Not an administrator? <Link href="/login">Use member sign in</Link></>
              : <>{isRegister ? "Already part of the club? " : "New around here? "}
                <Link href={isRegister ? "/login" : "/register"}>{isRegister ? "Sign in" : "Create an account"}</Link></>}
          </p>
          {!isAdmin && !isRegister && (
            <p className="auth-card__switch">Administrator? <Link href="/admin/login">Staff sign in</Link></p>
          )}
          <div className="auth-assurance"><LockKeyhole size={14} /> Protected with secure, same-site sign-in.</div>
        </div>
      </section>
    </main>
  );
}
