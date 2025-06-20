import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { VideoCounterProvider } from "@/contexts/VideoCounterContext";
import { ThemeProvider } from "@/contexts/ThemeContext";

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
          <VideoCounterProvider>
            {children}
          </VideoCounterProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
