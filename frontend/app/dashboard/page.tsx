import type { Metadata } from "next";

import { MemberDashboard } from "@/components/member-dashboard";

export const metadata: Metadata = {
  title: "Member space | Digital Heroes",
};

export default function DashboardPage() {
  return <MemberDashboard />;
}
