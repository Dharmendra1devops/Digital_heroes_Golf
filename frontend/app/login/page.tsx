import type { Metadata } from "next";

import { AuthForm } from "@/components/auth-form";

export const metadata: Metadata = {
  title: "Sign in | Digital Heroes",
};

export default function LoginPage() {
  return <AuthForm mode="login" />;
}
