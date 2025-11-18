import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AgriGuard - Corn Stress Monitoring',
  description: 'Real-time corn stress monitoring and yield prediction for Iowa counties',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
