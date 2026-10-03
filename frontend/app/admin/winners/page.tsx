import type { Metadata } from "next";

import { AdminWinners } from "@/components/admin-winners";

export const metadata: Metadata = {
  title: "Winners and payouts | Digital Heroes Admin",
};

export default function AdminWinnersPage() {
  return <AdminWinners />;
}
