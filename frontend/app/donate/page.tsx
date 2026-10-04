import type { Metadata } from "next";
import { Suspense } from "react";

import { DonationPage } from "@/components/donation-page";

export const metadata: Metadata = {
  title: "Donate | Digital Heroes",
  description: "Make a one-time donation directly to a cause supported by the Digital Heroes community.",
};

export default function DonateRoute() {
  return (
    <Suspense fallback={<main className="dashboard-loading"><p>Loading donation options…</p></main>}>
      <DonationPage />
    </Suspense>
  );
}
