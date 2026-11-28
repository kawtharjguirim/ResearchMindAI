"""
Graphe de connaissances (Neo4j) : reconstruction depuis le corpus et lecture des effectifs.

    POST /knowledge-graph/build   -> lit data_latex/ et écrit le graphe dans Neo4j
    GET  /knowledge-graph         -> nombre de nœuds et de relations par type
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user
from app.services import knowledge_graph as kg

router = APIRouter(prefix="/knowledge-graph", tags=["knowledge-graph"])


def _erreur_neo4j(e: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                         detail=f"Neo4j unavailable ({type(e).__name__}). Is the neo4j container running?")


@router.post("/build")
def build(user: CurrentUser = Depends(get_current_user)):
    """Reconstruit le graphe. Les requêtes MERGE ne créent pas de doublons : l'opération peut être relancée."""
    articles = kg.lire_corpus()
    try:
        driver = kg.pilote()
        try:
            resultat = kg.construire(articles, driver)
        finally:
            driver.close()
    except Exception as e:  # noqa: BLE001 : connexion refusée, authentification ou requête
        raise _erreur_neo4j(e) from e
    return {"articles_lus": len(articles), **resultat}


@router.get("")
def stats(user: CurrentUser = Depends(get_current_user)):
    try:
        driver = kg.pilote()
        try:
            return kg.statistiques(driver)
        finally:
            driver.close()
    except Exception as e:  # noqa: BLE001
        raise _erreur_neo4j(e) from e
