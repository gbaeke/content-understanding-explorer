import { useQuery } from '@tanstack/react-query'
import { ArrowDown, ArrowRight } from 'lucide-react'
import type { ReactNode } from 'react'
import { infoOptions } from '@/client/@tanstack/react-query.gen'
import { bands } from '@/lib/confidence'
import { cn } from '@/lib/utils'

/* The numbers on this page are the real ones from samples/invoice.pdf: page size, polygon and confidence of the
   invoice number as the service returned them. */
const PAGE = { width: 8.2639, height: 11.6806 }
const CORNERS = [
  [6.8314, 1.2192],
  [7.477, 1.2183],
  [7.477, 1.3542],
  [6.8314, 1.3535],
] as const
const POLYGON = CORNERS.flat()

function Box({ title, children, className }: { title: string; children?: ReactNode; className?: string }) {
  return (
    <div className={cn('rounded-md border border-border bg-surface px-3 py-2', className)}>
      <div className="font-medium">{title}</div>
      {children && <div className="mt-0.5 text-xs text-fg-muted">{children}</div>}
    </div>
  )
}

const Arrow = ({ label }: { label?: string }) => (
  <div className="flex shrink-0 flex-col items-center justify-center gap-0.5 text-fg-muted">
    {label && <span className="text-[11px] leading-none">{label}</span>}
    <ArrowRight className="hidden size-4 lg:block" />
    <ArrowDown className="size-4 lg:hidden" />
  </div>
)

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <section className="grid gap-x-6 gap-y-3 lg:grid-cols-[2.5rem_1fr]">
      <div className="flex size-9 items-center justify-center rounded-full bg-accent font-semibold text-accent-fg">
        {n}
      </div>
      <div className="min-w-0 space-y-3">
        <h2 className="pt-1.5 text-lg font-semibold">{title}</h2>
        {children}
      </div>
    </section>
  )
}

const Code = ({ children }: { children: string }) => (
  <pre className="overflow-x-auto rounded-md border border-border bg-muted p-3 font-mono text-xs leading-relaxed">
    {children}
  </pre>
)

/** A small page with the invoice number's box on it, corners labelled: how a polygon in inches lands on the page. */
function PolygonFigure() {
  const [[x1, y1], [x2], [, y3]] = CORNERS
  // the box is tiny at page scale, so the figure zooms in on the top right corner of the page
  const view = { x: 5.2, y: 0.95, width: 3.05, height: 1.05 }
  const labels = [
    { label: 'x1, y1', dx: -0.06, dy: -0.07, anchor: 'end' },
    { label: 'x2, y2', dx: 0.06, dy: -0.07, anchor: 'start' },
    { label: 'x3, y3', dx: 0.06, dy: 0.16, anchor: 'start' },
    { label: 'x4, y4', dx: -0.06, dy: 0.16, anchor: 'end' },
  ] as const
  const corners = CORNERS.map(([x, y], index) => ({ x, y, ...labels[index as 0 | 1 | 2 | 3] }))
  return (
    <div className="grid items-center gap-4 sm:grid-cols-[8rem_1fr]">
      {/* the whole page, with the zoomed area marked */}
      <svg viewBox={`0 0 ${PAGE.width} ${PAGE.height}`} className="w-32 rounded-sm border border-border bg-white">
        {[1.3, 2.9, 3.2, 3.5, 4.7, 5.1, 5.5, 5.9, 9.8, 10.1].map((y) => (
          <rect key={y} x={0.8} y={y} width={y > 4 && y < 9 ? 6.6 : 2.4} height={0.12} fill="#d5d5d0" />
        ))}
        <rect x={0.8} y={0.75} width={3} height={0.3} fill="#1f4e79" />
        <rect x={x1} y={y1} width={x2 - x1} height={y3 - y1} className="fill-ok/40 stroke-ok" strokeWidth={0.04} />
        <rect
          x={view.x}
          y={view.y}
          width={view.width}
          height={view.height}
          fill="none"
          className="stroke-accent"
          strokeWidth={0.06}
          strokeDasharray="0.15 0.1"
        />
      </svg>
      {/* the zoom */}
      <svg
        viewBox={`${view.x} ${view.y} ${view.width} ${view.height}`}
        className="w-full max-w-xl rounded-md border border-dashed border-accent bg-white"
      >
        <text x={5.35} y={1.33} fontSize={0.13} fill="#62626a">
          Invoice number
        </text>
        <text x={7.465} y={1.33} fontSize={0.118} fontWeight={700} textAnchor="end" fill="#1c1c1e">
          2026-0147
        </text>
        <polygon points={POLYGON.join(' ')} className="fill-ok/25 stroke-ok" strokeWidth={0.012} />
        {corners.map((c) => (
          <g key={c.label}>
            <circle cx={c.x} cy={c.y} r={0.025} className="fill-ok" />
            <text x={c.x + c.dx} y={c.y + c.dy} fontSize={0.09} textAnchor={c.anchor} fill="#15803d">
              {c.label}
            </text>
          </g>
        ))}
        <text x={5.3} y={1.85} fontSize={0.09} fill="#62626a">
          x1 = 6.83 in from the left edge, y1 = 1.22 in from the top edge
        </text>
      </svg>
    </div>
  )
}

export function HowItWorks() {
  // the model the analyzer is configured with, so this page never names a stale one
  const model = useQuery({ ...infoOptions(), staleTime: Infinity }).data?.model ?? 'chat model'
  return (
    <div className="h-full overflow-auto">
      <div className="mx-auto max-w-5xl space-y-10 px-6 py-8">
        <header className="space-y-2">
          <h1 className="text-2xl font-semibold">How this sample works</h1>
          <p className="max-w-3xl text-fg-muted">
            One call to Azure Content Understanding reads the document, fills a list of fields, and says for every value
            how sure it is and where on the page it found it. The app only sends the file and draws the answer.
          </p>
        </header>

        {/* ---- before and after */}
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="card space-y-3">
            <h2 className="font-semibold">Before: two steps you own</h2>
            <div className="flex flex-col items-stretch gap-2 lg:flex-row lg:items-center">
              <Box title="Document Intelligence">layout to Markdown</Box>
              <Arrow />
              <Box title="Your prompt + LLM">Markdown to JSON</Box>
              <Arrow />
              <Box title="JSON">values only</Box>
            </div>
            <p className="text-xs text-fg-muted">
              The LLM sees text, not the page. It cannot tell you where a value came from or how sure it is.
            </p>
          </div>
          <div className="card space-y-3 border-accent">
            <h2 className="font-semibold">Now: one analyzer</h2>
            <div className="flex flex-col items-stretch gap-2 lg:flex-row lg:items-center">
              <Box title="Content Understanding" className="flex-1 border-accent bg-accent-soft">
                reads, extracts and grounds in one call
              </Box>
              <Arrow />
              <Box title="JSON">
                values + <span className="text-ok">confidence</span> + <span className="text-ok">page regions</span>
              </Box>
            </div>
            <p className="text-xs text-fg-muted">
              You write field descriptions instead of a prompt. The service keeps the link between each value and the
              words on the page.
            </p>
          </div>
        </section>

        {/* ---- the request path */}
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">The path of one upload</h2>
          <div className="grid gap-3 lg:grid-cols-[1fr_auto_1.6fr]">
            <div className="rounded-lg border border-dashed border-border p-3">
              <div className="mb-2 text-xs font-medium tracking-wide text-fg-muted uppercase">Your laptop</div>
              <div className="flex flex-col items-stretch gap-2 lg:flex-row lg:items-center">
                <Box title="Browser" className="flex-1">
                  React page: upload, viewer, fields
                </Box>
                <Arrow label="file" />
                <Box title="FastAPI" className="flex-1">
                  POST /api/extract, renders pages to PNG
                </Box>
              </div>
            </div>
            <Arrow label="PDF bytes, Entra token" />
            <div className="rounded-lg border border-dashed border-accent p-3">
              <div className="mb-2 text-xs font-medium tracking-wide text-fg-muted uppercase">
                Azure: one Foundry resource (rg-geert-content-understanding, Sweden Central)
              </div>
              <div className="flex flex-col items-stretch gap-2 lg:flex-row lg:items-center">
                <Box title="1. Read" className="flex-1">
                  OCR and layout: words, lines, tables, with their position
                </Box>
                <Arrow />
                <Box title="2. Extract" className="flex-1 border-accent bg-accent-soft">
                  the {model} deployment fills the fields from your descriptions
                </Box>
                <Arrow />
                <Box title="3. Ground" className="flex-1">
                  links each value to its words, estimates a confidence
                </Box>
              </div>
            </div>
          </div>
          <p className="text-xs text-fg-muted">
            About 15 seconds for a one-page invoice. Content Understanding bills the pages; the tokens of step 2 are
            billed on your own model deployment. There are no keys: the backend signs in with your Azure login.
          </p>
        </section>

        <Step n={1} title="The analyzer is a list of described fields">
          <p className="max-w-3xl text-fg-muted">
            At startup the backend creates the analyzer <code>invoice_explorer</code>. Each field has a type, a
            description (this is the prompt) and a method. <code>extract</code> means: take the value literally from the
            page. <code>estimateSourceAndConfidence</code> asks for the score and the location.
          </p>
          <Code>{`{
  "baseAnalyzerId": "prebuilt-document",
  "models": { "completion": "${model}", "embedding": "text-embedding-3-large" },
  "fieldSchema": { "fields": {
    "InvoiceNumber": {
      "type": "string",
      "method": "extract",
      "description": "The invoice number.",
      "estimateSourceAndConfidence": true
    },
    "LineItems": { "type": "array", "items": { "type": "object", "properties": {
      "Description": { ... }, "Quantity": { ... }, "UnitPrice": { ... }, "Amount": { ... }
    } } }
  } }
}`}</Code>
        </Step>

        <Step n={2} title="The answer carries a value, a confidence and a source">
          <p className="max-w-3xl text-fg-muted">
            This is the invoice number of the sample as the service returned it. The source is a page number followed by
            four corners, in the units of the page (inches for a PDF, pixels for an image).
          </p>
          <div className="grid gap-3 lg:grid-cols-2">
            <Code>{`"InvoiceNumber": {
  "type": "string",
  "valueString": "2026-0147",
  "confidence": 0.989,
  "source": "D(1,6.8314,1.2192,7.4770,1.2183,
               7.4770,1.3542,6.8314,1.3535)"
}`}</Code>
            <div className="card space-y-2 text-sm">
              <div className="flex gap-3">
                <code className="w-24 shrink-0 text-accent">D(1, ...)</code>
                <span>page 1</span>
              </div>
              <div className="flex gap-3">
                <code className="w-24 shrink-0 text-accent">8 numbers</code>
                <span>x1,y1 to x4,y4: the corners, clockwise from top left</span>
              </div>
              <div className="flex gap-3">
                <code className="w-24 shrink-0 text-accent">;</code>
                <span>a value on two lines has two regions, joined with a semicolon</span>
              </div>
              <div className="flex gap-3">
                <code className="w-24 shrink-0 text-accent">0.989</code>
                <span>the service&apos;s estimate that the value is right, from 0 to 1</span>
              </div>
            </div>
          </div>
        </Step>

        <Step n={3} title="The box is the polygon, drawn in the page's own units">
          <p className="max-w-3xl text-fg-muted">
            The service says page 1 is {PAGE.width} by {PAGE.height} inches. The viewer lays an SVG over the page image
            with exactly that coordinate system, so the eight numbers go in unchanged. No conversion to pixels.
          </p>
          <PolygonFigure />
          <Code>{`<img src="page-1.png" />
<svg viewBox="0 0 ${PAGE.width} ${PAGE.height}">            <!-- page size in inches -->
  <polygon points="${POLYGON.join(' ')}" />
</svg>`}</Code>
        </Step>

        <Step n={4} title="The confidence decides what a human looks at">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="card border-ok">
              <div className="text-lg font-semibold text-ok">{bands.high}</div>
              <p className="text-fg-muted">Pass through. Header fields, totals and footer of the sample land here.</p>
            </div>
            <div className="card border-warn">
              <div className="text-lg font-semibold text-warn">{bands.medium}</div>
              <p className="text-fg-muted">
                Accepted, shown in amber. Most line item cells of the sample score 0.54 to 0.79 and are correct.
              </p>
            </div>
            <div className="card border-danger">
              <div className="text-lg font-semibold text-danger">{bands.low}</div>
              <p className="text-fg-muted">
                Counted as &quot;check those&quot;. Nothing in the sample scores this low.
              </p>
            </div>
          </div>
          <p className="max-w-3xl text-xs text-fg-muted">
            The thresholds are this app&apos;s choice (frontend/src/lib/confidence.ts), not the service&apos;s. The
            score barely changes with the chat model: gpt-6-luna and gpt-6.1-sol gave the same score on 34 of 38 values.
            A real workflow sets the thresholds per field from measured accuracy.
          </p>
        </Step>

        <footer className="border-t border-border pt-4 text-xs text-fg-muted">
          Where to look in the code: <code>src/content_understanding/extraction.py</code> (analyzer, call, result),{' '}
          <code>frontend/src/components/DocumentViewer.tsx</code> (the SVG overlay), <code>infra/main.bicep</code> (the
          Azure resources).
        </footer>
      </div>
    </div>
  )
}
