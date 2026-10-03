import type { Metadata } from "next";

import { CharityDirectory } from "@/components/charity-directory";

export const metadata: Metadata = {
  title: "Charities | Digital Heroes",
  description: "Explore causes supported by the Digital Heroes community.",
};

export default function CharitiesPage() {
  return <CharityDirectory />;
}
