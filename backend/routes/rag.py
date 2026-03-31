"""RAG Routes — query the pandemic knowledge base and LLM reasoning."""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.rag_service import PandemicKnowledgeBase
from services.llm_service import get_llm_service
from services.data_service import DataIngestionService

router = APIRouter()
logger = logging.getLogger(__name__)
data_service = DataIngestionService()


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    region_id: str = Field(default="delhi")
    top_k: int = Field(default=3, ge=1, le=8)
    intervention_filter: str | None = Field(default=None)


class NLQueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    region_id: str = Field(default="delhi")


@router.post("/query")
async def rag_query(request: RAGQueryRequest):
    """Direct vector search against the pandemic knowledge base."""
    try:
        kb = PandemicKnowledgeBase.get_instance()
        results = kb.query(
            request.query,
            top_k=request.top_k,
            intervention_filter=request.intervention_filter,
        )
        return {
            "query": request.query,
            "results": [
                {
                    "id": r.id,
                    "title": r.title,
                    "content": r.content,
                    "intervention": r.intervention,
                    "effectiveness": r.effectiveness,
                    "economic_cost": r.economic_cost,
                    "similarity_score": r.similarity_score,
                    "tags": r.tags,
                }
                for r in results
            ],
            "total_documents": len(kb._docs),
        }
    except Exception as e:
        logger.exception("RAG query error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nl-query")
async def nl_query(request: NLQueryRequest):
    """
    Natural language query: RAG retrieval + LLM reasoning.
    Returns an evidence-grounded answer to plain-English epidemic questions.
    """
    try:
        region = data_service.get_region(request.region_id)
        disease_stats = data_service.get_current_disease_stats(region)

        sim_context = {
            "r0": disease_stats.get("reproduction_number", 1.5),
            "severity": "HIGH" if disease_stats.get("reproduction_number", 1.5) > 1.5 else "MODERATE",
            "region": region["name"],
        }

        llm = get_llm_service()
        result = llm.answer_natural_language_query(
            query=request.query,
            region_name=region["name"],
            sim_context=sim_context,
        )

        return {
            "query": request.query,
            "region": region["name"],
            "answer": result["answer"],
            "source": result["source"],
            "rag_sources": result.get("rag_sources", []),
            "context": sim_context,
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("NL query error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def list_documents():
    """List all documents in the knowledge base."""
    kb = PandemicKnowledgeBase.get_instance()
    return {
        "total": len(kb._docs),
        "documents": [
            {
                "id": d["id"],
                "title": d["title"],
                "intervention": d["intervention"],
                "effectiveness": d["effectiveness"],
                "tags": d["tags"],
            }
            for d in kb._docs
        ],
    }
