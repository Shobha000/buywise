import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'BuyWise — Real-Time Review Intelligence',
  description: 'AI-powered platform for monitoring and analyzing customer reviews in real-time. Sentiment analysis, fake detection, topic extraction, and more.',
  keywords: ['review analytics', 'AI sentiment analysis', 'fake review detection', 'customer insights'],
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
