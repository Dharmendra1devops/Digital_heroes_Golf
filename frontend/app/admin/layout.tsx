import type { ReactNode } from "react";

import { AdminWorkspace } from "@/components/admin-workspace";

export default function AdminLayout({ children }: { children: ReactNode }) {
  const djangoOrigin = (process.env.DJANGO_API_ORIGIN ?? "http://127.0.0.1:8000").replace(/\/$/, "");
  return <AdminWorkspace djangoAdminUrl={`${djangoOrigin}/admin/`}>{children}</AdminWorkspace>;
}
