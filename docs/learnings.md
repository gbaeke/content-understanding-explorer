# What we learned about Azure Content Understanding

Notes from building the invoice explorer on 9 November 2026. Everything under "Measured" comes from runs against
our own Foundry resource with `samples/invoice.pdf`. Everything under "From the docs" comes from Microsoft Learn
and was not tested here. Inferences are marked as such.

## The short version

- Content Understanding (CU) replaces the old two-step pipeline (Document Intelligence to Markdown, then a prompt
  to an LLM) with one call. You define an analyzer with described fields and get typed values back.
- The part the old pipeline could not do: every value comes with a confidence score and the place on the page it
  was read from.
- On a clean one-page invoice all 38 values were correct, in about 15 seconds.
- The confidence score barely depends on the chat model. It also runs low on table cells that are correct. Do not
  read it as "probability the value is right" without measuring it on your own documents.

## How the service works

| Concept | What it is |
|---|---|
| Foundry resource | CU lives in a Microsoft Foundry resource (`kind: AIServices`). There is no separate CU resource. |
| Model deployments | CU calls chat and embedding models that you deploy in the same resource. You pay their tokens. |
| Defaults | A one-time `PATCH /contentunderstanding/defaults` maps model names to your deployment names. |
| Analyzer | A JSON definition: a base analyzer, a `config`, the models, and a `fieldSchema`. |
| Field | A name, a type, a description and a method. The description is the prompt. |
| Method | `extract` takes the value literally from the page. `classify` picks from an enum. `generate` infers or summarises. |
| Result | Markdown of the document, plus the fields. Each field can carry `confidence` and `source`. |

A custom document analyzer inherits from `prebuilt-document`. To get scores and locations, set
`estimateSourceAndConfidence` on a field, or `estimateFieldSourceAndConfidence` in the analyzer config.

API versions: `2025-11-01` is GA. `2026-06-01-preview` adds agentic mode, signature detection, document metadata,
in-page segmentation and synchronous Read and Layout calls.

## The result format

This is the invoice number of the sample, as returned:

```json
"InvoiceNumber": {
  "type": "string",
  "valueString": "2026-0147",
  "confidence": 0.989,
  "source": "D(1,6.8314,1.2192,7.4770,1.2183,7.4770,1.3542,6.8314,1.3535)"
}
```

- `source` is `D(page, x1, y1, x2, y2, x3, y3, x4, y4)`: a page number and four corners, clockwise from top left.
- The coordinates use the unit of the page: inches for a PDF, pixels for an image. The result gives each page's
  width and height in the same unit (the A4 sample is 8.2639 by 11.6806).
- A value that spans two lines has two regions, joined with a semicolon.
- The value key depends on the type: `valueString`, `valueNumber`, `valueDate`, `valueArray`, `valueObject`.
- Dates and numbers are normalised: "3 November 2026" comes back as `2026-11-03`, "1.250,00" as `1250`. The raw
  text is not returned next to it.

Drawing the boxes needs no conversion. The viewer puts an SVG with `viewBox="0 0 <width> <height>"` over the page
image and passes the eight numbers straight into a `<polygon>`.

## Measured on the sample invoice

One clean, computer-generated, one-page invoice with 18 header, totals and footer fields and 4 line items of 5
cells: 38 values.

### Accuracy and speed

- All 38 values were correct in every run, with every model.
- Every value had at least one page region.
- One call took 13 to 17 seconds.

### Confidence per section

| Section | Lowest | Average |
|---|---|---|
| Header | 0.86 to 0.89 | 0.93 to 0.95 |
| Line items | 0.54 | 0.72 |
| Totals | 0.96 | 0.97 |
| Footer | 0.89 | 0.94 |

Line item cells score 0.54 to 0.88 although they are correct. The VAT rate column is lowest, around 0.55.

### The chat model does not move the confidence

| Model | Runs | Line items average | Values below 0.8 |
|---|---|---|---|
| `gpt-5.2` | 2 | 0.72 | 14 of 38 |
| `gpt-6-luna` | 1 | 0.72 | 14 of 38 |
| `gpt-6.1-sol` | 2 | 0.72 | 14 of 38 |

Between `gpt-6-luna` and `gpt-6.1-sol`, 34 of 38 scores were identical to three decimals. The four that differed
were the two addresses, where the models returned slightly different text (with or without a comma between the
lines).

Inference: the score is computed by the service after the model answers, from how well the value matches the
words it read on the page. It is not the model's own certainty. Microsoft does not document the calculation. The
practical consequence is that a stronger model will not lift low scores.

### `extract` is not fully repeatable

The same document gave `BE 0712.345.678` in one run and `VAT BE 0712.345.678` in another. The same happened with
the "IBAN" and "BIC" labels in front of those values. If the exact text matters, say so in the field description
(for example "without the VAT prefix") or clean it up after extraction.

### Thresholds

The first version of the app flagged everything below 0.8 for review, which asked a human to check 14 correct
values. The thresholds are now 0.8 and up for green and below 0.5 for review (`frontend/src/lib/confidence.ts`).

These numbers are fitted to one document where nothing went wrong. That shows how low a correct value can score.
It does not show how a wrong value scores, which is what a review threshold depends on. See "Open questions".

## Models

The live service lists these chat models for `prebuilt-document` (read with `GET analyzers/prebuilt-document`):

| Family | Models |
|---|---|
| GPT-6 | `gpt-6.1-sol`, `gpt-6-sol`, `gpt-6-luna`, `gpt-6-astra` |
| GPT-5.6 | `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna` |
| GPT-5 | `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.2`, `gpt-5.1`, `gpt-5`, `gpt-5-mini`, `gpt-5-nano` |
| GPT-4.1 | `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano` |
| GPT-4o | `gpt-4o`, `gpt-4o-mini` |

- **GPT-6 works on the GA API.** The docs list the GPT-6 and GPT-5.6 models for the preview API only. We ran
  `gpt-6-luna` and `gpt-6.1-sol` on `2025-11-01` without a problem.
- **Claude is not supported.** Claude models exist in Foundry, but CU only accepts OpenAI models. Using Claude
  means going back to two steps: `prebuilt-layout` for Markdown, then your own prompt. You lose the built-in
  confidence and page regions.
- **The embedding model is only used with labeled samples.** CU embeds your example documents to find the ones
  most similar to the incoming document. This sample has none. We set an embedding model because Microsoft's SDK
  sample marks it as required; we did not test leaving it out.
- **Analyzer `models` takes model names, not deployment names.** The defaults map one to the other. Here both are
  the same string.

## Building against it

- **SDK:** `azure-ai-contentunderstanding` 1.1.0. `begin_create_analyzer` accepts a plain dict in REST casing, so
  the analyzer definition in code looks like the JSON in the docs. `begin_analyze_binary` takes the file bytes.
  `poller.result().as_dict()` gives the raw result.
- **No keys:** the resource has `disableLocalAuth: true`. The app uses `DefaultAzureCredential` (your `az login`)
  and the user needs the "Cognitive Services User" role on the resource.
- **Region:** CU is available in 12 regions, including Sweden Central and West Europe.
- **Bicep:** model deployments on one account must be created one at a time (`@batchSize(1)` on the loop, and
  `dependsOn` between separate resources). Bicep does not remove a deployment you drop from the template: the
  unused `gpt-5.2` deployment is still there.
- **Changing the schema or the model:** the app recreates the analyzer at startup with `allow_replace=True`, so
  edit `SECTIONS` or `COMPLETION_MODEL` in `extraction.py` and restart.
- **One unexplained failure:** the first call after switching the analyzer to `gpt-6.1-sol` failed with
  "the OpenAI deployment 'gpt-6-luna' does not exist", although that deployment existed. The next call succeeded
  with no change.
- **Tests:** they use a result recorded from the real service (`tests/data/invoice_result.json`) and a fake
  analyzer. They never call Azure.

## From the docs, not tested here

- **Pricing has three parts:** content extraction per page, contextualization (about $1 per 1,000 pages standard,
  $3 advanced), and the tokens on your own model deployment.
- **When Microsoft recommends Document Intelligence instead:** high-volume, fixed-layout forms where you want
  deterministic output and low latency, and on-premises containers. For plain OCR or layout, CU's `prebuilt-read`
  and `prebuilt-layout` need no LLM and are positioned as the cheaper replacement.
- **Prebuilt analyzers:** invoice, receipt, contract, ID document, bank statement, purchase order, US tax and
  mortgage forms. They can be extended with extra fields.
- **Classification and splitting:** `contentCategories` and `enableSegment` split a mixed PDF, classify each part
  (up to 200 categories) and route each to its own analyzer, in one call.
- **Schema helpers:** `prebuilt-documentFieldSchema` proposes a field schema for a document.
  `prebuilt-documentFields` extracts key-value pairs without a schema.
- **Labeled samples:** corrected example documents raise accuracy. The docs present them as the way to handle new
  formats and low confidence.
- **Agentic mode (preview):** `config.workflow: "agentic"` reasons across a document for calculations and
  validation. It uses the advanced rate, needs about 400,000 tokens per minute, rejects `extract` fields and
  labeled samples, and takes one input file per request.
- **Other modalities:** audio (transcripts with speakers), video (scene segments) and images use the same field
  schema idea. Confidence and page regions are for documents only.

## Open questions

1. **How do wrong values score?** Run degraded versions of the sample (blurred, rotated, a phone photo, a
   low-resolution scan) and real invoices with known answers, then tabulate confidence against correctness. Without
   this the review threshold is a guess.
2. **Do labeled samples raise the line item scores?** The docs suggest they calibrate confidence.
3. **Is the embedding model required** for an analyzer without labeled samples?
4. **Does a cheaper model keep the accuracy?** `gpt-5.4-mini` or a nano model on harder documents. The confidence
   will not tell, so this needs a labeled test set.
5. **How does `generate` compare with `extract`** on confidence and regions, for values that need cleaning or
   inference?
6. **Other document types:** the app is invoice-only because of `SECTIONS`. A schema editor in the page, with
   `prebuilt-documentFieldSchema` proposing the fields, would turn it into an explorer for any document.
7. **Classification and agentic mode** are untouched.

## Where things are

| What | Where |
|---|---|
| Analyzer definition, call, result parsing | `src/content_understanding/extraction.py` |
| Upload and info endpoints | `src/content_understanding/api/extract.py` |
| Page viewer with the SVG overlay | `frontend/src/components/DocumentViewer.tsx` |
| Confidence thresholds | `frontend/src/lib/confidence.ts` |
| Visual explanation in the app | `/how-it-works` (`frontend/src/pages/HowItWorks.tsx`) |
| Azure resources | `infra/main.bicep`, `scripts/azure-up.sh` |
| Sample invoice and its generator | `samples/invoice.pdf`, `scripts/make_sample_invoice.py` |

Azure: resource group `rg-geert-content-understanding` in Sweden Central, one Foundry resource with deployments
`gpt-6-luna`, `gpt-6.1-sol`, `gpt-5.2` (unused) and `text-embedding-3-large`.
