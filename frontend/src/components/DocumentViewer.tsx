import type { Field, Page } from '@/client/types.gen'
import { level, levelClass, label, percent } from '@/lib/confidence'
import { boxId } from '@/lib/dom-ids'
import { cn } from '@/lib/utils'

interface Props {
  pages: Page[]
  fields: Field[]
  active: string | null
  onHover: (fieldId: string | null) => void
  onSelect: (fieldId: string) => void
}

/** The pages as images, each under an SVG in the page's own units: a region's polygon is drawn as it came. */
export function DocumentViewer({ pages, fields, active, onHover, onSelect }: Props) {
  return (
    <div className="space-y-4">
      {pages.map((page) => (
        <div
          key={page.number}
          className="relative mx-auto max-w-3xl overflow-hidden rounded-md border border-border shadow-sm"
        >
          <img src={page.image} alt={`Page ${page.number}`} className="block w-full bg-white" />
          <svg
            viewBox={`0 0 ${page.width} ${page.height}`}
            preserveAspectRatio="none"
            className="absolute inset-0 size-full"
          >
            {fields.flatMap((field) =>
              field.regions
                .filter((region) => region.page === page.number)
                .map((region, index) => {
                  const cls = levelClass[level(field.confidence)]
                  return (
                    <polygon
                      key={`${field.id}-${index}`}
                      id={index === 0 ? boxId(field.id) : undefined}
                      points={region.polygon.join(' ')}
                      vectorEffect="non-scaling-stroke"
                      className={cn(
                        'cursor-pointer transition-colors',
                        field.id === active ? cn(cls.boxActive, 'stroke-2') : cn(cls.box, 'stroke-1'),
                      )}
                      onMouseEnter={() => onHover(field.id)}
                      onMouseLeave={() => onHover(null)}
                      onClick={() => onSelect(field.id)}
                    >
                      <title>{`${label(field.name)} (${percent(field.confidence)})`}</title>
                    </polygon>
                  )
                }),
            )}
          </svg>
        </div>
      ))}
    </div>
  )
}
