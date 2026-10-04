"use client";

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { HeartHandshake } from "lucide-react";

import { AppSidebar } from "@/components/app-sidebar";
import { ApiError, getCurrentAccount, type Account } from "@/lib/api";

type MemberAccountContextValue = {
  account: Account;
  setAccount: (account: Account) => void;
};

const MemberAccountContext = createContext<MemberAccountContextValue | null>(null);

const pageTitles: Record<string, string> = {
  "/dashboard": "Overview",
  "/dashboard/account": "Account settings",
  "/dashboard/membership": "Membership",
  "/dashboard/scores": "My scores",
  "/dashboard/winnings": "Winnings",
  "/dashboard/causes": "My cause",
};

export function useMemberAccount() {
  const value = useContext(MemberAccountContext);
  if (!value) throw new Error("useMemberAccount must be used inside MemberWorkspace.");
  return value;
}

export function MemberWorkspace({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const initialPath = useRef(pathname);
  const [account, setAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    let active = true;
    getCurrentAccount()
      .then(({ user }) => {
        if (active) setAccount(user);
      })
      .catch((error: unknown) => {
        if (!active) return;
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
          router.replace(`/login?next=${encodeURIComponent(initialPath.current)}`);
          return;
        }
        setLoadError("We could not open your member space. Please try again.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [router]);

  if (loading) {
    return <main className="dashboard-loading"><div><span className="loading-mark"><HeartHandshake size={18} /></span>Opening your member space…</div></main>;
  }
  if (!account) {
    return (
      <main className="dashboard-loading">
        <div>
          <p>{loadError || "Redirecting to sign in…"}</p>
          {loadError && <button className="button button--forest button--small" type="button" onClick={() => window.location.reload()}>Try again</button>}
        </div>
      </main>
    );
  }

  const firstName = account.display_name.trim().split(/\s+/)[0] || account.email.split("@")[0];
  const title = pageTitles[pathname] ?? "Member space";

  return (
    <MemberAccountContext.Provider value={{ account, setAccount }}>
      <main className="dashboard-shell member-workspace">
        <AppSidebar account={account} />
        <section className="dashboard-main">
          <header className="dashboard-topbar">
            <div className="breadcrumb" aria-label={`Member space, ${title}`}>
              <span className="breadcrumb__section">Member space</span>
              <span className="breadcrumb__separator" aria-hidden="true">/</span>
              <strong>{title}</strong>
            </div>
            <div className="dashboard-topbar__right">
              <span
                className={`membership-tag${account.is_subscriber ? " membership-tag--active" : ""}`}
                aria-label={account.is_subscriber ? "Membership active" : "Membership inactive"}
              >
                <span className="eyebrow-dot" />
                <span className="membership-tag__label">{account.is_subscriber ? "Membership active" : "Membership inactive"}</span>
              </span>
              <span className="account-avatar" aria-label={account.display_name || account.email}>{firstName.slice(0, 1).toUpperCase()}</span>
            </div>
          </header>
          {children}
        </section>
      </main>
    </MemberAccountContext.Provider>
  );
}
