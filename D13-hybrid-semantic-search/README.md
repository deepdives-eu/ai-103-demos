# D13 Hybrid and semantic search

deepdives.eu demo for AI-103 · our own material, not Microsoft Official Courseware.

Goes with the deepdives.eu video "Vision and extraction: what the exam adds" in the AI-103 playlist.

**Goal:** run one question against one Azure AI Search index four ways (keyword, vector, hybrid, hybrid plus semantic ranker) and see that the scores live on different scales.

## Exam skill

AI-103, "Implement information extraction solutions (10–15%)" > "Build retrieval and grounding pipelines":

> Configure semantic search, hybrid search, and vector search for grounding

It also touches "Plan and manage an Azure AI solution" > "Choose the appropriate Foundry services for generative AI and agents":

> Choose an appropriate method for retrieval and indexing

## What it costs and why

**This one is billed by the hour. Create it, do the demo, and delete it the same day.**

- **The search service.** Basic is a dedicated tier: you pay a fixed hourly rate for every hour the service exists, whether you query it or not. Learn's free-trial page puts Basic at about one third of a USD 200 trial credit over 30 days, so a forgotten Basic service uses up a large part of a monthly credit. Prices per region are on the Azure pricing page; check there first. `cleanup.sh` deletes the resource group, which stops the charge.
- **Semantic ranker.** Every new service starts on the semantic ranker **Free plan**: a monthly allowance of requests at no charge. When the allowance is used up, semantic queries return a billing error instead of a bill. This demo sends a handful of semantic queries. Don't switch the service to the Standard plan.
- **Embeddings.** One call for the 20 short hotel descriptions, then one small call per question, on the shared `text-embedding-3-small` deployment (Global Standard, pay per token). Negligible.
- Nothing else: no indexer, no skillset, no storage account.

**About the Free tier.** Learn disagrees with itself. The "Try Azure AI Search for free" page says Free doesn't support semantic ranking or managed identities. The region list says Sweden Central supports semantic ranker on the free tier, and the tier page says semantic ranker runs on Free. Only one Free service per subscription is allowed. Basic is the safe choice. If you want to try Free, run `SEARCH_SKU=free ./setup.sh`. It removes the hourly charge if the semantic query works. This demo doesn't need managed identity, because the embeddings are made client-side.

## Prerequisites

- The shared demo project from `../common/setup.sh` (Sweden Central, `text-embedding-3-small`, Global Standard) and `../common/demo.env` filled in.
- `az login` with an account that can create role assignments (Owner or User Access Administrator on the subscription). No keys anywhere.
- Python 3.10 or later.

**Region.** The search service is created in France Central by default (EU, semantic ranker available). Learn marks Sweden Central with "This region is in high demand, which prevents the creation of new search services", so it is not the default. To use another region that supports semantic ranker (see the regions page in Sources), set `SEARCH_LOCATION` when you run the script, for example `SEARCH_LOCATION=<region> ./setup.sh`. The search service never calls the Foundry resource in this demo, so its region can differ from the Foundry region. It only changes where the 20 made-up hotels are stored.

## Setup

```bash
cd D13-hybrid-semantic-search
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a; source ../common/demo.env; set +a
./setup.sh                       # rg-ai103-d13, search service <FOUNDRY>-d13, Basic, keys off, your roles
# wait 5 to 10 minutes for the role assignments
python create_index.py           # step 2
python query.py all              # step 7
```

`setup.sh` creates `rg-ai103-d13` with one search service, API keys disabled (`--disable-local-auth`), and gives you Search Service Contributor, Search Index Data Contributor and Search Index Data Reader on it, plus Cognitive Services OpenAI User on the shared Foundry resource for the embeddings call.

Use a terminal window at least 80 characters wide. The score table is about 75 characters.

## Files

| File | What it is |
| --- | --- |
| `hotels.json` | 20 made-up hotels: id, name, category, short description. Written for this demo |
| `common.py` | Names, `DefaultAzureCredential`, the OpenAI v1 client on the Foundry resource, the embeddings call |
| `create_index.py` | The index (text field, vector field, semantic configuration), embeddings for all 20 descriptions in one call, upload |
| `query.py` | The same question as `keyword`, `vector`, `hybrid`, `semantic` or `all`, printing `@search.score` and `@search.reranker_score` |
| `setup.sh` / `cleanup.sh` | Create and delete `rg-ai103-d13` |

## Steps

The question for all steps: **quiet place to stay near the water where I can bring my dog**.

### 1. The data and the question

Open `hotels.json`. Look at three hotels:

- h02 Pine Shore Cabins is what the question wants, but it never says "dog". It says "four-legged friends".
- h17 Seal Bay Cottages says "companions on four paws".
- h03 Hot Dog Corner Hostel says "dog" twice, and "place to stay". It is loud and doesn't take animals. That is the trap for keyword search.

### 2. One index, three parts

Open the `fields`, `vector_search` and `semantic_search` blocks in `create_index.py`. Then run:

```bash
python create_index.py
```

The index has three parts:

- A text field, `description`, for keyword search.
- A vector field next to it, 1536 numbers per hotel, because that is what `text-embedding-3-small` returns. It uses HNSW with cosine similarity, the default.
- A semantic configuration. It doesn't change the index. It tells the semantic ranker which fields to read: the name as title, the description as content.

The embeddings are made in your own code, in one call for all twenty. The alternative is a vectorizer in the index, so the service embeds the query for you (integrated vectorization). That means less code on the query side, but the search service then needs its own managed identity and a role on the model. This demo doesn't use it.

Expected output:

```text
Index 'd13-hotels' created on https://<foundry>-d13.search.windows.net
Embedded 20 descriptions, 1536 dimensions each
Uploaded 20 of 20 documents
```

Optional: in the portal, the search service > Settings > Keys shows role-based access control only. This service accepts Entra tokens only. The code uses `DefaultAzureCredential`.

If this step fails:

- `setup.sh` fails on the service create: the region may be full. Run it again with another `SEARCH_LOCATION`, see Prerequisites.
- 403 errors: the role assignments can take 5 to 10 minutes. Wait and run it again.
- Errors about class or parameter names from `azure-search-documents`: check that the installed version is 12.x (`pip show azure-search-documents`). The index uses plain type strings (`"Edm.String"`, `"Collection(Edm.Single)"`) to avoid the difference between `SearchFieldDataType.STRING` in the 12.0.0 readme and `.String` in the quickstarts.
- Errors on the embeddings call: the code uses `base_url=https://<FOUNDRY>.openai.azure.com/openai/v1/` with a bearer token for `https://ai.azure.com/.default`, as on Learn's embeddings page, which asks for the Cognitive Services OpenAI User role on the resource. `setup.sh` adds that role. Check that it exists and has propagated.

### 3. Keyword only

```bash
python query.py keyword
```

Keyword search is BM25. It looks for the words. The hostel has "dog", "place" and "stay", so it scores well, even though it is the worst answer here. The score is BM25: it starts at zero and has no upper limit. It only means something compared with other results of the same query.

Expected (roughly; the exact order depends on BM25 and the analyzer): Hot Dog Corner Hostel in the top two or three. Dune Retreat and Riverside Camping Pods near the top, because they contain "dog" and "quiet" or "water". Pine Shore Cabins and Seal Bay Cottages low or missing. The reranker column shows `-`.

### 4. Vector only

```bash
python query.py vector
```

The question becomes 1536 numbers, and the index returns the five nearest hotels. No words have to match. That is why Pine Shore Cabins and Seal Bay Cottages can come up: "four-legged friends" is close to "dog" in meaning. The score is cosine similarity, between 0.333 and 1. Different method, different scale.

Expected (roughly): Pine Shore Cabins, Seal Bay Cottages, Dune Retreat, Fjord View Lodge, Island Lighthouse Stay or Riverside Camping Pods in the top five. The hostel absent or low. Scores between 0.333 and 1. The reranker column shows `-`.

### 5. Hybrid in one request

Open the `hybrid` function in `query.py`, then run:

```bash
python query.py hybrid
```

Hybrid is keyword and vector in one request. `search_text` is the keyword part, `vector_queries` is the vector part. The service runs both in parallel and merges the two lists with Reciprocal Rank Fusion (RRF). RRF doesn't look at the original scores. It looks at positions. Each result gets 1 / (60 + rank) from each list, and those add up. A hotel that is high in both lists wins.

The best score is around 0.03. That is not a bad match. It is the most you can get with two lists. So never put a fixed threshold on a hybrid score.

Expected (roughly): Dune Retreat and Riverside Camping Pods near the top (good in both lists). Scores all small, the highest at or just under about 0.033. The reranker column shows `-`.

### 6. Hybrid plus semantic ranker

Open the `semantic` function in `query.py`: it adds two parameters. Then run:

```bash
python query.py semantic
```

It is the same hybrid request, plus `query_type="semantic"` and the name of the semantic configuration. The semantic ranker takes the merged results and reads them with a language model, against your question. It reorders them. The vector side asks for 50 results because the ranker works on up to 50, and you don't want to starve it.

You now get two scores. `@search.score` is still the RRF score from step 5. `@search.reranker_score` is new, and it is on a fixed scale, zero to four. That is the one to use for a quality cut-off.

Expected (roughly): the order changes compared with step 5. Hotels that clearly match "quiet, water, dog allowed" (Dune Retreat, Pine Shore Cabins, Seal Bay Cottages, Riverside Camping Pods) at the top, with reranker scores well above the rest. The hostel, if it is in the top five at all, with a clearly lower reranker score. `@search.score` still RRF-sized (around 0.01 to 0.033), `@search.reranker_score` between 0 and 4.

If this step fails with a billing error, you have used up the monthly semantic ranker Free plan allowance. Don't switch to the Standard plan for this demo. Wait for the next month or use another service.

### 7. All four side by side

```bash
python query.py all
```

Four lists, four scales. BM25 has no upper limit. Cosine runs from a third to one. RRF is tiny by design. The reranker goes from zero to four, in its own field. You can't compare these numbers across query types.

If you need a cut-off, use the reranker score. To prove that relevance got better, don't look at scores at all. Keep a fixed set of test questions with known good answers, and compare the results before and after.

Optional: try a question where keyword search does fine on its own:

```bash
python query.py all --q "hotel near the station for a business trip"
```

## Expected output (shape)

Layout only. Your numbers will differ.

```text
Question: "quiet place to stay near the water where I can bring my dog"

Hybrid + semantic ranker
  #  hotel                         @search.score   @search.reranker_score
  1  <hotel>                              0.0xxx                   x.xxxx
  2  <hotel>                              0.0xxx                   x.xxxx
  ...
```

## Cleanup (same day)

```bash
./cleanup.sh
az group exists -n rg-ai103-d13     # false when the delete has finished
```

This deletes `rg-ai103-d13`: the search service, the index and the role assignments on it. The hourly charge stops. The shared project `rg-ai103-demos` and the Cognitive Services OpenAI User assignment on it stay for the other demos. Check Cost Management the next day.

## Sources

Microsoft Learn:

- Vector quickstart for Python (index with vector field and semantic configuration, `VectorizedQuery`, hybrid and semantic hybrid queries, roles): https://learn.microsoft.com/azure/search/search-get-started-vector?pivots=python
- Semantic ranking quickstart for Python (`SemanticConfiguration`, `SemanticPrioritizedFields`, `@search.reranker_score`): https://learn.microsoft.com/azure/search/search-get-started-semantic?pivots=python
- Hybrid query how-to (k=50 with semantic ranker, RRF score example): https://learn.microsoft.com/azure/search/hybrid-search-how-to-query
- RRF and score ranges (BM25 no upper limit, cosine 0.333 to 1, reranker 0 to 4): https://learn.microsoft.com/azure/search/hybrid-search-ranking
- Hybrid search overview: https://learn.microsoft.com/azure/search/hybrid-search-overview
- Semantic ranking overview (top 50, billing): https://learn.microsoft.com/azure/search/semantic-search-overview
- Semantic ranker Free and Standard plans: https://learn.microsoft.com/azure/search/semantic-how-to-enable-disable
- Regions (semantic ranker in Sweden Central, high-demand footnote): https://learn.microsoft.com/azure/search/search-region-support
- Tiers and billing (Basic hourly, feature availability by tier): https://learn.microsoft.com/azure/search/search-sku-tier
- Free tier and Basic credit use: https://learn.microsoft.com/azure/search/search-try-for-free
- Enable roles, disable API keys (`--disable-local-auth`), role propagation time: https://learn.microsoft.com/azure/search/search-security-enable-roles
- Search roles: https://learn.microsoft.com/azure/search/search-security-rbac
- `az search service create`: https://learn.microsoft.com/azure/search/search-manage-azure-cli
- Python client library, version 12.0.0: https://learn.microsoft.com/python/api/overview/azure/search-documents-readme
- `VectorizedQuery` (GA reference): https://learn.microsoft.com/python/api/azure-search-documents/azure.search.documents.models.vectorizedquery
- Embeddings with Entra ID on the v1 endpoint, Cognitive Services OpenAI User: https://learn.microsoft.com/azure/foundry/openai/how-to/embeddings
- Azure OpenAI vectorizer (integrated vectorization, managed identity): https://learn.microsoft.com/azure/search/vector-search-vectorizer-azure-open-ai
- AI-103 study guide: https://learn.microsoft.com/credentials/certifications/resources/study-guides/ai-103

Other:

- Azure AI Search pricing (regional rates): https://azure.microsoft.com/pricing/details/search/

Checked against Learn on 2026-11-07.
