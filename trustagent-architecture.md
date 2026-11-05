# Trust Agent — System Architecture

Vietnamese legal Agentic RAG platform for traffic, accounting, and labor law.

```mermaid
flowchart LR
    U[User]
    FE[Next.js Frontend\nVercel]
    API[FastAPI API Gateway]
    ORCH[LangGraph Orchestrator\nDomain routing\nClarification questions]

    U --> FE --> API --> ORCH

    subgraph SPECIALISTS[Specialist Agents]
        TRAFFIC[Traffic Law Agent]
        ACCOUNTING[Accounting Law Agent]
        LABOR[Labor Law Agent]
    end

    ORCH --> TRAFFIC
    ORCH --> ACCOUNTING
    ORCH --> LABOR

    subgraph RAG[Shared Hybrid RAG Engine]
        BM25[BM25 keyword search]
        CHROMA[ChromaDB vector search]
        FILTER[Metadata filtering]
        RRF[Reciprocal Rank Fusion]
        RERANK[Reranking]
        BM25 --> RRF
        CHROMA --> RRF
        FILTER --> RRF
        RRF --> RERANK
    end

    TRAFFIC --> RAG
    ACCOUNTING --> RAG
    LABOR --> RAG

    subgraph CORPUS[Legal Corpus]
        TC[(Traffic collection)]
        AC[(Accounting collection)]
        LC[(Labor collection)]
        CHUNK[Chunks with:\nsource URL · document number · article · clause\neffective date · expiry date · status]
        TC --- CHUNK
        AC --- CHUNK
        LC --- CHUNK
    end

    RAG --> CORPUS
    CORPUS --> VERIFY[Citation & Effective Date Verifier\nEvidence sufficiency\nLegal applicability at requested time]
    VERIFY --> LLM[OpenAI\nGrounded Vietnamese answer\nCitations + disclaimer]
    LLM --> U

    DB[(SQLite / PostgreSQL\nSessions · traces · retrieved evidence\ncitations · evaluation logs)]
    API -.-> DB
    ORCH -.-> DB
    VERIFY -.-> DB

    subgraph ADMIN[Admin Portal]
        AP[Corpus and metadata management\nDocument versions\nTrace monitoring]
    end
    AP --> TC
    AP --> AC
    AP --> LC
    AP --> DB

    classDef app fill:#e8f1ff,stroke:#2563eb,color:#0f172a
    classDef agent fill:#f3e8ff,stroke:#9333ea,color:#0f172a
    classDef data fill:#ecfdf5,stroke:#059669,color:#0f172a
    classDef verify fill:#fff7ed,stroke:#ea580c,color:#0f172a
    class FE,API,ORCH app
    class TRAFFIC,ACCOUNTING,LABOR agent
    class TC,AC,LC,CHUNK,DB data
    class VERIFY,LLM verify
```

## Main request flow

`User → Next.js/Vercel → FastAPI → LangGraph → Specialist Agent → Hybrid RAG → Legal Corpus → Citation and Effective Date Verifier → OpenAI answer → User`

## Architecture notes

- Routing is centralized in LangGraph; a request can be clarified before specialist dispatch.
- The three legal collections are separated by domain, while retrieval and verification are shared.
- Legal applicability must be evaluated against the requested time using effective date, expiry date, and status metadata.
- The verifier is a gate before answer generation: insufficient or inapplicable evidence should prevent an unsupported legal answer.
- Admin writes are separated from the user query path and must preserve document versions and audit traces.
