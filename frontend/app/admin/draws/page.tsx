import type { Metadata } from "next";

import { AdminDraws } from "@/components/admin-draws";

export const metadata: Metadata = {
  title: "Draw operations | Digital Heroes Admin",
};

export default function AdminDrawsPage() {
  return <AdminDraws />;
}
