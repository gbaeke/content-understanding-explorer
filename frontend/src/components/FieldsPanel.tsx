import type { Extraction, Field } from '@/client/types.gen'
import { REVIEW_BELOW, display, label, level, levelClass, percent } from '@/lib/confidence'
import { rowId } from '@/lib/dom-ids'
import { cn } from '@/lib/utils'

interface Props {
  extraction: Extraction
  fields: Field[]
  active: string | null
  onHover: (fieldId: string | null) => void
  onSelect: (fieldId: string) => void
}

function Value({ field }: { field: Field }) {
  const text = display(field)
  return text ? <span className="break-words">{text}</span> : <span className="text-fg-muted italic">not found</span>
}

function Confidence({ field }: { field: Field }) {
  return (
    <span className={cn('shrink-0 text-xs font-medium tabular-nums', levelClass[level(field.confidence)].text)}>
      {percent(field.confidence)}
    </span>
  )
}

export function FieldsPanel({ extraction, fields, active, onHover, onSelect }: Props) {
  const review = fields.filter((f) => f.confidence !== null && f.confidence < REVIEW_BELOW).length
  const hover = (field: Field) => ({
    id: rowId(field.id),
    onMouseEnter: () => onHover(field.id),
    onMouseLeave: () => onHover(null),
    onClick: () => onSelect(field.id),
  })

  return (
    <div className="space-y-4">
      <p className="text-fg-muted">
        {fields.length} values extracted.{' '}
        {review === 0 ? (
          'None is below the review threshold.'
        ) : (
          <span className="text-danger">
            {review} below {percent(REVIEW_BELOW)} confidence: check those.
          </span>
        )}{' '}
        Hover a value to see where it comes from.
      </p>

      {extraction.sections.map((section) => (
        <section key={section.title} className="card overflow-x-auto p-0">
          <h2 className="border-b border-border px-4 py-2 font-semibold">{section.title}</h2>
          {section.fields.length > 0 && (
            <dl>
              {section.fields.map((field) => (
                <div
                  key={field.id}
                  {...hover(field)}
                  className={cn(
                    'flex cursor-pointer items-baseline gap-3 border-b border-border px-4 py-1.5 last:border-b-0',
                    field.id === active && 'bg-accent-soft',
                  )}
                >
                  <dt className="w-36 shrink-0 text-fg-muted">{label(field.name)}</dt>
                  <dd className="min-w-0 flex-1">
                    <Value field={field} />
                  </dd>
                  <Confidence field={field} />
                </div>
              ))}
            </dl>
          )}
          {section.table &&
            (section.table.rows.length === 0 ? (
              <p className="px-4 py-2 text-fg-muted italic">not found</p>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="text-left text-fg-muted">
                    {section.table.columns.map((column) => (
                      <th key={column} className="px-3 py-1.5 font-normal first:pl-4 last:pr-4">
                        {label(column)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {section.table.rows.map((row, index) => (
                    <tr key={index} className="border-t border-border align-top">
                      {row.map((cell) => (
                        <td
                          key={cell.id}
                          {...hover(cell)}
                          className={cn(
                            'cursor-pointer px-3 py-1.5 first:pl-4 last:pr-4',
                            cell.id === active && 'bg-accent-soft',
                          )}
                        >
                          <div>
                            <Value field={cell} />
                          </div>
                          <Confidence field={cell} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ))}
        </section>
      ))}
    </div>
  )
}
