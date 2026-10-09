from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import aiofiles
from datetime import datetime

from app.core.database import get_db
from app.models.models import Document, DocumentChunk, User
from app.schemas.schemas import (
    DocumentResponse, DocumentUpload, DocumentProcessRequest,
    DocumentSearchRequest, DocumentSearchResult
)
from app.services.document_service import DocumentService
from app.core.config import settings
from app.dependencies import get_current_user, get_doc_service, get_rag_service
from app.services.rag_service import RagService

router = APIRouter()

@router.post("/documents/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    keywords: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_doc_service)
):
    """
    Upload a document for processing
    """
    # Validate file type
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_extension} not allowed. Allowed types: {settings.ALLOWED_EXTENSIONS}"
        )
    
    # Check file size
    if file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size {file.size} exceeds maximum allowed size {settings.MAX_FILE_SIZE}"
        )
    
    try:
        # Create upload directory if it doesn't exist
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
        # Save file to disk
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Create document record
        document = Document(
            filename=unique_filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=len(content),
            file_type=file_extension,
            mime_type=file.content_type,
            title=title or file.filename,
            description=description,
            keywords=keywords,
            uploaded_at=datetime.now(),
            user_id=current_user.id
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)

        # Auto-process document immediately after upload
        try:
            chunks_created = await doc_service.process_document(
                document=document,
                chunk_size=1000,
                chunk_overlap=200,
                db=db
            )
            document.processed = True
            document.processed_at = datetime.now()
            document.chunk_count = chunks_created
            document.embedding_model = settings.EMBEDDING_MODEL
            db.commit()
            db.refresh(document)
        except Exception as e:
            # If processing fails, return upload success but mark as not processed
            print(f"Auto-processing failed for document {document.id}: {e}")
            db.rollback()
        
        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            original_filename=document.original_filename,
            file_size=document.file_size,
            file_type=document.file_type,
            uploaded_at=document.uploaded_at,
            processed=document.processed,
            processed_at=document.processed_at,
            chunk_count=document.chunk_count,
            title=document.title,
            description=document.description
        )
        
    except Exception as e:
        # Clean up file if database operation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading document: {str(e)}"
        )

@router.post("/documents/{document_id}/process")
async def process_document(
    document_id: int,
    process_request: DocumentProcessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_doc_service)
):
    """
    Process a document by chunking and creating embeddings
    """
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.processed:
        raise HTTPException(status_code=400, detail="Document already processed")
    
    try:
        # Process document
        chunks_created = await doc_service.process_document(
            document=document,
            chunk_size=process_request.chunk_size,
            chunk_overlap=process_request.chunk_overlap,
            db=db
        )
        
        # Update document status
        document.processed = True
        document.processed_at = datetime.now()
        document.chunk_count = chunks_created
        document.embedding_model = settings.EMBEDDING_MODEL
        
        db.commit()
        
        return {
            "message": f"Document processed successfully. Created {chunks_created} chunks.",
            "document_id": document.id,
            "chunks_created": chunks_created
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )

@router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    processed_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of uploaded documents
    """
    query = db.query(Document).filter(Document.user_id == current_user.id)
    
    if processed_only:
        query = query.filter(Document.processed == True)
    
    documents = query.order_by(
        Document.uploaded_at.desc()
    ).offset(skip).limit(limit).all()
    
    return [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            file_size=doc.file_size,
            file_type=doc.file_type,
            uploaded_at=doc.uploaded_at,
            processed=doc.processed,
            processed_at=doc.processed_at,
            chunk_count=doc.chunk_count,
            title=doc.title,
            description=doc.description
        )
        for doc in documents
    ]

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get specific document details
    """
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        original_filename=document.original_filename,
        file_size=document.file_size,
        file_type=document.file_type,
        uploaded_at=document.uploaded_at,
        processed=document.processed,
        processed_at=document.processed_at,
        chunk_count=document.chunk_count,
        title=document.title,
        description=document.description
    )

@router.post("/documents/search", response_model=List[DocumentSearchResult])
async def search_documents(
    search_request: DocumentSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_doc_service)
):
    """
    Search documents using semantic similarity
    """
    if search_request.document_ids:
        requested = set(search_request.document_ids)
        owned = db.query(Document.id).filter(Document.id.in_(requested), Document.user_id == current_user.id).count()
        if owned != len(requested):
            raise HTTPException(status_code=404, detail="Document not found")

    try:
        results = await doc_service.search_documents(
            query=search_request.query,
            user_id=current_user.id,
            document_ids=search_request.document_ids,
            limit=search_request.limit,
            similarity_threshold=search_request.similarity_threshold,
            db=db
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching documents: {str(e)}"
        )

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    rag_service: RagService = Depends(get_rag_service)
):
    """
    Delete a document and its associated data, including its embeddings in the vector store
    """
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Delete embeddings first, so a failure leaves the document record in place
        await rag_service.delete_by_document_id(document_id=document_id)

        # Delete file from disk
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete associated chunks
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        
        # Delete document record
        db.delete(document)
        db.commit()
        
        return {"message": "Document deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting document: {str(e)}"
        ) 