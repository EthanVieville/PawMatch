import './globals.css';
import Navbar from '../components/Navbar';
import { ReactNode } from 'react';

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="fr">
      <body className="text-gray-900">
        <Navbar />
        {children}
      </body>
    </html>
  );
}