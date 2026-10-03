import type { Metadata } from "next";
import type { ReactNode } from "react";
import { DM_Sans, DM_Serif_Display } from "next/font/google";
import "./globals.css";

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
});

const dmSerif = DM_Serif_Display({
  weight: "400",
  variable: "--font-dm-serif",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Digital Heroes | Golf that gives back",
  description: "Play your game, support a cause you choose, and join the monthly draw.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" data-scroll-behavior="smooth" className={`${dmSans.variable} ${dmSerif.variable}`}>
      <body>{children}</body>
    </html>
  );
}
