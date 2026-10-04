import type { Metadata } from "next";

import { AuthForm } from "@/components/auth-form";

export const metadata: Metadata = {
  title: "Administrator sign in | Digital Heroes",
  description: "Secure sign-in for authorized Digital Heroes administrators.",
};

export default function AdminLoginPage() {
  return <AuthForm mode="login" audience="admin" />;
}
