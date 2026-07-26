import type { Metadata } from "next";

import "../styles/globals.css";
import Providers from "./providers";
import { SessionRestorer } from "@/components/session-restorer";

export const metadata: Metadata = {
  title: "Signal Clone",
  description: "Signal-inspired messaging workspace built with Next.js and FastAPI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background font-sans text-foreground antialiased">
        <Providers>
          <SessionRestorer>{children}</SessionRestorer>
        </Providers>
      </body>
    </html>
  );
}
