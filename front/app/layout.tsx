import './globals.css';
import { Bebas_Neue, Barlow } from 'next/font/google';
import Navbar from '../components/Navbar';
import ChatWidget from '../components/ChatWidget';
import { ReactNode } from 'react';

const bebas = Bebas_Neue({
  weight: '400',
  subsets: ['latin'],
  variable: '--font-bebas',
  display: 'swap',
});

const barlow = Barlow({
  weight: ['400', '500', '600'],
  subsets: ['latin'],
  variable: '--font-barlow',
  display: 'swap',
});

export const metadata = {
  title: 'PawMatch — Adoptez un animal',
  description: 'Plateforme centralisée d\'adoption animale — SPA, Seconde Chance et plus.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr" className={`${bebas.variable} ${barlow.variable}`}>
      <body style={{ fontFamily: 'var(--font-barlow), system-ui, sans-serif' }}>
        <Navbar />
        {children}
        <ChatWidget />
      </body>
    </html>
  );
}
