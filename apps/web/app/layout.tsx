import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "SessionZero — Price discovery beyond the close",
  description: "SessionZero estimates where U.S. equities should reopen and interprets continuous-market price discovery beyond the cash close.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="bg-white font-['Inter'] text-zinc-950 antialiased">{children}</body>
    </html>
  );
}

