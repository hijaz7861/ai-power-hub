import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Power Hub",
  description: "One platform for your AI tools and workflows.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
