import './globals.css';
import Navbar from '../components/Navbar';
import ChatWidget from '../components/ChatWidget';
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
        <ChatWidget />
      </body>
    </html>
  );
}