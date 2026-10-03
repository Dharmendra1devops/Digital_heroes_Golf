import type { Metadata } from "next";

import { SubscribePage } from "@/components/subscribe-page";

export const metadata: Metadata = {
  title: "Membership | Digital Heroes",
  description: "Choose a Digital Heroes membership plan and support a cause you care about.",
};

export default async function MembershipPage({
  searchParams,
}: {
  searchParams: Promise<{ checkout?: string }>;
}) {
  const params = await searchParams;
  return <SubscribePage checkoutCancelled={params.checkout === "cancelled"} />;
}
