import type { Metadata } from "next";

import { AdminPlans } from "@/components/admin-plans";

export const metadata: Metadata = {
  title: "Membership plans | Digital Heroes Admin",
};

export default function AdminPlansPage() {
  return <AdminPlans />;
}
