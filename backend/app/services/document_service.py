import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import PyPDF2
from docx import Document as DocxDocument
import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime

from app.models.models import Document, DocumentChunk
from app.schemas.schemas import DocumentSearchResult
from app.core.config import settings
from app.services.rag_service import RagService

class DocumentService:
    def __init__(self):
        self.embedding_model = None
        self.chroma_client = None
        self.collection = None
        self._init_embedding_model()
        self._init_vector_db()

    def _init_embedding_model(self):
        """Initialize the sentence transformer model for embeddings"""
        try:
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        except Exception as e:
            print(f"Warning: Could not load embedding model: {e}")
            self.embedding_model = None

    def _init_vector_db(self):
        """Initialize ChromaDB for vector storage"""
        try:
            self.chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            self.collection = self.chroma_client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            print(f"Warning: Could not initialize ChromaDB: {e}")
            self.chroma_client = None
            self.collection = None

    async def process_document(
        self, 
        document: Document, 
        chunk_size: int = 1000, 
        chunk_overlap: int = 200,
        db: Session = None
    ) -> int:
        """
        Process a document by extracting text, chunking, and creating embeddings
        """
        try:
            # Extract text from document
            text_content = await self._extract_text_from_file(document.file_path, document.file_type)
            
            if not text_content.strip():
                raise Exception("No text content found in document")
            
            # Split text into chunks
            chunks = self._split_text_into_chunks(text_content, chunk_size, chunk_overlap)
            
            # Create embeddings and store in vector database (via RagService)
            chunk_count = 0
            # Lazy import to avoid circular
            from app.services.rag_service import RagService  # type: ignore
            from app.main import app  # type: ignore
            rag: RagService = app.state.rag_service  # type: ignore[attr-defined]

            batch_texts: list[str] = []
            batch_metas: list[dict] = []
            batch_ids: list[str] = []
            for i, chunk_text in enumerate(chunks):
                try:
                    # Create document chunk record
                    chunk = DocumentChunk(
                        document_id=document.id,
                        chunk_index=i,
                        content=chunk_text,
                        metadata=json.dumps({
                            "chunk_size": len(chunk_text),
                            "document_title": document.title,
                            "file_type": document.file_type
                        })
                    )
                    
                    db.add(chunk)
                    db.flush()  # Get the chunk ID
                    
                    # Accumulate for RAG upsert
                    embedding_id = f"doc_{document.id}_chunk_{i}"
                    batch_texts.append(chunk_text)
                    batch_metas.append({
                        "document_id": document.id,
                        "chunk_id": chunk.id,
                        "document_title": document.title,
                        "chunk_index": i,
                        "file_type": document.file_type,
                        "user_id": document.user_id,
                    })
                    batch_ids.append(embedding_id)
                    chunk.embedding_id = embedding_id
                    
                    chunk_count += 1
                    
                except Exception as e:
                    print(f"Error processing chunk {i}: {e}")
                    continue
            
            # Perform a single upsert into vector store via RAG service
            if batch_texts:
                try:
                    await rag.upsert_chunks(texts=batch_texts, metadatas=batch_metas, ids=batch_ids)
                except Exception as e:
                    print(f"Vector upsert failed: {e}")

            db.commit()
            return chunk_count
            
        except Exception as e:
            db.rollback()
            raise Exception(f"Error processing document: {str(e)}")

    async def _extract_text_from_file(self, file_path: str, file_type: str) -> str:
        """
        Extract text content from various file types
        """
        try:
            if file_type.lower() == '.pdf':
                return await self._extract_from_pdf(file_path)
            elif file_type.lower() == '.docx':
                return await self._extract_from_docx(file_path)
            elif file_type.lower() in ['.txt', '.md']:
                return await self._extract_from_text(file_path)
            else:
                raise Exception(f"Unsupported file type: {file_type}")
        except Exception as e:
            raise Exception(f"Error extracting text from {file_path}: {str(e)}")

    async def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            raise Exception(f"Error reading PDF: {str(e)}")
        return text

    async def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = DocxDocument(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            raise Exception(f"Error reading DOCX: {str(e)}")
        return text

    async def _extract_from_text(self, file_path: str) -> str:
        """Extract text from text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as file:
                return file.read()
        except Exception as e:
            raise Exception(f"Error reading text file: {str(e)}")

    def _split_text_into_chunks(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Split text into chunks with specified size and overlap
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings
                for i in range(end, start + chunk_size - 100, -1):
                    if text[i] in '.!?':
                        end = i + 1
                        break
                # If no sentence boundary found, look for word boundaries
                else:
                    for i in range(end, start + chunk_size - 50, -1):
                        if text[i] == ' ':
                            end = i
                            break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - chunk_overlap
            if start >= len(text):
                break
        
        return chunks

    async def search_documents(
        self,
        query: str,
        document_ids: List[int] = None,
        limit: int = 5,
        similarity_threshold: float | None = 0.7,
        db: Session = None
    ) -> List[DocumentSearchResult]:
        """
        Search for relevant document chunks using semantic similarity
        """
        if not self.embedding_model or not self.collection:
            raise Exception("Embedding model or vector database not available")
        
        try:
            # Create query embedding
            query_embedding = self.embedding_model.encode([query])[0]
            
            # Build filter conditions
            where_conditions = {}
            if document_ids:
                where_conditions["document_id"] = {"$in": document_ids}
            
            # Search in vector database
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=limit * 2,  # Get more results to filter
                where=where_conditions if where_conditions else None
            )
            
            # Process results
            search_results = []
            if results['documents']:
                for i, (doc_text, metadata, distance) in enumerate(zip(
                    results['documents'][0], 
                    results['metadatas'][0], 
                    results['distances'][0]
                )):
                    # Convert distance to similarity score (cosine distance -> cosine similarity)
                    similarity_score = 1.0 - distance
                    
                    if similarity_threshold is None or similarity_score >= similarity_threshold:
                        search_results.append(DocumentSearchResult(
                            document_id=metadata['document_id'],
                            document_title=metadata['document_title'],
                            chunk_content=doc_text,
                            similarity_score=similarity_score,
                            metadata=metadata
                        ))
            
            # Sort by similarity score and limit results
            search_results.sort(key=lambda x: x.similarity_score, reverse=True)
            return search_results[:limit]
            
        except Exception as e:
            raise Exception(f"Error searching documents: {str(e)}")

    async def get_document_chunks(self, document_id: int, db: Session) -> List[DocumentChunk]:
        """
        Get all chunks for a specific document
        """
        return db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id
        ).order_by(DocumentChunk.chunk_index).all()

    async def delete_document_embeddings(self, document_id: int):
        """
        Delete embeddings for a specific document from vector database
        """
        try:
            from app.main import app  # type: ignore
            rag: RagService = app.state.rag_service  # type: ignore[attr-defined]
            await rag.delete_by_document_id(document_id=document_id)
        except Exception as e:
            print(f"Error deleting embeddings for document {document_id}: {e}")

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database collection
        """
        if not self.collection:
            return {"error": "Vector database not available"}
        
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "collection_name": self.collection.name,
                "embedding_model": settings.EMBEDDING_MODEL
            }
        except Exception as e:
            return {"error": f"Error getting collection stats: {str(e)}"} 