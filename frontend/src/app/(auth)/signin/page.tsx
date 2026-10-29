import { Suspense } from "react";
import { AuthLayout, SignInAside } from "@/components/auth-panel";
import { SignInForm } from "./signin-form";

export const metadata = { title: "Sign in" };

export default function SignInPage() {
  return (
    <AuthLayout aside={<SignInAside />}>
      <Suspense>
        <SignInForm />
      </Suspense>
    </AuthLayout>
  );
}
