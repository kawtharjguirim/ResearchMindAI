import { redirect } from "next/navigation";

// The marketing landing page comes in a later step; until then "/" opens the app.
export default function Home() {
  redirect("/projects");
}
