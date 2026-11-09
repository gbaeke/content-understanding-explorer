# Content Understanding Explorer

Upload an invoice (PDF, PNG or JPEG) and see what Azure Content Understanding extracts from it in one call: the
header, the line items, the totals and the payment footer. Every value comes with a confidence score and the place
on the page it was read from, drawn as a box over the document. Built to explore the service, for one user on a
laptop.

## Content Understanding in one minute

Azure Content Understanding is a service that turns a document into structured data with a generative model. If
you know Azure Document Intelligence: that service reads a document and returns its text and layout, and you then
prompt an LLM yourself to get fields out. Content Understanding does both steps in one call.

Four terms come back in this repository:

| Term | Meaning |
|---|---|
| Foundry resource | The Azure resource that hosts Content Understanding (`Microsoft.CognitiveServices/accounts`, kind `AIServices`). There is no separate Content Understanding resource. |
| Model deployment | A chat model (here a GPT model) deployed inside that Foundry resource. Content Understanding calls it to fill the fields, and you pay its tokens. |
| Analyzer | A definition you create once in the service: which fields you want, each with a type and a description in plain language. The description works as the prompt. |
| Confidence and source | Per value: a score from 0 to 1, and the page number plus four corner points where the value was found. |

## What you need

- An Azure subscription where you can create a resource group and a role assignment (Owner, or Contributor plus
  User Access Administrator).
- The Azure CLI, signed in: `az login`.
- [uv](https://docs.astral.sh/uv/) and Node.js 24 or newer.
- Quota for the chat models in `infra/main.bicep` in Sweden Central. Change the `chatModels` parameter if you have
  quota for other models; the app accepts any chat model Content Understanding supports.

Cost: the Foundry resource and idle model deployments cost nothing. Each analysis is billed per page by Content
Understanding, plus the tokens the chat model uses ([docs/learnings.md](docs/learnings.md) has the pricing parts).

## Run it

1. Create the Azure resources. This takes a few minutes and prints the endpoint of the Foundry resource.

   ```bash
   scripts/azure-up.sh
   ```

   It creates the resource group `rg-geert-content-understanding` in Sweden Central, a Foundry resource, the model
   deployments, and gives your user the "Cognitive Services User" role on the resource. Pass another name and
   region as arguments: `scripts/azure-up.sh my-rg westeurope`.

2. Copy `.env.example` to `.env` and set the line the script printed:

   ```
   CONTENT_UNDERSTANDING_ENDPOINT=https://<your-resource>.services.ai.azure.com/
   ```

3. Start the app and open http://localhost:8809.

   ```bash
   scripts/run-local.sh
   ```

4. Click **Use the sample invoice**, or upload your own. After about 15 seconds the document appears on the left
   and the extracted values on the right. Hover a value to see its box on the page.

There are no keys. The app signs in to Azure with your `az login`. A new role assignment can take a few minutes
before the first call works; an error in the first minutes usually means that.

Remove the Azure resources with `az group delete --name rg-geert-content-understanding`.

## How it works

The app has a visual explanation of its own: the **How it works** link in the header. In short:

1. **First upload after a start.** The backend tells the Foundry resource which model deployments to use, and
   creates the analyzer `invoice_explorer`. The fields come from `SECTIONS` in
   `src/content_understanding/extraction.py`. The chat model is `COMPLETION_MODEL` in the same file; the header of
   the app shows it.
2. **Upload.** `POST /api/extract` sends the file to the analyzer. The service reads the page, fills the fields
   with the chat model, and links every value back to the words on the page.
3. **Answer.** The backend returns the values per section, each with a confidence and its regions: a page number
   and a four-corner polygon in the page's own units (inches for a PDF, pixels for an image). It also returns
   each page as an image.
4. **Viewer.** The browser draws the polygons in an SVG over the page image.

To extract other fields, edit `SECTIONS` and restart: the analyzer is replaced at startup. The app is not tied to
invoices beyond that list.

## What we learned

[docs/learnings.md](docs/learnings.md): how the service works, what we measured on the sample invoice (accuracy,
confidence per section, three chat models), and what is still open. The main finding: the confidence score barely
depends on the chat model, and it runs low on table cells that are correct.

## Develop

```bash
scripts/check.sh [--fix]   # the quality gate: ruff, pyright, pytest, generated API client, prettier, oxlint, build
scripts/run-local.sh --dev # Vite hot reload on :5173
```

Tests use a result recorded from the real service (`tests/data/invoice_result.json`) and never call Azure.

| What | Where |
|---|---|
| Analyzer definition, call to the service, result parsing | `src/content_understanding/extraction.py` |
| HTTP endpoints | `src/content_understanding/api/extract.py` |
| Page viewer with the box overlay | `frontend/src/components/DocumentViewer.tsx` |
| Azure resources | `infra/main.bicep`, `scripts/azure-up.sh` |
| Sample invoice and its generator | `samples/invoice.pdf`, `scripts/make_sample_invoice.py` |
