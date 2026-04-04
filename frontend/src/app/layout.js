import "./globals.css";
import AppShell from "@/components/AppShell";

export const metadata = {
  title: "RideGuard | Parametric Insurance for Gig Workers",
  description: "AI-powered parametric insurance platform for food delivery partners.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
