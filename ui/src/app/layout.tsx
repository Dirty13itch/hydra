import type { Metadata } from 'next'
import './globals.css'
import { ThemeProvider } from '@/components/ThemeProvider'
import { ToastProvider } from '@/components/Toast'

export const metadata: Metadata = {
  title: 'HYDRA Control Plane',
  description: 'Autonomous AI Operating System Control Interface',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen grid-bg">
        <ThemeProvider>
          <ToastProvider>
            <div className="scanlines">{children}</div>
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
