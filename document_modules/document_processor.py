"""
Document Processing Module

Handles document uploading, text extraction, chunking, and embedding.
"""
import os
import uuid
from typing import List, Dict, Any
from pathlib import Path

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class DocumentProcessor:
    """Handles document upload, text extraction, and chunking."""
    
    def __init__(self, document_dir: str = "./documents"):
        """Initialize the document processor.
        
        Args:
            document_dir: Directory to store uploaded documents
        """
        self.document_dir = Path(document_dir)
        self.document_dir.mkdir(exist_ok=True, parents=True)
        
    def save_uploaded_file(self, uploaded_file, access_level: str = "Public") -> str:
        """Save an uploaded file to disk.
        
        Args:
            uploaded_file: File object from Streamlit or similar
            access_level: Access level for the document
            
        Returns:
            str: Path to saved document
        """
        # Create a unique filename
        file_id = str(uuid.uuid4())
        file_extension = Path(uploaded_file.name).suffix
        filename = f"{file_id}{file_extension}"
        
        file_path = self.document_dir / filename
        
        # Save the file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        return str(file_path)
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text content from a PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            str: Extracted text content
        """
        text = ""
        with open(file_path, "rb") as file:
            pdf_reader = PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
                
        return text
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Document]:
        """Split text into chunks for processing.
        
        Args:
            text: Text to split
            metadata: Metadata to attach to each chunk
            
        Returns:
            List[Document]: List of document chunks with metadata
        """
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        if metadata is None:
            metadata = {}
            
        chunks = text_splitter.create_documents([text], [metadata])
        return chunks
    
    def process_document(self, file_path: str, metadata: Dict[str, Any] = None) -> List[Document]:
        """Process document: extract text, split into chunks.
        
        Args:
            file_path: Path to document
            metadata: Metadata for the document
            
        Returns:
            List[Document]: Processed document chunks
        """
        if metadata is None:
            metadata = {}
            
        # Add file path to metadata
        metadata["source"] = file_path
            
        # Extract text
        text = self.extract_text_from_pdf(file_path)
        
        # Split into chunks
        chunks = self.chunk_text(text, metadata)
        
        return chunks
