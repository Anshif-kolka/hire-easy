"""
Gemini LLM wrapper - unified interface for all LLM operations.
"""
import json
import time
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T', bound=BaseModel)


class GeminiLLM:
    """
    Unified wrapper around Google Gemini API.
    Handles text generation, structured output, and embeddings.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-flash-latest",
        embedding_model: str = "models/text-embedding-004",
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize Gemini LLM wrapper.
        
        Args:
            api_key: Google Gemini API key
            model: Model name for text generation
            embedding_model: Model name for embeddings
            max_retries: Number of retries on failure
            retry_delay: Delay between retries in seconds
        """
        self.api_key = api_key
        self.model_name = model
        self.embedding_model = embedding_model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Configure the API
        genai.configure(api_key=api_key)
        
        # Initialize the model
        self.model = genai.GenerativeModel(model)
        
        logger.info(f"Initialized GeminiLLM with model: {model}")
    
    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_instruction: Optional[str] = None
    ) -> str:
        """
        Generate text response from a prompt.
        
        Args:
            prompt: The input prompt
            temperature: Creativity parameter (0-1)
            max_tokens: Maximum output tokens
            system_instruction: Optional system prompt
            
        Returns:
            Generated text response
        """
        for attempt in range(self.max_retries):
            try:
                generation_config = genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
                
                if system_instruction:
                    model = genai.GenerativeModel(
                        self.model_name,
                        system_instruction=system_instruction
                    )
                else:
                    model = self.model
                
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
                
                return response.text
                
            except google_exceptions.ResourceExhausted:
                logger.warning(f"Rate limited, attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise
            except Exception as e:
                logger.error(f"Error generating text: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise
    
    def generate_structured(
        self,
        prompt: str,
        output_model: Type[T],
        temperature: float = 0.3,
        system_instruction: Optional[str] = None
    ) -> T:
        """
        Generate structured output that conforms to a Pydantic model.
        
        Args:
            prompt: The input prompt
            output_model: Pydantic model class for output validation
            temperature: Creativity parameter (lower is more deterministic)
            system_instruction: Optional system prompt
            
        Returns:
            Instance of the output_model
        """
        # Build schema description from the model
        schema = output_model.model_json_schema()
        
        structured_prompt = f"""{prompt}

Please respond with a valid JSON object that matches this schema:
{json.dumps(schema, indent=2)}

Respond ONLY with the JSON object, no additional text or markdown."""

        if system_instruction:
            full_system = f"{system_instruction}\n\nYou must respond with valid JSON only."
        else:
            full_system = "You are a helpful assistant that responds with valid JSON only."
        
        for attempt in range(self.max_retries):
            try:
                response_text = self.generate_text(
                    prompt=structured_prompt,
                    temperature=temperature,
                    system_instruction=full_system
                )
                
                # Clean the response (remove markdown code blocks if present)
                cleaned = response_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
                
                # Parse JSON and validate with Pydantic
                data = json.loads(cleaned)
                return output_model.model_validate(data)
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    continue
                raise ValueError(f"Failed to parse LLM response as JSON: {e}")
            except Exception as e:
                logger.error(f"Error in structured generation: {e}")
                if attempt < self.max_retries - 1:
                    continue
                raise
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        for attempt in range(self.max_retries):
            try:
                # Truncate text if too long (embedding models have limits)
                max_chars = 10000
                if len(text) > max_chars:
                    text = text[:max_chars]
                
                result = genai.embed_content(
                    model=self.embedding_model,
                    content=text,
                    task_type="retrieval_document"
                )
                
                return result['embedding']
                
            except google_exceptions.ResourceExhausted:
                logger.warning(f"Rate limited on embedding, attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise
            except Exception as e:
                logger.error(f"Error generating embedding: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = self.embed_text(text)
            embeddings.append(embedding)
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        return embeddings
