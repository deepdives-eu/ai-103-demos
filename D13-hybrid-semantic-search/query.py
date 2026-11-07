"""D13 step 2: the same question four ways, with both scores printed side by side.

  python query.py keyword    # full text only, BM25
  python query.py vector     # vector only, HNSW cosine similarity
  python query.py hybrid     # text + vector in one request, merged with RRF
  python query.py semantic   # hybrid + semantic ranker on top
  python query.py all        # all four, one after the other
  python query.py all --q "your own question"

The question is embedded once, client-side, and the same vector is reused.
For hybrid and semantic the vector side asks for k=50, because the semantic ranker
reranks up to 50 results; top=5 then limits what comes back.

Sources:
https://learn.microsoft.com/azure/search/search-get-started-vector?pivots=python
https://learn.microsoft.com/azure/search/hybrid-search-how-to-query
https://learn.microsoft.com/azure/search/hybrid-search-ranking
"""
import argparse

from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

from common import INDEX_NAME, SEARCH_ENDPOINT, SEMANTIC_CONFIG, VECTOR_FIELD, credential, embed

QUESTION = "quiet place to stay near the water where I can bring my dog"
TOP = 5
SELECT = ["id", "name", "category"]

search_client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=credential)


def keyword(q, _vector):
    return search_client.search(search_text=q, select=SELECT, top=TOP)


def vector(_q, v):
    vq = VectorizedQuery(vector=v, k_nearest_neighbors=TOP, fields=VECTOR_FIELD)
    return search_client.search(search_text=None, vector_queries=[vq], select=SELECT, top=TOP)


def hybrid(q, v):
    vq = VectorizedQuery(vector=v, k_nearest_neighbors=50, fields=VECTOR_FIELD)
    return search_client.search(search_text=q, vector_queries=[vq], select=SELECT, top=TOP)


def semantic(q, v):
    vq = VectorizedQuery(vector=v, k_nearest_neighbors=50, fields=VECTOR_FIELD)
    return search_client.search(
        search_text=q,
        vector_queries=[vq],
        select=SELECT,
        query_type="semantic",
        semantic_configuration_name=SEMANTIC_CONFIG,
        top=TOP,
    )


MODES = {
    "keyword": ("Keyword only (BM25)", keyword),
    "vector": ("Vector only (HNSW, cosine)", vector),
    "hybrid": ("Hybrid: keyword + vector, merged with RRF", hybrid),
    "semantic": ("Hybrid + semantic ranker", semantic),
}


def show(title, results):
    print(f"\n{title}")
    print(f"  {'#':<3}{'hotel':<28}{'@search.score':>15}{'@search.reranker_score':>25}")
    for rank, r in enumerate(results, start=1):
        reranker = r.get("@search.reranker_score")
        reranker_text = f"{reranker:.4f}" if reranker is not None else "-"
        print(f"  {rank:<3}{r['name']:<28}{r['@search.score']:>15.4f}{reranker_text:>25}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=[*MODES, "all"])
    parser.add_argument("--q", default=QUESTION, help="the question (default: the demo question)")
    args = parser.parse_args()

    print(f'Question: "{args.q}"')
    v = None if args.mode == "keyword" else embed([args.q])[0]
    for name in (MODES if args.mode == "all" else [args.mode]):
        title, run = MODES[name]
        show(title, run(args.q, v))


if __name__ == "__main__":
    main()
