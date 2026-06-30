import "./globals.css";

export const metadata = {
  title: "ledger — monthly expense tracker",
  description: "Track your expenses in plain English with a sleek terminal-style dashboard.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
