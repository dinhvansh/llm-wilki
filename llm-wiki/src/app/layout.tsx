import type { Metadata } from "next"
import "@/styles/globals.css"
import { AuthProvider } from "@/providers/auth-provider"
import { QueryProvider } from "@/providers/query-provider"

export const metadata: Metadata = {
  title: "LLM Wiki — AI Knowledge Base",
  description: "AI-native wiki and knowledge base platform with source grounding and traceability",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <QueryProvider><AuthProvider>{children}</AuthProvider></QueryProvider>
      </body>
    </html>
  )
}
