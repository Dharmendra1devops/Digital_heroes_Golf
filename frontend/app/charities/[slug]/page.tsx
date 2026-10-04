import { CharityDetail } from "@/components/charity-detail";

export default async function CharityPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <CharityDetail slug={slug} />;
}
