# What we have not explored yet

The sample uses one slice of Azure Content Understanding: a custom document analyzer with `extract` fields,
confidence and page regions, on one clean one-page PDF. This list covers the rest, ordered by how much each item
would teach. The descriptions come from Microsoft Learn (November 2026) and are not tested here. What we did test
is in [learnings.md](learnings.md).

## Closest to what we built

| Feature | What it would show |
|---|---|
| `generate` and `classify` fields | Values that need inference or cleaning (a summary, "is this invoice overdue", a category from an enum), and how their confidence and regions compare with `extract`. |
| Labeled samples | Whether a few corrected examples raise the low line item scores. This is the open question from our measurements. |
| The Markdown output | The same call already returns the document as Markdown with tables. The app ignores it. It is the direct replacement for a Document Intelligence layout step. |
| Prebuilt analyzers | `prebuilt-invoice` on the same sample, against our hand-written schema. Also receipt, contract, ID document, bank statement. |
| Schema helpers | `prebuilt-documentFieldSchema` proposes fields for an unknown document. `prebuilt-documentFields` extracts key-value pairs with no schema. |

## Multi-document workflows

| Feature | What it would show |
|---|---|
| Classification and splitting | One PDF with an invoice, a contract and a delivery note: split it, label each part, route each to its own analyzer. Up to 200 categories, in one call (`contentCategories`, `enableSegment`). |
| In-page segmentation (preview) | Two document types on a single page. |

## Preview features (`2026-06-01-preview`)

| Feature | What it would show |
|---|---|
| Agentic mode | Reasoning across a document: check that line items add up to the total, validate against rules, compare a contract with its amendment. Slower, and needs about 400,000 tokens per minute on the model deployment. It rejects `extract` fields and labeled samples, and takes one input file per request. |
| Signature detection | Location of signatures on contracts. |
| Document metadata | Author, creation date and title embedded in the file. |
| Synchronous Read and Layout | OCR without polling, for small documents. |

## Layout details and RAG

| Feature | What it would show |
|---|---|
| `prebuilt-documentSearch` | Markdown plus a summary, figure descriptions, and charts turned into chart.js or diagrams into mermaid. Chunking for a vector index. |
| Layout elements | Tables as structures, selection marks, barcodes, formulas as LaTeX, handwritten annotations, hyperlinks. |
| Other input formats | Office documents, multi-page PDFs, phone photos, scans. |

## Other modalities

| Feature | What it would show |
|---|---|
| Audio | Transcripts with speakers, call-center analysis (summary, sentiment, entities). |
| Video | Scene segmentation with a description and transcript per segment. |
| Images | Descriptions and fields from a picture without text. |

Confidence and page regions exist for documents only.

## Operations

- **Cost per document.** The result has a `usage` object with pages and tokens. The app never reads it.
- **Analyzer lifecycle.** Copying analyzers between resources, versioning, deleting results for data retention.
- **Integrations.** The Azure AI Search skill, Logic Apps, LangChain, Agent Framework, and the `azd ai cu` command
  line.
- **Content Understanding Studio.** The browser tool for building and labeling analyzers. Everything here was done
  in code.

## Suggested order

1. **Degraded documents plus labeled samples.** Run blurred, rotated and photographed versions of the sample, and
   real invoices with known answers. Tabulate confidence against correctness, then add labeled samples and
   measure again. This settles whether the confidence score is usable for routing values to a human, which is the
   main advantage over a hand-built pipeline.
2. **Classification and splitting.** It is the other part a hand-built pipeline has to implement itself, and it
   fits the existing viewer: boxes per segment, a label per part.
3. **Agentic mode on the invoice.** "Do the line items add up to the subtotal, and is the VAT 21% of it" is a
   small, visual test of the reasoning feature.
