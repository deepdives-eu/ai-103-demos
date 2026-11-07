"""D13 step 1: create the index and load 20 made-up hotels with their embeddings.

One index with three things in it:
- a text field (description) for keyword search, BM25,
- a vector field (descriptionVector) for vector search, HNSW with cosine,
- a semantic configuration that tells the semantic ranker which fields to read.

The embeddings are made here, client-side, with one call to text-embedding-3-small.
Re-running replaces the index definition and uploads the same documents again.

Sources:
https://learn.microsoft.com/azure/search/search-get-started-vector?pivots=python
https://learn.microsoft.com/azure/search/search-get-started-semantic?pivots=python
"""
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    VectorSearch,
    VectorSearchProfile,
)

from common import (
    DIMENSIONS, INDEX_NAME, SEARCH_ENDPOINT, SEMANTIC_CONFIG, VECTOR_FIELD,
    credential, embed, load_hotels,
)

fields = [
    SearchField(name="id", type="Edm.String", key=True, filterable=True),
    SearchField(name="name", type="Edm.String", searchable=True),
    SearchField(name="category", type="Edm.String", searchable=True, filterable=True, facetable=True),
    SearchField(name="description", type="Edm.String", searchable=True),
    SearchField(
        name=VECTOR_FIELD,
        type="Collection(Edm.Single)",
        searchable=True,
        vector_search_dimensions=DIMENSIONS,
        vector_search_profile_name="d13-vector-profile",
    ),
]

vector_search = VectorSearch(
    algorithms=[HnswAlgorithmConfiguration(name="d13-hnsw")],  # cosine is the default metric
    profiles=[VectorSearchProfile(name="d13-vector-profile", algorithm_configuration_name="d13-hnsw")],
)

semantic_search = SemanticSearch(
    configurations=[
        SemanticConfiguration(
            name=SEMANTIC_CONFIG,
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="name"),
                content_fields=[SemanticField(field_name="description")],
                keywords_fields=[SemanticField(field_name="category")],
            ),
        )
    ]
)

index = SearchIndex(name=INDEX_NAME, fields=fields, vector_search=vector_search, semantic_search=semantic_search)
SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=credential).create_or_update_index(index)
print(f"Index '{INDEX_NAME}' created on {SEARCH_ENDPOINT}")

hotels = load_hotels()
vectors = embed([h["description"] for h in hotels])
for hotel, vector in zip(hotels, vectors):
    hotel[VECTOR_FIELD] = vector
print(f"Embedded {len(hotels)} descriptions, {len(vectors[0])} dimensions each")

search_client = SearchClient(endpoint=SEARCH_ENDPOINT, index_name=INDEX_NAME, credential=credential)
results = search_client.upload_documents(documents=hotels)
ok = sum(1 for r in results if r.succeeded)
print(f"Uploaded {ok} of {len(hotels)} documents")
for r in results:
    if not r.succeeded:
        print(f"  {r.key}: {r.error_message}")
