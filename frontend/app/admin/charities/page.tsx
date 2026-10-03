import type { Metadata } from "next";

import { AdminCharities } from "@/components/admin-charities";

export const metadata: Metadata = {
  title: "Cause directory | Digital Heroes Admin",
};

export default function AdminCharitiesPage() {
  return <AdminCharities />;
}
