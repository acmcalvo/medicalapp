import type { Metadata } from 'next';

import './globals.css';

export const metadata: Metadata = {
  title: 'Create API Key',
  description: 'Create a restricted API key for MedicalAPP integration access',
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
