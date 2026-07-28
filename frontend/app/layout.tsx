import type { Metadata } from 'next';

import './globals.css';

export const metadata: Metadata = {
  title: 'Medical Interaction Assistant',
  description: 'Role-based workflow for medication interaction checking and clinician review',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
