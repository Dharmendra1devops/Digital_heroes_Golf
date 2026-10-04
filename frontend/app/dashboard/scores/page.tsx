import type { Metadata } from "next";

import { MemberDashboard } from "@/components/member-dashboard";

export const metadata: Metadata = {
  title: "My scorecard | Digital Heroes",
};

export default function MemberScoresPage() {
  return <MemberDashboard page="scores" />;
}
