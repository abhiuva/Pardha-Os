# Knowledge Ingestion API

The Knowledge Ingestion Layer stores business-isolated context for retrieval by Pardha agents.

## Database Migration

Run the versioned PostgreSQL migration:

```bash
venv/bin/python scripts/apply_migrations.py
```

The existing `scripts/init_db.py` and application startup `create_all` flow also create the SQLAlchemy table for local development.

## Create Knowledge

Request:

```http
POST /knowledge
Content-Type: application/json

{
  "business_name": "UVA",
  "category": "company",
  "title": "UVA Capabilities",
  "content": "UVA provides Product Engineering, AI Solutions, Cloud Engineering and Enterprise Software Development.",
  "tags": ["engineering", "ai", "cloud"],
  "source": "company-profile"
}
```

Response:

```json
{
  "business_name": "UVA",
  "category": "company",
  "title": "UVA Capabilities",
  "content": "UVA provides Product Engineering, AI Solutions, Cloud Engineering and Enterprise Software Development.",
  "tags": ["engineering", "ai", "cloud"],
  "source": "company-profile",
  "source_uri": null,
  "document_metadata": {},
  "knowledge_id": "0e644c88-0558-42d4-b102-22304768ee7c",
  "created_at": "2026-06-10T12:00:00Z",
  "embedding_model": null,
  "embedding_reference": null
}
```

## Retrieve and Search

```http
GET /knowledge
GET /knowledge?business_name=UVA&category=company
GET /knowledge/search?query=cloud&business_name=UVA&category=company
GET /knowledge/business/UVA
GET /knowledge/business/Trevia%20EV?category=product
```

Supported categories:

`company`, `product`, `project`, `roadmap`, `prd`, `sop`, `meeting_notes`, `customer_feedback`

`source_uri`, `document_metadata`, `embedding_model`, and `embedding_reference` reserve schema space for future document uploads, embeddings, RAG, and agent retrieval. Vector storage is not implemented in v0.1.
