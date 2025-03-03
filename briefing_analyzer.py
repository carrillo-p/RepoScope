import fitz
import logging
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from sklearn.metrics.pairwise import cosine_similarity

class ComplianceAnalyzer:
    def __init__(self):
        """Initialize ComplianceAnalyzer with logging configuration"""
        self.logger = logging.getLogger(__name__)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.threshold = 0.7  # Minimum similarity for compliance

    def extract_text_from_pdf(self, pdf_path):
        """
        Extracts text from a given PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            str: Extracted text from PDF
        """
        text = ""
        try:
            doc = fitz.open(pdf_path)
            text = " ".join([page.get_text() for page in doc])
            self.logger.info(f"Successfully extracted text from {pdf_path}")
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF: {e}")
        return text

    def check_compliance_with_briefing(self, repo_docs, briefing_text):
        """
        Compares repository content with briefing requirements using vector embeddings.
        
        Args:
            repo_docs (list): List of repository document texts
            briefing_text (str): Text from briefing document
            
        Returns:
            list: List of dictionaries containing compliance results
        """
        try:
            # Convert briefing text to embeddings
            briefing_embedding = self.embeddings.embed_query(briefing_text)

            # Convert repository text to embeddings
            repo_embeddings = [self.embeddings.embed_query(doc) for doc in repo_docs]

            # Compute similarity scores
            similarities = cosine_similarity([briefing_embedding], repo_embeddings)[0]

            compliance_results = []

            for idx, sim in enumerate(similarities):
                compliance_results.append({
                    "section": repo_docs[idx][:100],  
                    "similarity": round(sim * 100, 2),
                    "compliant": sim >= self.threshold
                })

            self.logger.info(f"Completed compliance check for {len(repo_docs)} documents")
            return compliance_results

        except Exception as e:
            self.logger.error(f"Error in compliance check: {e}")
            return []

    def analyze_repository_compliance(self, repo_docs_path, briefing_path):
        """
        Complete analysis pipeline for repository compliance.
        
        Args:
            repo_docs_path (str): Path to repository documents
            briefing_path (str): Path to briefing PDF
            
        Returns:
            dict: Analysis results including compliance scores and summary
        """
        try:
            # Extract briefing text
            briefing_text = self.extract_text_from_pdf(briefing_path)
            if not briefing_text:
                raise ValueError("Failed to extract text from briefing PDF")

            # Check compliance
            compliance_results = self.check_compliance_with_briefing(repo_docs_path, briefing_text)

            # Calculate overall compliance
            compliant_sections = sum(1 for result in compliance_results if result["compliant"])
            total_sections = len(compliance_results)
            overall_compliance = (compliant_sections / total_sections * 100) if total_sections > 0 else 0

            return {
                "overall_compliance": round(overall_compliance, 2),
                "total_sections": total_sections,
                "compliant_sections": compliant_sections,
                "detailed_results": compliance_results
            }

        except Exception as e:
            self.logger.error(f"Error in repository compliance analysis: {e}")
            return {
                "overall_compliance": 0,
                "total_sections": 0,
                "compliant_sections": 0,
                "detailed_results": []
            }
