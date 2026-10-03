"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { ArrowLeft, ArrowRight, Eye, EyeOff, HeartHandshake, LoaderCircle, LockKeyhole } from "lucide-react";

import { ApiError, logIn, registerAccount } from "@/lib/api";

type AuthMode = "login" | "register";

export function AuthForm({ mode }: { mode: AuthMode }) {
  const router = useRouter();
  const isRegister = mode === "register";
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (isRegister) {
        await registerAccount({ email, display_name: displayName, password });
      } else {
        await logIn({ email, password });
      }
      router.replace("/dashboard");
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
          <p className="eyebrow eyebrow--light"><span className="eyebrow-dot" /> Golf that gives back</p>
          <h1>{isRegister ? "A better reason to play." : "Good to have you back."}</h1>
          <p>Keep your game close. Keep a good cause closer.</p>
        </div>
        <p className="auth-story__foot">Your game can go further.</p>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <Link className="auth-card__toplink" href="/"><ArrowLeft size={15} /> Back to Digital Heroes</Link>
          <p className="eyebrow">Member access</p>
          <h2>{isRegister ? "Create your account" : "Welcome back"}</h2>
          <p className="auth-card__intro">{isRegister ? "Start with the basics. Your profile is yours to shape." : "Sign in to pick up where your last round left off."}</p>

          <form className="form-stack" onSubmit={handleSubmit}>
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
            <label className="field-label" htmlFor="email">
              Email address
              <input
                className="field-input"
                id="email"
                name="email"
                type="email"
                autoComplete="email"
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
                  minLength={8}
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder={isRegister ? "At least 8 characters" : "Your password"}
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
            {error && <p className="auth-error" role="alert">{error}</p>}
            <button className="button button--forest auth-submit" type="submit" disabled={busy}>
              {busy ? <LoaderCircle className="spin" size={17} /> : <>{isRegister ? "Create account" : "Sign in"} <ArrowRight size={16} /></>}
            </button>
          </form>

          <p className="auth-card__switch">
            {isRegister ? "Already part of the club? " : "New around here? "}
            <Link href={isRegister ? "/login" : "/register"}>{isRegister ? "Sign in" : "Create an account"}</Link>
          </p>
          <div className="auth-assurance"><LockKeyhole size={14} /> Your password is securely hashed by Django.</div>
        </div>
      </section>
    </main>
  );
}
