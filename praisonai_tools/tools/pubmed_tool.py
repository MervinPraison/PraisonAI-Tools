"""PubMed Tool for PraisonAI Agents.

Search biomedical literature on PubMed.

Usage:
    from praisonai_tools import PubMedTool
    
    pubmed = PubMedTool()
    results = pubmed.search("cancer treatment")
"""

import logging
from typing import Any, Dict, List, Optional, Union

from praisonai_tools.tools.base import BaseTool

logger = logging.getLogger(__name__)


class PubMedTool(BaseTool):
    """Tool for PubMed search."""
    
    name = "pubmed"
    description = "Search biomedical literature on PubMed."
    
    def __init__(self, email: Optional[str] = None):
        self.email = email
        super().__init__()
    
    def run(
        self,
        action: str = "search",
        query: Optional[str] = None,
        max_results: int = 10,
        **kwargs
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]]]:
        action = action.lower().replace("-", "_")
        
        if action == "search":
            return self.search(query=query, max_results=max_results)
        elif action == "get_article":
            return self.get_article(pmid=kwargs.get("pmid"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search PubMed."""
        if not query:
            return [{"error": "query is required"}]
        
        try:
            from Bio import Entrez
        except ImportError:
            return [{"error": "biopython not installed. Install with: pip install biopython"}]
        
        try:
            Entrez.email = self.email or "user@example.com"
            handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
            record = Entrez.read(handle)
            handle.close()
            
            ids = record.get("IdList", [])
            if not ids:
                return []
            
            handle = Entrez.efetch(db="pubmed", id=ids, rettype="abstract", retmode="xml")
            records = Entrez.read(handle)
            handle.close()
            
            results = []
            for article in records.get("PubmedArticle", []):
                medline = article.get("MedlineCitation", {})
                art = medline.get("Article", {})
                results.append({
                    "pmid": str(medline.get("PMID", "")),
                    "title": art.get("ArticleTitle", ""),
                    "abstract": art.get("Abstract", {}).get("AbstractText", [""])[0] if art.get("Abstract") else "",
                    "journal": art.get("Journal", {}).get("Title", ""),
                })
            return results
        except Exception as e:
            logger.error(f"PubMed search error: {e}")
            return [{"error": str(e)}]
    
    def get_article(self, pmid: str) -> Dict[str, Any]:
        """Get article by PMID."""
        if not pmid:
            return {"error": "pmid is required"}
        
        try:
            from Bio import Entrez
        except ImportError:
            return {"error": "biopython not installed"}
        
        try:
            Entrez.email = self.email or "user@example.com"
            handle = Entrez.efetch(db="pubmed", id=pmid, rettype="abstract", retmode="xml")
            records = Entrez.read(handle)
            handle.close()
            
            if not records.get("PubmedArticle"):
                return {"error": "Article not found"}
            
            article = records["PubmedArticle"][0]
            medline = article.get("MedlineCitation", {})
            art = medline.get("Article", {})
            
            return {
                "pmid": pmid,
                "title": art.get("ArticleTitle", ""),
                "abstract": art.get("Abstract", {}).get("AbstractText", [""])[0] if art.get("Abstract") else "",
                "journal": art.get("Journal", {}).get("Title", ""),
                "authors": [
                    f"{a.get('LastName', '')} {a.get('ForeName', '')}"
                    for a in art.get("AuthorList", [])
                ],
            }
        except Exception as e:
            logger.error(f"PubMed get_article error: {e}")
            return {"error": str(e)}


def pubmed_search(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search PubMed."""
    return PubMedTool().search(query=query, max_results=max_results)
