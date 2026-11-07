"""Shared bits for D13: names, clients and the embedding call.

Keyless everywhere: DefaultAzureCredential picks up your `az login`.
- Azure AI Search: the service is created with API keys disabled, so only roles work
  (Search Service Contributor, Search Index Data Contributor, Search Index Data Reader).
- Embeddings: the shared text-embedding-3-small deployment, called through the
  OpenAI v1 endpoint of the Foundry resource (role: Cognitive Services OpenAI User).

Env vars come from ../common/demo.env (FOUNDRY, EMBED_DEPLOYMENT). The search service
name is derived from FOUNDRY the same way setup.sh does it; set SEARCH_SERVICE to override.
"""
import json
import os
from pathlib import Path

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI

HERE = Path(__file__).parent

SEARCH_SERVICE = os.environ.get("SEARCH_SERVICE") or f"{os.environ['FOUNDRY']}-d13".lower()
SEARCH_ENDPOINT = f"https://{SEARCH_SERVICE}.search.windows.net"
INDEX_NAME = os.environ.get("SEARCH_INDEX", "d13-hotels")
SEMANTIC_CONFIG = "d13-semantic"
VECTOR_FIELD = "descriptionVector"
DIMENSIONS = 1536  # text-embedding-3-small default output size

credential = DefaultAzureCredential()


def openai_client() -> OpenAI:
    """OpenAI v1 client on the Foundry resource, with an Entra token instead of a key."""
    token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
    return OpenAI(
        base_url=f"https://{os.environ['FOUNDRY']}.openai.azure.com/openai/v1/",
        api_key=token_provider,
    )


def embed(texts: list[str]) -> list[list[float]]:
    """One embeddings call for a list of texts; returns the vectors in the same order."""
    response = openai_client().embeddings.create(model=os.environ["EMBED_DEPLOYMENT"], input=texts)
    return [item.embedding for item in sorted(response.data, key=lambda d: d.index)]


def load_hotels() -> list[dict]:
    return json.loads((HERE / "hotels.json").read_text(encoding="utf-8"))
