import { AuthLayout, SignUpAside } from "@/components/auth-panel";
import { SignUpForm } from "./signup-form";

export const metadata = { title: "Sign up" };

export default function SignUpPage() {
  return (
    <AuthLayout aside={<SignUpAside />}>
      <SignUpForm />
    </AuthLayout>
  );
}
