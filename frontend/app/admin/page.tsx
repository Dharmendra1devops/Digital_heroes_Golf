import type { Metadata } from "next";

import { AdminDashboard } from "@/components/admin-dashboard";

export const metadata: Metadata = {
  title: "Administrator dashboard | Digital Heroes",
};

export default function AdminDashboardPage() {
  return <AdminDashboard />;
}
