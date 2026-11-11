import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Essencial & Despensa — LPS",
  description: "Duas lojas, uma família de escolhas. Demonstração acadêmica de e-commerce.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
