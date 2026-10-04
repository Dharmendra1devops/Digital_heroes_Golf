"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { AppSidebar } from "@/components/app-sidebar";
import { ApiError, getCurrentAccount, type Account } from "@/lib/api";

export function AdminWorkspace({
  children,
  djangoAdminUrl,
}: {
  children: ReactNode;
  djangoAdminUrl: string;
}) {
  const pathname = usePathname();
  const [auth, setAuth] = useState<{ pathname: string; account: Account | null; error: string }>({
    pathname: "",
    account: null,
    error: "",
  });
  const adminSessionCheck = useRef<Promise<Account> | null>(null);

  useEffect(() => {
    if (pathname === "/admin/login" || auth.account) return;

    let active = true;
    if (!adminSessionCheck.current) {
      adminSessionCheck.current = getCurrentAccount().then(({ user }) => {
        if (!user.is_admin) {
          throw new ApiError("Administrator access is required.", 403);
        }
        return user;
      });
    }

    adminSessionCheck.current
      .then((user) => {
        if (!active) return;
        setAuth({ pathname, account: user, error: "" });
      })
      .catch((cause: unknown) => {
        if (active) {
          setAuth({
            pathname,
            account: null,
            error: cause instanceof ApiError && [401, 403].includes(cause.status)
              ? "Sign in with your administrator account to continue."
              : "Administrator access could not be verified. Please try again.",
          });
        }
      })

    return () => { active = false; };
  }, [pathname, auth.account]);

  if (pathname === "/admin/login") return <>{children}</>;

  if (!auth.account && auth.pathname !== pathname) {
    return <main className="dashboard-loading"><div>Loading administrator workspace…</div></main>;
  }

  if (!auth.account) {
    return (
      <main className="dashboard-loading">
        <div className="admin-denied">
          <h1>Administrator access required</h1>
          <p role="alert">{auth.error}</p>
          <Link className="button button--forest" href="/admin/login">Administrator sign in</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="dashboard-shell admin-workspace">
      <AppSidebar account={auth.account} admin adminSystemUrl={djangoAdminUrl} />
      <section className="dashboard-main admin-main">
        <header className="admin-topbar">
          <div className="admin-topbar__crumb"><span>Digital Heroes</span><span>/</span><strong>Administration</strong></div>
          <div className="admin-topbar__account"><span className="admin-status-dot" /> Administrator <span className="admin-topbar__divider" /> {auth.account.display_name || auth.account.email}</div>
        </header>
        <section className="admin-content">{children}</section>
      </section>
    </main>
  );
}
