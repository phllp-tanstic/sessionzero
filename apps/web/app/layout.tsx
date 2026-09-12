import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "SessionZero",
  description: "Price discovery for the market session that did not exist before 24/7 equities.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

