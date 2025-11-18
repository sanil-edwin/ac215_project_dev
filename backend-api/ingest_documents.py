"""
AgriGuard RAG - Document Ingestion Pipeline
Processes agricultural PDFs and creates vector embeddings for semantic search
"""

import os
import logging
from pathlib import Path
from typing import List, Dict
import shutil

from langchain_community.document_loaders import (
    PyPDFLoader,
    DirectoryLoader,
    TextLoader,
    UnstructuredMarkdownLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.docstore.document import Document

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgriGuardDocumentIngestion:
    """
    Document ingestion pipeline for AgriGuard RAG system
    Processes agricultural research papers, MCSI docs, and ML model outputs
    """
    
    def __init__(
        self,
        knowledge_base_dir: str = "./knowledge_base",
        vector_store_dir: str = "./chroma_db",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        self.knowledge_base_dir = Path(knowledge_base_dir)
        self.vector_store_dir = Path(vector_store_dir)
        self.embedding_model_name = embedding_model
        
        # Create directories if they don't exist
        self.knowledge_base_dir.mkdir(parents=True, exist_ok=True)
        self.vector_store_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize embeddings
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
    def load_documents(self) -> List[Document]:
        """Load all documents from knowledge base directory"""
        documents = []
        
        # Load PDFs
        logger.info("Loading PDF documents...")
        pdf_loader = DirectoryLoader(
            str(self.knowledge_base_dir),
            glob="**/*.pdf",
            loader_cls=PyPDFLoader,
            show_progress=True
        )
        pdf_docs = pdf_loader.load()
        logger.info(f"Loaded {len(pdf_docs)} PDF pages")
        documents.extend(pdf_docs)
        
        # Load Markdown files (README, MCSI docs, etc.)
        logger.info("Loading Markdown documents...")
        md_files = list(self.knowledge_base_dir.glob("**/*.md"))
        for md_file in md_files:
            try:
                loader = UnstructuredMarkdownLoader(str(md_file))
                md_docs = loader.load()
                # Add source metadata
                for doc in md_docs:
                    doc.metadata['source'] = str(md_file.name)
                    doc.metadata['type'] = 'documentation'
                documents.extend(md_docs)
                logger.info(f"Loaded {md_file.name}")
            except Exception as e:
                logger.warning(f"Failed to load {md_file}: {e}")
        
        # Load text files
        logger.info("Loading text documents...")
        txt_files = list(self.knowledge_base_dir.glob("**/*.txt"))
        for txt_file in txt_files:
            try:
                loader = TextLoader(str(txt_file))
                txt_docs = loader.load()
                for doc in txt_docs:
                    doc.metadata['source'] = str(txt_file.name)
                    doc.metadata['type'] = 'text'
                documents.extend(txt_docs)
                logger.info(f"Loaded {txt_file.name}")
            except Exception as e:
                logger.warning(f"Failed to load {txt_file}: {e}")
        
        logger.info(f"Total documents loaded: {len(documents)}")
        return documents
    
    def add_custom_documents(self) -> List[Document]:
        """Add AgriGuard-specific documentation as documents"""
        custom_docs = []
        
        # MCSI Interpretation Guide
        mcsi_doc = Document(
            page_content="""
            Multi-Crop Stress Index (MCSI) Interpretation Guide for Iowa Corn
            
            MCSI Score Ranges and Meanings:
            - 0.0 - 0.3 (Low Stress): Optimal growing conditions
              * Corn plants are healthy with good canopy cover
              * NDVI values > 0.7 indicate vigorous vegetation
              * Soil moisture is adequate
              * Temperatures within optimal range (70-85°F)
              * Expected yield: 95-100% of county average
              
            - 0.3 - 0.5 (Moderate Stress): Minor stress detected
              * Some reduction in vegetation vigor
              * NDVI values 0.5-0.7
              * Possible water deficit emerging
              * Monitor closely, especially during critical growth stages
              * Expected yield: 85-95% of county average
              
            - 0.5 - 0.7 (High Stress): Significant stress
              * Visible reduction in crop health
              * NDVI < 0.5 indicates stress
              * Water deficit or heat stress present
              * Land Surface Temperature elevated
              * Immediate action recommended
              * Expected yield: 70-85% of county average
              
            - 0.7 - 1.0 (Severe Stress): Critical conditions
              * Crop is experiencing severe stress
              * Potential irreversible damage
              * Multiple stress factors likely present
              * Yield loss expected to be significant
              * Expected yield: < 70% of county average
            
            Critical Growth Stages for Iowa Corn:
            - V6-V10 (Early June): Rapid growth phase
            - VT-R1 (Tasseling/Silking, mid-July): MOST CRITICAL
              * Stress during this period causes largest yield impacts
              * Water stress can reduce kernel set by 50%+
            - R2-R4 (Grain fill, August): Important for kernel weight
            
            MCSI Component Indicators:
            1. Vegetation Health (NDVI, EVI)
               - Measures plant greenness and photosynthetic activity
               - Lower values indicate stress
            
            2. Water Stress (NDWI, ET anomalies, Water Deficit)
               - Soil moisture and plant water status
               - Precipitation deficits accumulate over weeks
            
            3. Thermal Stress (LST, VPD)
               - Land Surface Temperature above 95°F causes stress
               - Vapor Pressure Deficit > 3 kPa indicates heat stress
            
            Iowa-Specific Factors:
            - Most corn planted: Late April - Mid May
            - Silking typically: Mid-July
            - Harvest: October - November
            - Average county yield: 180-200 bushels/acre
            - 2012 drought reduced yields by 40% statewide
            - 2023 wet year increased yields by 15%
            """,
            metadata={
                "source": "MCSI_Interpretation_Guide",
                "type": "documentation",
                "topic": "mcsi_interpretation"
            }
        )
        custom_docs.append(mcsi_doc)
        
        # Corn Stress Management Guide
        management_doc = Document(
            page_content="""
            Corn Stress Management Recommendations for Iowa Farmers
            
            When MCSI Shows Moderate Stress (0.3-0.5):
            1. Monitor soil moisture regularly
            2. Check weather forecast for rainfall
            3. Assess irrigation options if available
            4. Scout fields for pest/disease issues
            5. Consider fungicide application if justified
            
            When MCSI Shows High Stress (0.5-0.7):
            1. Immediate Actions:
               - Irrigate if possible (1-1.5 inches)
               - Prioritize fields in critical growth stages
               - Delay fertilizer applications
            2. Field Assessment:
               - Check for leaf rolling (water stress indicator)
               - Look for heat stress symptoms
               - Assess root health if possible
            3. Management Adjustments:
               - Reduce crop load if excessive
               - Maintain weed control to reduce competition
            
            When MCSI Shows Severe Stress (0.7-1.0):
            1. Critical Response:
               - Emergency irrigation if infrastructure exists
               - Consider crop insurance claim assessment
               - Document stress for records
            2. Salvage Options:
               - May need to consider silage harvest
               - Assess if crop will reach maturity
            3. Future Planning:
               - Review hybrid selection for stress tolerance
               - Consider tiling for drainage in wet years
               - Evaluate irrigation investment
            
            Irrigation Scheduling Based on MCSI:
            - MCSI < 0.3: No irrigation needed
            - MCSI 0.3-0.5: Monitor closely, prepare irrigation
            - MCSI 0.5-0.7: Irrigate 1 inch immediately
            - MCSI > 0.7: Emergency irrigation, 1.5 inches
            
            Critical Period Irrigation Priority:
            1. VT-R1 (Silking): Highest priority
            2. R2-R3 (Early grain fill): High priority
            3. V10-V15 (Rapid growth): Medium priority
            4. R5-R6 (Late grain fill): Lower priority
            
            Weather-Based Adjustments:
            - If rain forecast within 48 hours: Delay irrigation
            - High humidity (>70%): Stress impact reduced slightly
            - Hot winds: Increase stress impact, act sooner
            - Cool nights: Helps recovery from day stress
            
            Economic Considerations:
            - Irrigation cost: $40-60/acre per application
            - Yield benefit from timely irrigation: 20-40 bu/acre
            - Critical period irrigation has 5:1 benefit-cost ratio
            - Late season irrigation may not be economical
            """,
            metadata={
                "source": "Stress_Management_Guide",
                "type": "documentation",
                "topic": "management_recommendations"
            }
        )
        custom_docs.append(management_doc)
        
        # Yield Prediction Interpretation
        yield_doc = Document(
            page_content="""
            Understanding AgriGuard Yield Predictions
            
            How Yield Predictions Work:
            AgriGuard uses machine learning (Random Forest) to predict corn yields based on:
            1. Historical MCSI patterns throughout the growing season
            2. County-specific baseline yields (10-year average)
            3. Current year stress trajectory
            4. Critical period stress (VT-R1, R2-R4)
            5. Weather patterns and anomalies
            
            Prediction Accuracy:
            - Early season (May-June): Lower confidence (±20%)
            - Mid-season (July-August): Medium confidence (±10%)
            - Late season (September): High confidence (±5%)
            
            Interpreting Yield Forecasts:
            - Prediction shows: County-level expected yield
            - Baseline: Historical 10-year average for county
            - Deviation: Percentage above/below average
            
            Example: Polk County, Iowa
            - Historical average: 195 bu/acre
            - Current prediction: 175 bu/acre
            - Deviation: -10% (below average)
            - Reason: High MCSI during silking period
            
            Key Factors Affecting Predictions:
            1. Timing of Stress:
               - Silking period stress: 40-50% yield impact
               - Grain fill stress: 15-25% yield impact
               - Early vegetative stress: 10-15% yield impact
            
            2. Stress Duration:
               - 1 week of severe stress at silking: -30 bu/acre
               - 2 weeks of moderate stress in grain fill: -20 bu/acre
               - Season-long low stress: +10-15 bu/acre
            
            3. Hybrid Selection:
               - Stress-tolerant hybrids: 10-15% better under stress
               - High-yield potential hybrids: Better in good years
            
            4. Management Practices:
               - Irrigation can mitigate 50-70% of water stress
               - Optimal plant population: 32,000-36,000 plants/acre
               - Proper fertility: Foundation for yield potential
            
            Historical Yield Context (Iowa):
            - 2012 Drought: Average yield 135 bu/acre (-35%)
            - 2014 Record: Average yield 203 bu/acre (+20%)
            - 2019 Wet year: Average yield 165 bu/acre (-15%)
            - 2021 Good year: Average yield 205 bu/acre (+25%)
            - 10-year average: 180-190 bu/acre
            
            County-Level Variability:
            - Northern Iowa: Generally higher yields (fertile soils)
            - Southern Iowa: More variable (rolling terrain)
            - Western Iowa: Excellent soils, sensitive to drought
            - Eastern Iowa: Good yields, occasional wet conditions
            """,
            metadata={
                "source": "Yield_Prediction_Guide",
                "type": "documentation",
                "topic": "yield_forecasting"
            }
        )
        custom_docs.append(yield_doc)
        
        logger.info(f"Added {len(custom_docs)} custom documentation documents")
        return custom_docs
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks for embedding"""
        logger.info("Splitting documents into chunks...")
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = text_splitter.split_documents(documents)
        logger.info(f"Created {len(chunks)} document chunks")
        
        return chunks
    
    def create_vector_store(self, chunks: List[Document]) -> Chroma:
        """Create and persist Chroma vector store"""
        logger.info("Creating vector store...")
        
        # Remove existing vector store if it exists
        if self.vector_store_dir.exists():
            logger.info("Removing existing vector store...")
            shutil.rmtree(self.vector_store_dir)
            self.vector_store_dir.mkdir(parents=True, exist_ok=True)
        
        # Create new vector store
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=str(self.vector_store_dir),
            collection_name="agriguard_knowledge"
        )
        
        logger.info(f"Vector store created with {len(chunks)} chunks")
        logger.info(f"Persisted to: {self.vector_store_dir}")
        
        return vectorstore
    
    def test_retrieval(self, vectorstore: Chroma, test_queries: List[str]):
        """Test the vector store with sample queries"""
        logger.info("\n" + "="*60)
        logger.info("Testing vector store retrieval...")
        logger.info("="*60)
        
        for query in test_queries:
            logger.info(f"\nQuery: {query}")
            results = vectorstore.similarity_search(query, k=2)
            
            for i, doc in enumerate(results, 1):
                logger.info(f"\n  Result {i}:")
                logger.info(f"  Source: {doc.metadata.get('source', 'Unknown')}")
                logger.info(f"  Content preview: {doc.page_content[:150]}...")
    
    def ingest_all(self):
        """Main ingestion pipeline"""
        logger.info("\n" + "="*60)
        logger.info("Starting AgriGuard RAG Document Ingestion")
        logger.info("="*60 + "\n")
        
        # Load documents
        documents = self.load_documents()
        
        # Add custom documentation
        custom_docs = self.add_custom_documents()
        documents.extend(custom_docs)
        
        if not documents:
            logger.error("No documents found! Add PDFs/docs to knowledge_base/")
            return None
        
        # Split into chunks
        chunks = self.split_documents(documents)
        
        # Create vector store
        vectorstore = self.create_vector_store(chunks)
        
        # Test retrieval
        test_queries = [
            "What does an MCSI score of 0.6 mean?",
            "How does stress during silking affect yield?",
            "What should I do if my crop is under high stress?"
        ]
        self.test_retrieval(vectorstore, test_queries)
        
        logger.info("\n" + "="*60)
        logger.info("Document ingestion completed successfully!")
        logger.info("="*60)
        
        return vectorstore


def main():
    """Run document ingestion"""
    
    # Initialize ingestion pipeline
    ingestion = AgriGuardDocumentIngestion(
        knowledge_base_dir="./knowledge_base",
        vector_store_dir="./chroma_db"
    )
    
    # Run ingestion
    ingestion.ingest_all()
    
    logger.info("\nNext steps:")
    logger.info("1. Add more PDF documents to ./knowledge_base/")
    logger.info("2. Run this script again to update the vector store")
    logger.info("3. The vector store is ready for the RAG chat endpoint")


if __name__ == "__main__":
    main()
