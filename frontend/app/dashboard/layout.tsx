import type { ReactNode } from "react";

import { MemberWorkspace } from "@/components/member-workspace";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return <MemberWorkspace>{children}</MemberWorkspace>;
}
