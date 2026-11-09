import { useMutation } from '@tanstack/react-query'
import { FileText, LoaderCircle, Upload } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'
import { extractMutation } from '@/client/@tanstack/react-query.gen'
import { DocumentViewer } from '@/components/DocumentViewer'
import { FieldsPanel } from '@/components/FieldsPanel'
import { errorMessage } from '@/lib/api'
import { bands } from '@/lib/confidence'
import { boxId, rowId } from '@/lib/dom-ids'

const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' })

export function Explorer() {
  const input = useRef<HTMLInputElement>(null)
  const [name, setName] = useState('')
  const [active, setActive] = useState<string | null>(null)
  const extraction = useMutation({
    ...extractMutation(),
    onError: (error) => toast.error(errorMessage(error)),
  })

  const analyze = (file: File) => {
    setName(file.name)
    setActive(null)
    extraction.mutate({ body: { file } })
  }
  const analyzeSample = async () => {
    try {
      const res = await fetch('/api/sample')
      if (!res.ok) throw new Error('The sample invoice is missing.')
      analyze(new File([await res.blob()], 'invoice.pdf (sample)', { type: 'application/pdf' }))
    } catch (error) {
      toast.error(errorMessage(error))
    }
  }

  const data = extraction.data
  // every value in one list, in the order of the panel
  const fields = useMemo(
    () => (data ? data.sections.flatMap((s) => [...s.fields, ...(s.table?.rows.flat() ?? [])]) : []),
    [data],
  )

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 flex-wrap items-center gap-3 border-b border-border bg-surface px-6 py-3">
        <input
          ref={input}
          type="file"
          accept="application/pdf,image/png,image/jpeg"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) analyze(file)
            e.target.value = '' // the same file can be chosen again
          }}
        />
        <button className="btn-primary" disabled={extraction.isPending} onClick={() => input.current?.click()}>
          <Upload className="size-4" />
          Upload a document
        </button>
        <button className="btn-ghost" disabled={extraction.isPending} onClick={analyzeSample}>
          <FileText className="size-4" />
          Use the sample invoice
        </button>
        {extraction.isPending ? (
          <span className="flex items-center gap-2 text-fg-muted">
            <LoaderCircle className="size-4 animate-spin" />
            Analyzing {name}. This takes about 15 seconds.
          </span>
        ) : (
          data && <span className="text-fg-muted">{name}</span>
        )}
        <span className="ml-auto flex items-center gap-3 text-xs text-fg-muted">
          Confidence:
          <span className="text-ok">{bands.high}</span>
          <span className="text-warn">{bands.medium}</span>
          <span className="text-danger">{bands.low}</span>
        </span>
      </div>

      {data ? (
        <div className="flex min-h-0 flex-1">
          <div className="min-w-0 flex-1 overflow-auto bg-muted p-6">
            <DocumentViewer
              pages={data.pages}
              fields={fields}
              active={active}
              onHover={setActive}
              onSelect={(id) => scrollTo(rowId(id))}
            />
          </div>
          <div className="w-[34rem] shrink-0 overflow-auto border-l border-border p-4">
            <FieldsPanel
              extraction={data}
              fields={fields}
              active={active}
              onHover={setActive}
              onSelect={(id) => scrollTo(boxId(id))}
            />
          </div>
        </div>
      ) : (
        <div className="flex flex-1 items-center justify-center p-6 text-center text-fg-muted">
          {extraction.isPending ? null : (
            <p className="max-w-md">
              Upload an invoice (PDF, PNG or JPEG) or use the sample. Azure Content Understanding extracts the header,
              the line items, the totals and the payment footer, and the page shows where each value was found.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
