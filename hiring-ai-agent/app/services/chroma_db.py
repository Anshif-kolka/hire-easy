"""
ChromaDB wrapper - vector store operations for embeddings.
"""
import chromadb
from chromadb.config import Settings
from typing import Any, Dict, List, Optional
import uuid

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ChromaStore:
    """
    Wrapper around ChromaDB for storing and querying embeddings.
    """
    
    def __init__(self, persist_dir: str = "data/chroma_db"):
        """
        Initialize ChromaDB client.
        
        Args:
            persist_dir: Directory to persist the database
        """
        self.persist_dir = persist_dir
        
        # Initialize persistent client
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        logger.info(f"Initialized ChromaDB at: {persist_dir}")
    
    def get_or_create_collection(self, collection_name: str) -> chromadb.Collection:
        """
        Get or create a collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            ChromaDB Collection object
        """
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
    
    def add_embedding(
        self,
        collection_name: str,
        id: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        document: Optional[str] = None
    ) -> None:
        """
        Add a single embedding to a collection.
        
        Args:
            collection_name: Target collection
            id: Unique ID for the embedding
            embedding: Vector embedding
            metadata: Optional metadata dict
            document: Optional document text
        """
        collection = self.get_or_create_collection(collection_name)
        
        collection.add(
            ids=[id],
            embeddings=[embedding],
            metadatas=[metadata] if metadata else None,
            documents=[document] if document else None
        )
        
        logger.debug(f"Added embedding {id} to collection {collection_name}")
    
    def add_embeddings(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[str]] = None
    ) -> None:
        """
        Add multiple embeddings to a collection.
        
        Args:
            collection_name: Target collection
            ids: List of unique IDs
            embeddings: List of vector embeddings
            metadatas: Optional list of metadata dicts
            documents: Optional list of document texts
        """
        collection = self.get_or_create_collection(collection_name)
        
        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        
        logger.info(f"Added {len(ids)} embeddings to collection {collection_name}")
    
    def query_similar(
        self,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 10,
        where: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Query for similar embeddings.
        
        Args:
            collection_name: Collection to query
            query_embedding: Query vector
            top_k: Number of results to return
            where: Optional filter conditions
            include: Fields to include in results
            
        Returns:
            Query results with ids, distances, metadatas, documents
        """
        collection = self.get_or_create_collection(collection_name)
        
        if include is None:
            include = ["metadatas", "documents", "distances"]
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=include
        )
        
        logger.debug(f"Query returned {len(results['ids'][0])} results from {collection_name}")
        
        return results
    
    def get_by_id(
        self,
        collection_name: str,
        id: str,
        include: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific embedding by ID.
        
        Args:
            collection_name: Collection to query
            id: ID to fetch
            include: Fields to include
            
        Returns:
            Record data or None if not found
        """
        collection = self.get_or_create_collection(collection_name)
        
        if include is None:
            include = ["metadatas", "documents", "embeddings"]
        
        results = collection.get(
            ids=[id],
            include=include
        )
        
        if results['ids']:
            return {
                'id': results['ids'][0],
                'metadata': results['metadatas'][0] if results.get('metadatas') else None,
                'document': results['documents'][0] if results.get('documents') else None,
                'embedding': results['embeddings'][0] if results.get('embeddings') else None
            }
        return None
    
    def update_embedding(
        self,
        collection_name: str,
        id: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        document: Optional[str] = None
    ) -> None:
        """
        Update an existing embedding.
        
        Args:
            collection_name: Collection name
            id: ID to update
            embedding: New embedding (optional)
            metadata: New metadata (optional)
            document: New document (optional)
        """
        collection = self.get_or_create_collection(collection_name)
        
        collection.update(
            ids=[id],
            embeddings=[embedding] if embedding else None,
            metadatas=[metadata] if metadata else None,
            documents=[document] if document else None
        )
        
        logger.debug(f"Updated embedding {id} in collection {collection_name}")
    
    def delete(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Delete embeddings from a collection.
        
        Args:
            collection_name: Collection name
            ids: List of IDs to delete
            where: Filter condition for deletion
        """
        collection = self.get_or_create_collection(collection_name)
        
        if ids:
            collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} embeddings from {collection_name}")
        elif where:
            collection.delete(where=where)
            logger.info(f"Deleted embeddings matching filter from {collection_name}")
    
    def count(self, collection_name: str) -> int:
        """
        Count embeddings in a collection.
        
        Args:
            collection_name: Collection name
            
        Returns:
            Number of embeddings
        """
        collection = self.get_or_create_collection(collection_name)
        return collection.count()
    
    def list_collections(self) -> List[str]:
        """
        List all collection names.
        
        Returns:
            List of collection names
        """
        collections = self.client.list_collections()
        return [c.name for c in collections]
    
    def delete_collection(self, collection_name: str) -> None:
        """
        Delete an entire collection.
        
        Args:
            collection_name: Collection to delete
        """
        self.client.delete_collection(name=collection_name)
        logger.info(f"Deleted collection: {collection_name}")
