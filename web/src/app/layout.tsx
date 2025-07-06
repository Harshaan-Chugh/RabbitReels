import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import "./mobile.css";
import { VideoCounterProvider } from "@/contexts/VideoCounterContext";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { AuthProvider } from "@/contexts/AuthContext";
import { BillingProvider } from "@/contexts/BillingContext";
import { VideoHistoryProvider } from "@/contexts/VideoHistoryContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RabbitReels - AI Video Generator",
  description: "Create AI-powered short videos with your favorite characters like Family Guy and Rick & Morty",
  viewport: "width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "RabbitReels",
  },
  formatDetection: {
    telephone: false,
  },
  openGraph: {
    type: "website",
    title: "RabbitReels - AI Video Generator",
    description: "Create AI-powered short videos with your favorite characters like Family Guy and Rick & Morty",
    url: "https://rabbitreels.us",
    siteName: "RabbitReels",
    images: [
      {
        url: "https://rabbitreels.us/og-image.png",
        width: 1200,
        height: 630,
        alt: "RabbitReels - AI Video Generator",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "RabbitReels - AI Video Generator",
    description: "Create AI-powered short videos with your favorite characters like Family Guy and Rick & Morty",
    images: ["https://rabbitreels.us/og-image.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ThemeProvider>
          <AuthProvider>
            <BillingProvider>
              <VideoHistoryProvider>
                <VideoCounterProvider>
                  {children}
                </VideoCounterProvider>
              </VideoHistoryProvider>
            </BillingProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
