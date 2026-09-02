"""Embedding generation using CLIP (multimodal text + image)."""

from typing import List, Tuple, Union
import io
import numpy as np
from sentence_transformers import SentenceTransformer
from PIL import Image

from src.models import Passage
from src.utils.logger import setup_logger, log_event
from src.utils.constants import EMBEDDING_MODEL

logger = setup_logger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for passages using CLIP (handles text + images)."""
    
    def __init__(self):
        """Initialize the embedding generator with CLIP model."""
        try:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            self.model = SentenceTransformer(EMBEDDING_MODEL)
            self.is_clip = "clip" in EMBEDDING_MODEL.lower()
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise ValueError(f"Could not load embedding model '{EMBEDDING_MODEL}': {e}")
    
    def embed_passages(self, passages: List[Passage]) -> List[List[float]]:
        """Generate embeddings for a list of passages (hybrid text + image).
        
        For passages with images, creates dual embeddings:
        - Image embedding (if is_diagram=True)
        - Text embedding (OCR'd text)
        
        For text-only passages, creates text embedding.
        
        Args:
            passages: List of passages to embed.
        
        Returns:
            List of embedding vectors (each is a list of floats).
        """
        if not passages:
            return []
        
        try:
            embeddings = []
            image_passages = []
            text_passages = []
            
            # Separate image and text passages
            for idx, p in enumerate(passages):
                if p.is_diagram and p.image_bytes:
                    image_passages.append((idx, p))
                else:
                    text_passages.append((idx, p))
            
            # Initialize embedding dict
            embedding_dict = {}
            
            # Process text passages (including OCR'd diagrams)
            if text_passages:
                logger.info(f"Generating text embeddings for {len(text_passages)} passages...")
                texts = [p.text for _, p in text_passages]
                text_embeddings = self.model.encode(
                    texts,
                    convert_to_tensor=False,
                    show_progress_bar=True,
                    batch_size=32
                )
                if isinstance(text_embeddings, np.ndarray):
                    text_embeddings = text_embeddings.tolist()
                
                for (idx, _), emb in zip(text_passages, text_embeddings):
                    embedding_dict[idx] = emb
            
            # Process image passages (CLIP image encoding)
            if image_passages and self.is_clip:
                logger.info(f"Generating image embeddings for {len(image_passages)} diagrams...")
                for idx, passage in image_passages:
                    try:
                        # Decode image bytes
                        image = Image.open(io.BytesIO(passage.image_bytes))
                        
                        # Encode image using CLIP
                        img_embedding = self.model.encode(image, convert_to_tensor=False)
                        if isinstance(img_embedding, np.ndarray):
                            img_embedding = img_embedding.tolist()
                        
                        # Store image embedding (optionally combine with text embedding)
                        embedding_dict[idx] = img_embedding
                        logger.info(f"Generated image embedding for passage {idx}")
                    except Exception as e:
                        logger.warning(f"Failed to embed image for passage {idx}: {e}")
                        # Fallback to text embedding if image fails
                        if passage.text.strip():
                            text_emb = self.model.encode(passage.text, convert_to_tensor=False)
                            if isinstance(text_emb, np.ndarray):
                                text_emb = text_emb.tolist()
                            embedding_dict[idx] = text_emb
            
            # Reconstruct embeddings in original order
            embeddings = [embedding_dict.get(i, [0] * 384) for i in range(len(passages))]
            
            logger.info(f"Successfully generated {len(embeddings)} embeddings")
            log_event(
                "embed_passages",
                passage_count=len(passages),
                text_count=len(text_passages),
                image_count=len(image_passages),
                embedding_model=EMBEDDING_MODEL,
            )
            
            return embeddings
        
        except Exception as e:
            logger.exception(f"Failed to generate embeddings: {e}")
            raise
    
    def embed_query(self, query_text: str) -> List[float]:
        """Generate embedding for a query.
        
        Args:
            query_text: The query text.
        
        Returns:
            Embedding vector (list of floats).
        """
        try:
            embedding = self.model.encode(query_text, convert_to_tensor=False)
            # Convert to list if numpy array
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            return embedding
        except Exception as e:
            logger.exception(f"Failed to embed query: {e}")
            raise
