"""
Vector Database Module

Handles document embedding storage and retrieval using FAISS.
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document


class VectorDatabase:
    """Vector database for storing and retrieving document embeddings."""
    
    def __init__(self, db_path: str = "./vector_db", embedding_model: str = "text-embedding-3-small"):
        """Initialize the vector database.
        
        Args:
            db_path: Path to store the vector database
            embedding_model: OpenAI embedding model to use
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(exist_ok=True, parents=True)
        
        # Initialize embedding model
        self.embeddings = OpenAIEmbeddings(model=embedding_model)
        
        # Initialize or load vector store
        self.vector_store = self._load_or_create_vector_store()
        
    def _load_or_create_vector_store(self) -> FAISS:
        """Load existing vector store or create a new one.
        
        Returns:
            FAISS: Vector store instance
        """
        if (self.db_path / "index.faiss").exists():
            return FAISS.load_local(
                str(self.db_path), 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
        
        # Create an empty vector store if none exists
        empty_vector_store = FAISS.from_documents(
            [Document(page_content="", metadata={})], 
            self.embeddings
        )
        
        # Save the empty vector store
        empty_vector_store.save_local(str(self.db_path))
        
        return empty_vector_store
    
    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the vector store.
        
        Args:
            documents: List of document chunks to add
        """
        if not documents:
            return
        
        # Add documents to existing store
        self.vector_store.add_documents(documents)
        
        # Save the updated vector store
        self.vector_store.save_local(str(self.db_path))
        
    def similarity_search(self, query: str, k: int = 4, filter: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Search for relevant documents based on query.
        
        Args:
            query: Search query
            k: Number of results to return
            filter: Optional filter based on metadata
            
        Returns:
            List[Document]: Relevant document chunks
        """
        return self.vector_store.similarity_search(query, k=k, filter=filter)
    
    def search(self, query: str, limit: int = 5, user_role: str = None) -> List[Document]:
        """Search for documents with role-based access control.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            user_role: User role for access control filtering
            
        Returns:
            List[Document]: List of relevant document chunks
        """
        # Define access control logic - users can access documents at their level and below
        role_access = {
            "Junior": ["Junior"],
            "Senior": ["Junior", "Senior"],
            "Manager": ["Junior", "Senior", "Manager"],
            "Admin": ["Junior", "Senior", "Manager", "Admin"]
        }
        
        # Get accessible document levels for the user role
        accessible_levels = role_access.get(user_role, ["Junior"])
        
        # Create filter for metadata-based filtering
        filter_dict = {
            "min_access_level": {"$in": accessible_levels}
        }
        
        # Perform similarity search with filtering
        try:
            results = self.vector_store.similarity_search(
                query=query, 
                k=limit,
                filter=filter_dict
            )
            return results
        except Exception as e:
            print(f"Search error: {str(e)}")
            return []

    def delete_document_chunks(self, document_id: str) -> Dict[str, Any]:
        """Delete all chunks belonging to a specific document.
        
        Args:
            document_id: The document ID to delete chunks for
            
        Returns:
            Dict with deletion status and count
        """
        try:
            # FAISS doesn't support direct deletion by metadata filter
            # We need to rebuild the vector store without the deleted document's chunks
            
            # Get all documents from the vector store
            all_docs = []
            try:
                # Get the internal docstore to access all documents
                docstore = self.vector_store.docstore
                index_to_docstore_id = self.vector_store.index_to_docstore_id
                
                # Collect all documents except those from the document to delete
                deleted_count = 0
                for i, doc_id in index_to_docstore_id.items():
                    doc = docstore.search(doc_id)
                    if doc and doc.metadata.get('document_id') != document_id:
                        all_docs.append(doc)
                    elif doc and doc.metadata.get('document_id') == document_id:
                        deleted_count += 1
                
                if deleted_count == 0:
                    return {
                        "success": True,
                        "message": f"No chunks found for document {document_id}",
                        "deleted_count": 0
                    }
                
                # Rebuild vector store without deleted document chunks
                if all_docs:
                    # Create new vector store with remaining documents
                    new_vector_store = FAISS.from_documents(all_docs, self.embeddings)
                else:
                    # Create empty vector store if no documents remain
                    new_vector_store = FAISS.from_documents(
                        [Document(page_content="", metadata={})], 
                        self.embeddings
                    )
                
                # Replace the current vector store
                self.vector_store = new_vector_store
                
                # Save the updated vector store
                self.vector_store.save_local(str(self.db_path))
                
                return {
                    "success": True,
                    "message": f"Deleted {deleted_count} chunks for document {document_id}",
                    "deleted_count": deleted_count
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error accessing vector store internals: {str(e)}",
                    "deleted_count": 0
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error deleting document chunks: {str(e)}",
                "deleted_count": 0
            }
    
    def get_document_chunk_count(self, document_id: str) -> int:
        """Get the number of chunks for a specific document.
        
        Args:
            document_id: The document ID to count chunks for
            
        Returns:
            Number of chunks for the document
        """
        try:
            docstore = self.vector_store.docstore
            index_to_docstore_id = self.vector_store.index_to_docstore_id
            
            count = 0
            for i, doc_id in index_to_docstore_id.items():
                doc = docstore.search(doc_id)
                if doc and doc.metadata.get('document_id') == document_id:
                    count += 1
            
            return count
        except Exception as e:
            print(f"Error counting document chunks: {str(e)}")
            return 0
