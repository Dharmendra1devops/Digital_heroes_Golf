"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import {
  Activity, ChartNoAxesColumnIncreasing, ChevronLeft, ChevronRight,
  CreditCard, ExternalLink, HeartHandshake, LayoutDashboard, LogOut,
  ShieldCheck, Trophy, UserRoundCog,
} from "lucide-react";

import { logOut, type Account } from "@/lib/api";

type AppSidebarProps = {
  account?: Account | null;
  admin?: boolean;
  adminSystemUrl?: string;
};

export function AppSidebar({ account, admin = false, adminSystemUrl }: AppSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const firstName = account?.display_name.trim().split(/\s+/)[0] || account?.email.split("@")[0] || "Admin";

  async function handleLogout() {
    setLoggingOut(true);
    setLogoutError("");
    try {
      await logOut();
      router.replace("/");
      router.refresh();
    } catch {
      setLogoutError("Sign out failed. Please try again.");
      setLoggingOut(false);
    }
  }

  function isCurrent(href: string) {
    return href.startsWith("#")
      ? pathname === "/dashboard" && href === "#overview"
      : pathname === href;
  }

  return (
    <aside className={`dashboard-sidebar${collapsed ? " dashboard-sidebar--collapsed" : ""}`}>
      <div className="sidebar-brand-row">
        <Link className="brand-lockup" href="/dashboard" aria-label="Digital Heroes dashboard">
          <span className="brand-mark"><HeartHandshake size={18} /></span>
          <span className="sidebar-wordmark">digital<span className="brand-lockup__light">heroes</span></span>
        </Link>
        <button
          className="sidebar-toggle"
          type="button"
          onClick={() => setCollapsed((value) => !value)}
          aria-controls="app-navigation"
          aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
          aria-expanded={!collapsed}
          title={collapsed ? "Expand navigation" : "Collapse navigation"}
        >
          {collapsed ? <ChevronRight size={17} /> : <ChevronLeft size={17} />}
        </button>
      </div>

      <p className="sidebar-label">{admin ? "Administration" : "Member space"}</p>
      <nav id="app-navigation" className="sidebar-nav" aria-label={admin ? "Administrator navigation" : "Member navigation"}>
        {admin ? (
          <>
            <Link className={isCurrent("/admin") ? "is-active" : undefined} aria-current={isCurrent("/admin") ? "page" : undefined} href="/admin" title="Administrator dashboard">
              <LayoutDashboard size={17} /><span className="sidebar-nav__label">Overview</span>
            </Link>
            <Link className={isCurrent("/admin/users") ? "is-active" : undefined} aria-current={isCurrent("/admin/users") ? "page" : undefined} href="/admin/users" title="Member management">
              <UserRoundCog size={17} /><span className="sidebar-nav__label">Members</span>
            </Link>
            <Link className={isCurrent("/admin/subscriptions") ? "is-active" : undefined} aria-current={isCurrent("/admin/subscriptions") ? "page" : undefined} href="/admin/subscriptions" title="Subscriptions">
              <CreditCard size={17} /><span className="sidebar-nav__label">Subscriptions</span>
            </Link>
            <Link className={isCurrent("/admin/winners") ? "is-active" : undefined} aria-current={isCurrent("/admin/winners") ? "page" : undefined} href="/admin/winners" title="Winners and payouts">
              <Trophy size={17} /><span className="sidebar-nav__label">Winners &amp; payouts</span>
            </Link>
            <Link className={isCurrent("/admin/draws") ? "is-active" : undefined} aria-current={isCurrent("/admin/draws") ? "page" : undefined} href="/admin/draws" title="Draw operations">
              <Activity size={17} /><span className="sidebar-nav__label">Draw operations</span>
            </Link>
            <Link className={isCurrent("/admin/reports") ? "is-active" : undefined} aria-current={isCurrent("/admin/reports") ? "page" : undefined} href="/admin/reports" title="Reports and analytics">
              <ChartNoAxesColumnIncreasing size={17} /><span className="sidebar-nav__label">Reports &amp; analytics</span>
            </Link>
            <Link className={isCurrent("/admin/plans") ? "is-active" : undefined} aria-current={isCurrent("/admin/plans") ? "page" : undefined} href="/admin/plans" title="Membership plans">
              <CreditCard size={17} /><span className="sidebar-nav__label">Plan settings</span>
            </Link>
            <Link className={isCurrent("/admin/charities") ? "is-active" : undefined} aria-current={isCurrent("/admin/charities") ? "page" : undefined} href="/admin/charities" title="Cause directory">
              <HeartHandshake size={17} /><span className="sidebar-nav__label">Cause directory</span>
            </Link>
            {adminSystemUrl && (
              <a href={adminSystemUrl} target="_blank" rel="noreferrer" title="System administration">
                <ShieldCheck size={17} /><span className="sidebar-nav__label">System administration</span><ExternalLink className="sidebar-external-icon" size={13} />
              </a>
            )}
            <Link className={isCurrent("/dashboard") ? "is-active" : undefined} aria-current={isCurrent("/dashboard") ? "page" : undefined} href="/dashboard" title="Member dashboard">
              <LayoutDashboard size={17} /><span className="sidebar-nav__label">Member space</span>
            </Link>
            <Link href="/charities" title="Public directory">
              <ExternalLink size={17} /><span className="sidebar-nav__label">Public directory</span>
            </Link>
            <Link href="/donate" title="Make a donation">
              <HeartHandshake size={17} /><span className="sidebar-nav__label">Make a donation</span>
            </Link>
          </>
        ) : (
          <>
            <Link className={isCurrent("/dashboard") ? "is-active" : undefined} aria-current={isCurrent("/dashboard") ? "page" : undefined} href="/dashboard" title="Overview">
              <Activity size={17} /><span className="sidebar-nav__label">Overview</span>
            </Link>
            <Link className={isCurrent("/dashboard/scores") ? "is-active" : undefined} aria-current={isCurrent("/dashboard/scores") ? "page" : undefined} href="/dashboard/scores" title="My scores">
              <ChartNoAxesColumnIncreasing size={17} /><span className="sidebar-nav__label">My scores</span>
            </Link>
            <Link className={isCurrent("/dashboard/winnings") ? "is-active" : undefined} aria-current={isCurrent("/dashboard/winnings") ? "page" : undefined} href="/dashboard/winnings" title="Winnings">
              <Trophy size={17} /><span className="sidebar-nav__label">Winnings</span>
            </Link>
            <Link className={isCurrent("/dashboard/membership") ? "is-active" : undefined} aria-current={isCurrent("/dashboard/membership") ? "page" : undefined} href="/dashboard/membership" title="Membership">
              <CreditCard size={17} /><span className="sidebar-nav__label">Membership</span>
            </Link>
            <Link className={isCurrent("/dashboard/causes") ? "is-active" : undefined} aria-current={isCurrent("/dashboard/causes") ? "page" : undefined} href="/dashboard/causes" title="My cause">
              <HeartHandshake size={17} /><span className="sidebar-nav__label">My cause</span>
            </Link>
            <Link className={isCurrent("/dashboard/account") ? "is-active" : undefined} aria-current={isCurrent("/dashboard/account") ? "page" : undefined} href="/dashboard/account" title="Account settings">
              <UserRoundCog size={17} /><span className="sidebar-nav__label">Account settings</span>
            </Link>
            {account?.is_admin && (
              <Link href="/admin/charities" title="Administration">
                <ShieldCheck size={17} /><span className="sidebar-nav__label">Administration</span>
              </Link>
            )}
            <Link href="/donate" title="Make a donation">
              <HeartHandshake size={17} /><span className="sidebar-nav__label">Make a donation</span>
            </Link>
          </>
        )}
        <button
          className="sidebar-signout"
          type="button"
          onClick={handleLogout}
          disabled={loggingOut}
          title="Sign out"
        >
          <LogOut size={17} /><span className="sidebar-nav__label">{loggingOut ? "Signing out…" : "Sign out"}</span>
        </button>
      </nav>
      {logoutError && <p className="sidebar-logout-error" role="alert">{logoutError}</p>}

      <div className="sidebar-bottom">
        <div className="account-mini">
          <span className="account-avatar" aria-hidden="true">{firstName.slice(0, 1).toUpperCase()}</span>
          <div className="account-mini__text">
            <strong>{account?.display_name || firstName}</strong>
            <span>{account?.email || "Administrator account"}</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
