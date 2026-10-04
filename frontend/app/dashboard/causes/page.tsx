import type { Metadata } from "next";

import { MemberDashboard } from "@/components/member-dashboard";

export const metadata: Metadata = {
  title: "My cause | Digital Heroes",
};

export default function MemberCausesPage() {
  return <MemberDashboard page="causes" />;
}
