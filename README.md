# Content Understanding Explorer

Upload an invoice (PDF, PNG or JPEG) and see what Azure Content Understanding extracts from it in one call: the
header, the line items, the totals and the payment footer. Every value comes with a confidence score and the place
on the page it was read from, drawn as a box over the document. Built to explore the service, for one user on a
laptop.

## Run it

```bash
scripts/azure-up.sh        # once: creates rg-geert-content-understanding (Sweden Central) and prints the endpoint
# put the printed CONTENT_UNDERSTANDING_ENDPOINT=... line in .env (copy .env.example first)
scripts/run-local.sh       # http://localhost:8809
```

Sign-in to Azure is your `az login`; the deployment gives your user the "Cognitive Services User" role on the
resource. A new role assignment can take a few minutes before the first call works.

Remove the Azure resources with `az group delete --name rg-geert-content-understanding`.

## How it works

1. `infra/main.bicep` deploys a Foundry resource with `gpt-6-luna` (used by the app), `gpt-6.1-sol` (to compare) and
   `text-embedding-3-large`. Content Understanding
   bills pages itself and uses these deployments for the generative step.
2. On the first upload the backend maps those deployments as the resource defaults and creates the analyzer
   `invoice_explorer` from `SECTIONS` in `src/content_understanding/extraction.py`. Every field uses the `extract`
   method with `estimateSourceAndConfidence`.
3. `POST /api/extract` sends the file to the analyzer (about 15 seconds for one page) and returns the fields per
   section, each with a confidence (0 to 1) and its regions: a page number and a four-corner polygon in the page's
   own units (inches for a PDF, pixels for an image). It also returns each page as an image.
4. The page draws the polygons in an SVG over the page image. Hover a value to light up its box, click to scroll to it.

To extract other fields, edit `SECTIONS` and restart: the analyzer is replaced at startup.

## What we learned

[docs/learnings.md](docs/learnings.md): how the service works, what we measured on the sample invoice (accuracy,
confidence per section, three chat models), what is still open.

## Develop

```bash
scripts/check.sh [--fix]   # the quality gate: ruff, pyright, pytest, generated API client, prettier, oxlint, build
scripts/run-local.sh --dev # Vite hot reload on :5173
```

Tests use a result recorded from the real service (`tests/data/invoice_result.json`) and never call Azure.
