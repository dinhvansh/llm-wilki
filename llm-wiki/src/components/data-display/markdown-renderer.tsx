'use client'
import { Children } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'

interface MarkdownRendererProps {
  content: string
  className?: string
}

const IMAGE_URL_RE = /\.(png|jpe?g|gif|webp|svg)(\?.*)?$/i

function isRenderableImageUrl(value?: string | null) {
  if (!value) return false
  if (!IMAGE_URL_RE.test(value)) return false
  return value.includes('/uploads/') || value.includes('/backend-uploads/') || value.startsWith('/uploads/')
}

function RenderedImage({ src, alt }: { src?: string | null; alt?: string | null }) {
  if (!src) return null
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt ?? ''}
      className="my-4 w-full rounded-lg border border-border object-contain"
      loading="lazy"
    />
  )
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={cn('prose prose-sm max-w-none dark:prose-invert prose-slate', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="text-2xl font-bold mb-4 mt-6">{children}</h1>,
          h2: ({ children }) => <h2 className="text-xl font-semibold mb-3 mt-5 pb-1.5 border-b">{children}</h2>,
          h3: ({ children }) => <h3 className="text-base font-semibold mb-2 mt-4">{children}</h3>,
          p: ({ children }) => <p className="mb-3 leading-relaxed">{children}</p>,
          ul: ({ children }) => <ul className="list-disc list-inside mb-3 space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-inside mb-3 space-y-1">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          code: ({ className, children, ...props }) => {
            const isInline = !className
            return isInline
              ? <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">{children}</code>
              : <code className={cn('block bg-muted p-4 rounded-md text-xs font-mono overflow-x-auto mb-3', className)} {...props}>{children}</code>
          },
          blockquote: ({ children }) => (
            <blockquote className="border-l-3 border-primary pl-4 italic text-muted-foreground my-4">{children}</blockquote>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto mb-3">
              <table className="min-w-full border border-border rounded-md text-sm">{children}</table>
            </div>
          ),
          th: ({ children }) => <th className="border border-border bg-muted px-3 py-1.5 text-left font-medium">{children}</th>,
          td: ({ children }) => <td className="border border-border px-3 py-1.5">{children}</td>,
          a: ({ href, children }) => {
            if (isRenderableImageUrl(href)) {
              const labelNode = Children.toArray(children).find(child => typeof child === 'string')
              const label = typeof labelNode === 'string' ? labelNode : ''
              return <RenderedImage src={href} alt={label} />
            }
            return <a href={href} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>
          },
          img: ({ src, alt }) => <RenderedImage src={src} alt={alt} />,
          hr: () => <hr className="my-6 border-border" />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
