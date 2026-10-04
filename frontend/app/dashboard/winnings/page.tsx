import type { Metadata } from "next";

import { MemberDashboard } from "@/components/member-dashboard";

export const metadata: Metadata = {
  title: "Winnings | Digital Heroes",
};

export default function MemberWinningsPage() {
  return <MemberDashboard page="winnings" />;
}
