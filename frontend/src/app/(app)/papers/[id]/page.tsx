import { PaperView } from "./paper-view";

export const metadata = { title: "Paper" };

export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ chunk?: string }>;
}) {
  const [{ id }, { chunk }] = await Promise.all([params, searchParams]);
  return <PaperView docId={id} chunkId={chunk ?? null} />;
}
