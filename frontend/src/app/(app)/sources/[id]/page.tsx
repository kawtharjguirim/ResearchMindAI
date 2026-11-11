import { VideoView } from "./video-view";

export const metadata = { title: "Video" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <VideoView sourceId={id} />;
}
