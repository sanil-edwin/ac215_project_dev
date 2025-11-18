"""
AgriGuard RAG Chat System
Conversational AI assistant for corn stress interpretation and yield guidance
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field
from fastapi import HTTPException

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, AIMessage

import pandas as pd

logger = logging.getLogger(__name__)


# Pydantic Models
class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., description="User's message/question")
    county_fips: Optional[str] = Field(None, description="County FIPS code for context")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for history")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str = Field(..., description="AI assistant's response")
    sources: List[Dict[str, str]] = Field(default_factory=list, description="Source documents used")
    context: Optional[Dict[str, Any]] = Field(None, description="County data context")
    conversation_id: str = Field(..., description="Conversation ID")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AgriGuardRAGSystem:
    """
    RAG-based conversational AI for AgriGuard
    Combines vector search with real-time MCSI data
    """
    
    def __init__(
        self,
        vector_store_dir: str = "./chroma_db",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        llm_model: str = "gemini-pro",
        temperature: float = 0.3
    ):
        self.vector_store_dir = vector_store_dir
        self.embedding_model_name = embedding_model
        self.llm_model = llm_model
        self.temperature = temperature
        
        # Will be initialized in startup()
        self.vectorstore = None
        self.llm = None
        self.qa_chain = None
        self.conversations = {}  # Store conversation memories
        
        # Will be set by backend API
        self.mcsi_data = None
        self.county_names = None
        
    async def initialize(self):
        """Initialize RAG components"""
        try:
            logger.info("Initializing RAG system...")
            
            # Load embeddings
            logger.info(f"Loading embeddings: {self.embedding_model_name}")
            embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            
            # Load vector store
            logger.info(f"Loading vector store from: {self.vector_store_dir}")
            self.vectorstore = Chroma(
                persist_directory=self.vector_store_dir,
                embedding_function=embeddings,
                collection_name="agriguard_knowledge"
            )
            
            # Test vector store
            test_results = self.vectorstore.similarity_search("corn stress", k=1)
            logger.info(f"Vector store loaded: {len(test_results)} test results")
            
            # Initialize LLM
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set")
            
            logger.info(f"Initializing LLM: {self.llm_model}")
            self.llm = ChatGoogleGenerativeAI(
                model=self.llm_model,
                temperature=self.temperature,
                google_api_key=api_key,
                convert_system_message_to_human=True
            )
            
            logger.info("✓ RAG system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"RAG initialization failed: {e}")
            raise
    
    def set_data_sources(self, mcsi_data: pd.DataFrame, county_names: pd.DataFrame):
        """Set data sources for context retrieval"""
        self.mcsi_data = mcsi_data
        self.county_names = county_names
        logger.info("Data sources set for RAG system")
    
    def get_county_context(self, county_fips: str) -> Optional[Dict[str, Any]]:
        """Get current MCSI data for county as context"""
        if self.mcsi_data is None or county_fips is None:
            return None
        
        try:
            # Get county data
            county_data = self.mcsi_data[
                self.mcsi_data['county_fips'] == county_fips
            ]
            
            if len(county_data) == 0:
                return None
            
            row = county_data.iloc[0]
            
            # Get county name
            county_name = "Unknown"
            if self.county_names is not None:
                county_info = self.county_names[
                    self.county_names['FIPS'] == county_fips
                ]
                if len(county_info) > 0:
                    county_name = county_info.iloc[0]['County']
            
            # Build context dictionary
            context = {
                "county_name": county_name,
                "county_fips": county_fips,
                "mcsi_score": float(row['mcsi_score']),
                "stress_level": row['stress_level'],
                "date": row['date'],
                "growth_stage": row.get('growth_stage', 'Unknown')
            }
            
            # Add component scores if available
            if 'water_stress' in row:
                context["water_stress"] = float(row['water_stress'])
            if 'heat_stress' in row:
                context["heat_stress"] = float(row['heat_stress'])
            if 'vegetation_stress' in row:
                context["vegetation_stress"] = float(row['vegetation_stress'])
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting county context: {e}")
            return None
    
    def build_context_prompt(self, context: Optional[Dict[str, Any]]) -> str:
        """Build context string from county data"""
        if not context:
            return "No specific county data available."
        
        prompt = f"""
Current Field Conditions for {context['county_name']} County:
- MCSI Score: {context['mcsi_score']:.2f}
- Stress Level: {context['stress_level']}
- Date: {context['date']}
- Growth Stage: {context.get('growth_stage', 'Unknown')}
"""
        
        if 'water_stress' in context:
            prompt += f"- Water Stress: {context['water_stress']:.2f}\n"
        if 'heat_stress' in context:
            prompt += f"- Heat Stress: {context['heat_stress']:.2f}\n"
        if 'vegetation_stress' in context:
            prompt += f"- Vegetation Health: {context['vegetation_stress']:.2f}\n"
        
        return prompt.strip()
    
    def create_qa_chain(self, conversation_id: str) -> ConversationalRetrievalChain:
        """Create a conversation chain with memory"""
        
        # Check if conversation already exists
        if conversation_id in self.conversations:
            return self.conversations[conversation_id]
        
        # Create new conversation memory
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        # Create custom prompt template
        prompt_template = """You are an expert agricultural AI assistant for AgriGuard, helping Iowa corn farmers interpret crop stress data and make informed decisions.

Context from knowledge base:
{context}

Current conversation history:
{chat_history}

Farmer's question: {question}

Instructions for your response:
1. Use the provided knowledge base context to answer accurately
2. If current field data is available in the question, reference it specifically
3. Provide actionable recommendations when appropriate
4. Explain technical concepts (like MCSI, NDVI) in farmer-friendly terms
5. If you don't have enough information, say so clearly
6. Be concise but thorough
7. Use bullet points for clarity when listing recommendations

Your response:"""

        # Create the chain
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            ),
            memory=memory,
            return_source_documents=True,
            verbose=False,
            combine_docs_chain_kwargs={"prompt": PromptTemplate.from_template(prompt_template)}
        )
        
        # Store conversation
        self.conversations[conversation_id] = qa_chain
        
        return qa_chain
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Main chat endpoint - processes user message and returns AI response
        """
        try:
            # Validate RAG system is initialized
            if self.vectorstore is None or self.llm is None:
                raise HTTPException(
                    status_code=503,
                    detail="RAG system not initialized"
                )
            
            # Generate conversation ID if not provided
            conversation_id = request.conversation_id or f"conv_{datetime.utcnow().timestamp()}"
            
            # Get county context if FIPS provided
            context = self.get_county_context(request.county_fips)
            context_str = self.build_context_prompt(context)
            
            # Augment user message with context
            augmented_message = f"{context_str}\n\nFarmer's question: {request.message}"
            
            # Get or create conversation chain
            qa_chain = self.create_qa_chain(conversation_id)
            
            # Query the chain
            logger.info(f"Processing chat query: {request.message[:50]}...")
            result = qa_chain({"question": augmented_message})
            
            # Extract response and sources
            response_text = result["answer"]
            source_docs = result.get("source_documents", [])
            
            # Format sources
            sources = []
            for doc in source_docs[:3]:  # Limit to top 3 sources
                sources.append({
                    "source": doc.metadata.get("source", "Unknown"),
                    "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                })
            
            logger.info(f"Generated response ({len(response_text)} chars) with {len(sources)} sources")
            
            return ChatResponse(
                response=response_text,
                sources=sources,
                context=context,
                conversation_id=conversation_id
            )
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Chat processing failed: {str(e)}"
            )
    
    async def chat_simple(self, request: ChatRequest) -> ChatResponse:
        """
        Simplified chat without full RAG (fallback if RAG not available)
        Uses direct LLM calls with context
        """
        try:
            conversation_id = request.conversation_id or f"conv_{datetime.utcnow().timestamp()}"
            
            # Get county context
            context = self.get_county_context(request.county_fips)
            context_str = self.build_context_prompt(context)
            
            # Build prompt
            system_message = """You are an agricultural AI assistant for corn farmers in Iowa. 
Help interpret crop stress data and provide actionable recommendations."""
            
            user_message = f"{context_str}\n\nQuestion: {request.message}"
            
            # Call LLM directly
            messages = [
                HumanMessage(content=f"{system_message}\n\n{user_message}")
            ]
            
            response = self.llm(messages)
            
            return ChatResponse(
                response=response.content,
                sources=[],
                context=context,
                conversation_id=conversation_id
            )
            
        except Exception as e:
            logger.error(f"Simple chat error: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Chat processing failed: {str(e)}"
            )


# Global RAG system instance
rag_system = AgriGuardRAGSystem()


async def initialize_rag_system():
    """Initialize RAG system on startup"""
    try:
        await rag_system.initialize()
        return True
    except Exception as e:
        logger.error(f"Failed to initialize RAG system: {e}")
        return False
