import type { Metadata } from "next";

import { AdminSubscriptions } from "@/components/admin-subscriptions";

export const metadata: Metadata = {
  title: "Subscriptions | Digital Heroes Admin",
};

export default function AdminSubscriptionsPage() {
  return <AdminSubscriptions />;
}
