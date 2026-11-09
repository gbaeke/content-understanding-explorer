import type { Field } from '@/client/types.gen'

/**
 * The two thresholds, for the colours, the summary and the legend. They are set from what the sample invoice showed:
 * correct values score as low as 0.54 (table cells), so 0.8 and up is green and only a score below 0.5 asks for a
 * human. A real workflow measures them per field on documents with known answers.
 */
export const HIGH = 0.8
export const REVIEW_BELOW = 0.5

export type Level = 'high' | 'medium' | 'low' | 'none'

export function level(confidence: number | null): Level {
  if (confidence === null) return 'none'
  if (confidence >= HIGH) return 'high'
  return confidence >= REVIEW_BELOW ? 'medium' : 'low'
}

/** Text, box outline and box fill per level: the design tokens ok / warn / danger. */
export const levelClass: Record<Level, { text: string; box: string; boxActive: string }> = {
  high: { text: 'text-ok', box: 'stroke-ok/50 fill-ok/5', boxActive: 'stroke-ok fill-ok/25' },
  medium: { text: 'text-warn', box: 'stroke-warn/50 fill-warn/5', boxActive: 'stroke-warn fill-warn/25' },
  low: { text: 'text-danger', box: 'stroke-danger/50 fill-danger/5', boxActive: 'stroke-danger fill-danger/25' },
  none: {
    text: 'text-fg-muted',
    box: 'stroke-fg-muted/50 fill-transparent',
    boxActive: 'stroke-fg-muted fill-fg-muted/25',
  },
}

/** The three bands in words, for the legend and the explanation page. */
export const bands = {
  high: `${HIGH * 100}% and up`,
  medium: `${REVIEW_BELOW * 100} to ${HIGH * 100 - 1}%`,
  low: `below ${REVIEW_BELOW * 100}%`,
}

export const percent = (confidence: number | null) => (confidence === null ? 'n/a' : `${Math.round(confidence * 100)}%`)

/** "VendorVatNumber" -> "Vendor vat number" */
export const label = (name: string) => {
  const words = name.replace(/([a-z])([A-Z])/g, '$1 $2').toLowerCase()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

export function display(field: Field): string {
  if (field.value === null || field.value === '') return ''
  if (typeof field.value === 'number') return field.value.toLocaleString(undefined, { maximumFractionDigits: 2 })
  return String(field.value)
}
