/* eslint-disable react-refresh/only-export-components */
import { createFileRoute, Link } from '@tanstack/react-router'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ArrowLeft } from 'lucide-react'
import whitepaper from '../../../docs/loom-whitepaper.md?raw'

export const Route = createFileRoute('/whitepaper')({
  component: WhitepaperPage,
})

function WhitepaperPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-10 md:px-6">
      <div className="mb-8">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to homepage
        </Link>
      </div>

      <article className="rounded-3xl border border-border/70 bg-card px-6 py-8 shadow-sm md:px-10 md:py-10">
        <div className="prose prose-neutral max-w-none dark:prose-invert prose-headings:scroll-mt-24 prose-headings:tracking-tight prose-p:text-foreground/85 prose-li:text-foreground/80">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{whitepaper}</ReactMarkdown>
        </div>
      </article>
    </div>
  )
}
