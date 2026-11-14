"""Question router: decides between document search (RAG), business modules, or both."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

MODULE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "sales": ("sales", "vente", "revenue", "chiffre d'affaires", "forecast", "prevision",
              "predict", "trend", "tendance", "season", "saison", "product", "produit",
              "best seller", "top"),
    "customers": ("customer", "client", "churn", "attrition", "rfm", "segment", "loyal",
                  "fidel", "retention"),
    "marketing": ("marketing", "campaign", "campagne", "channel", "canal", "roi", "roas",
                  "advert", "publicite", "budget", "spend", "depense"),
    "insights": ("kpi", "anomal", "drop", "chute", "spike", "pic ", "unusual", "inhabituel",
                 "indicator", "indicateur", "overview", "apercu", "performance"),
}
DOCUMENT_KEYWORDS: tuple[str, ...] = (
    "document", "report", "rapport", "meeting", "reunion", "note", "memo", "pdf",
    "contract", "contrat", "according to", "selon", "what does", "que dit", "mentioned",
)


@dataclass
class Route:
    """Routing decision: which backends answer the question."""

    use_rag: bool
    modules: list[str] = field(default_factory=list)

    @property
    def kind(self) -> str:
        if self.use_rag and self.modules:
            return "both"
        return "business" if self.modules else "rag"


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text) + " "


def route_question(question: str) -> Route:
    """Route by keywords (FR/EN). Business-only keywords skip the document search."""
    text = _normalize(question)
    modules = [m for m, words in MODULE_KEYWORDS.items() if any(w in text for w in words)]
    wants_documents = any(w in text for w in DOCUMENT_KEYWORDS)
    if not modules:
        return Route(use_rag=True)
    return Route(use_rag=wants_documents, modules=modules)
