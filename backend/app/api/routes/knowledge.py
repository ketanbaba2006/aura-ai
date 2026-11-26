"""
AURA AI Knowledge Base Route
Endpoints for uploading (including chunked resumable uploads), listing, and searching documents.
"""

import os
import shutil
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, BackgroundTasks

from app.knowledge.knowledge_manager import knowledge_manager
from app.database.schemas import KnowledgeSearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])

# Allowed extensions
ALLOWED_EXTENSIONS = {
    # Text / Docs
    "pdf", "docx", "doc", "txt", "md", "markdown", "csv", "xlsx", "xls", "pptx", "ppt",
    # Images
    "png", "jpg", "jpeg", "webp", "gif", "bmp",
    # Code Files
    "py", "java", "c", "cpp", "h", "hpp", "js", "ts", "jsx", "tsx", "css", "html", "htm", "json", "xml", "yaml", "yml",
    # Archives
    "zip", "rar",
    # Audio / Video
    "mp3", "wav", "m4a", "ogg", "flac", "mp4", "avi", "mkv", "mov", "webm"
}

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    conversation_id: str | None = Form(None)
):
    """Upload document for knowledge base ingestion. Runs parsing and embedding in the background."""
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Filename missing.")

    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: .{ext}."
        )

    try:
        content = await file.read()
        file_size = len(content)

        # Create metadata row in status 'processing'
        doc_id = await knowledge_manager.create_document_placeholder(
            filename=filename,
            file_size=file_size,
            conversation_id=conversation_id,
            file_type=file.content_type or ext
        )

        # Save to permanent path
        root = Path(__file__).resolve().parent.parent.parent.parent
        dest = root / "user_files" / "Uploaded Files" / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        logger.info(f"Sandbox copy of uploaded file saved to: {dest}")

        # Trigger background processing task
        background_tasks.add_task(
            knowledge_manager.ingest_document_background,
            doc_id=doc_id,
            filepath=str(dest),
            filename=filename,
            conversation_id=conversation_id
        )

        return {
            "id": doc_id,
            "filename": filename,
            "status": "processing",
            "file_size": file_size,
            "message": "File upload accepted. Ingestion processing in background."
        }
    except Exception as e:
        logger.error(f"Failed to upload document {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload/chunk")
async def upload_chunk(
    background_tasks: BackgroundTasks,
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    filename: str = Form(...),
    conversation_id: str | None = Form(None),
    file: UploadFile = File(...)
):
    """Receives binary chunk slices, merging and triggers background indexing when complete."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    temp_dir = root / "user_files" / "temp_uploads" / upload_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    chunk_filepath = temp_dir / f"chunk_{chunk_index}"
    
    # Save chunk
    try:
        content = await file.read()
        chunk_filepath.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write chunk {chunk_index}: {e}")

    # Check if all chunks have been uploaded
    uploaded_chunks = [f for f in os.listdir(temp_dir) if f.startswith("chunk_")]
    if len(uploaded_chunks) == total_chunks:
        # All slices uploaded! Merge them together.
        dest = root / "user_files" / "Uploaded Files" / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"All {total_chunks} chunks received for '{filename}'. Merging slices...")
            with open(dest, "wb") as outfile:
                for idx in range(total_chunks):
                    slice_path = temp_dir / f"chunk_{idx}"
                    if not slice_path.exists():
                        raise FileNotFoundError(f"Missing chunk index {idx} during compile.")
                    outfile.write(slice_path.read_bytes())

            # Cleanup temp directory
            shutil.rmtree(temp_dir)
            
            # Fetch final merged file size
            file_size = dest.stat().st_size
            
            # Create metadata row in status 'processing'
            doc_id = await knowledge_manager.create_document_placeholder(
                filename=filename,
                file_size=file_size,
                conversation_id=conversation_id,
                file_type=file.content_type or (filename.split(".")[-1].lower() if "." in filename else "text")
            )

            # Trigger background indexing
            background_tasks.add_task(
                knowledge_manager.ingest_document_background,
                doc_id=doc_id,
                filepath=str(dest),
                filename=filename,
                conversation_id=conversation_id
            )

            return {
                "status": "completed",
                "id": doc_id,
                "filename": filename,
                "file_size": file_size,
                "message": "Upload complete. Compilation and background ingestion active."
            }

        except Exception as err:
            logger.error(f"Failed to compile chunked file '{filename}': {err}")
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            raise HTTPException(status_code=500, detail=f"Merge error: {err}")

    return {
        "status": "uploading",
        "chunk_index": chunk_index,
        "message": f"Chunk {chunk_index + 1}/{total_chunks} received successfully."
    }

@router.get("/upload/status")
async def check_upload_status(upload_id: str = Query(...)):
    """Status endpoint to query list of uploaded chunks, enabling client resumption."""
    root = Path(__file__).resolve().parent.parent.parent.parent
    temp_dir = root / "user_files" / "temp_uploads" / upload_id

    if not temp_dir.exists():
        return {"uploaded_chunks": []}

    try:
        # Collect chunk file indices
        chunk_files = [f for f in os.listdir(temp_dir) if f.startswith("chunk_")]
        indices = []
        for cf in chunk_files:
            try:
                indices.append(int(cf.split("_")[1]))
            except ValueError:
                pass
        return {"uploaded_chunks": sorted(indices)}
    except Exception as e:
        logger.error(f"Failed to check upload status for {upload_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{conversation_id}/files")
async def list_conversation_files(conversation_id: str):
    """Retrieve list of files ingested inside the current conversation bounds."""
    try:
        docs = await knowledge_manager.list_conversation_documents(conversation_id)
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents")
async def list_documents():
    """Get list of indexed knowledge base documents."""
    docs = await knowledge_manager.list_documents()
    return docs

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document and all its chunks from the database and vector index."""
    try:
        await knowledge_manager.delete_document(doc_id)
        return {"status": "deleted", "id": doc_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    q: str = Query(..., min_length=1, description="Search term"),
    conversation_id: str | None = Query(None, description="Conversation ID scoping"),
    limit: int = Query(5, ge=1, le=20),
):
    """Semantic vector search across indexed documents."""
    try:
        results = await knowledge_manager.search_knowledge(q, conversation_id, limit)
        return KnowledgeSearchResponse(query=q, results=results)
    except Exception as e:
        logger.error(f"Failed search: {e}")
        raise HTTPException(status_code=500, detail=str(e))
