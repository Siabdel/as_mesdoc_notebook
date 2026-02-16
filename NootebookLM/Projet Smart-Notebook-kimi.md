# Projet Smart-Notebook

> Created le 3 Fev 2026
>
> author : AS + kimi 2.5



 Je vais architecturer ce projet **Smart-Notebook** en respectant tes contraintes matérielles (RTX 3060 6GB / 16GB RAM) et ta stratégie hybride intelligente. Voici l'architecture complète :

## 🏗️ Arborescence Recommandée `backend/`

```
backend/
├── config/                      # Configuration Django
│   ├── __init__.py
│   ├── settings/
│   │   ├── base.py             # Configuration de base
│   │   ├── local.py            # Dev local
│   │   └── production.py       # Production
│   ├── urls.py                 # Routes principales
│   ├── asgi.py
│   └── wsgi.py
├── apps/                        # Applications métier
│   ├── core/                    # Utilitaires partagés
│   │   ├── __init__.py
│   │   ├── exceptions.py        # Exceptions personnalisées
│   │   └── utils.py
│   ├── documents/               # Gestion des documents (PDF, OCR)
│   │   ├── __init__.py
│   │   ├── models.py            # SourceDocument, DocumentChunk
│   │   ├── admin.py
│   │   ├── serializers.py
│   │   ├── views.py             # Upload, gestion docs
│   │   ├── tasks.py             # Celery: ingestion, chunking, embedding
│   │   └── services/
│   │       ├── ocr_service.py   # OCR placeholder (Tesseract/pikepdf)
│   │       └── pdf_extractor.py # Extraction texte PDF
│   ├── ai_engine/               # Moteur IA hybride
│   │   ├── __init__.py
│   │   ├── ai_router.py         # Routeur Ollama/OpenRouter
│   │   ├── clients/
│   │   │   ├── __init__.py
│   │   │   ├── ollama_client.py # Client Ollama (embeddings)
│   │   │   └── openrouter_client.py # Client OpenRouter (LLM)
│   │   └── services/
│   │       ├── rag_service.py   # Service RAG complet
│   │       └── podcast_service.py # Génération podcast
│   ├── chat/                    # Interface conversationnelle
│   │   ├── __init__.py
│   │   ├── models.py            # Conversations, messages
│   │   ├── views.py             # AskDocumentView (RAG endpoint)
│   │   └── serializers.py
│   └── audio/                   # Génération audio TTS
│       ├── __init__.py
│       ├── models.py            # Podcast episodes, audio files
│       ├── tasks.py             # Celery: génération audio edge-tts
│       └── services/
│           └── tts_service.py   # Wrapper edge-tts
├── media/                       # Fichiers uploadés (PDFs)
│   └── documents/
├── static/                      # Static files Django
├── templates/                   # Templates Django (admin...)
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── manage.py
├── celery_app.py                # Configuration Celery
└── docker-compose.yml           # PostgreSQL + pgvector, Redis
```

---

## 1. `apps/documents/models.py`

```python
"""
Modèles de données pour la gestion des documents et des chunks vectorisés.
Utilise pgvector pour le stockage et la recherche vectorielle.
"""

import uuid
from typing import List, Optional

from django.db import models
from django.contrib.postgres.indexes import GinIndex
from pgvector.django import VectorField, L2Distance

from apps.core.models import TimeStampedModel


class SourceDocument(TimeStampedModel):
    """
    Document source uploadé par l'utilisateur (PDF, texte, etc.).
    """
    id: models.UUIDField = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    title: models.CharField = models.CharField(
        max_length=255, 
        verbose_name="Titre du document"
    )
    file: models.FileField = models.FileField(
        upload_to="documents/%Y/%m/%d/",
        verbose_name="Fichier source"
    )
    file_type: models.CharField = models.CharField(
        max_length=50,
        choices=[
            ("pdf", "PDF"),
            ("txt", "Texte"),
            ("md", "Markdown"),
            ("docx", "Word"),
        ],
        default="pdf",
        verbose_name="Type de fichier"
    )
    content_text: models.TextField = models.TextField(
        blank=True,
        verbose_name="Contenu textuel extrait"
    )
    total_chunks: models.IntegerField = models.IntegerField(
        default=0,
        verbose_name="Nombre total de chunks"
    )
    embedding_model: models.CharField = models.CharField(
        max_length=100,
        default="nomic-embed-text",
        verbose_name="Modèle d'embedding utilisé"
    )
    is_processed: models.BooleanField = models.BooleanField(
        default=False,
        verbose_name="Traitement terminé"
    )
    processing_error: models.TextField = models.TextField(
        blank=True,
        null=True,
        verbose_name="Erreur de traitement"
    )

    class Meta:
        db_table = "source_documents"
        ordering = ["-created_at"]
        indexes = [
            GinIndex(
                name="source_doc_title_gin",
                fields=["title"],
                opclasses=["gin_trgm_ops"]
            ),
        ]
        verbose_name = "Document source"
        verbose_name_plural = "Documents sources"

    def __str__(self) -> str:
        return f"{self.title} ({self.file_type})"


class DocumentChunk(TimeStampedModel):
    """
    Segment de document avec embedding vectoriel pour la recherche sémantique.
    """
    id: models.UUIDField = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    document: models.ForeignKey = models.ForeignKey(
        SourceDocument,
        on_delete=models.CASCADE,
        related_name="chunks",
        verbose_name="Document parent"
    )
    chunk_index: models.IntegerField = models.IntegerField(
        verbose_name="Index du chunk"
    )
    content: models.TextField = models.TextField(
        verbose_name="Contenu textuel du chunk"
    )
    # Champ pgvector pour l'embedding (dimension 768 pour nomic-embed-text)
    embedding: VectorField = VectorField(
        dimensions=768,
        null=True,  # Temporairement null pendant le traitement
        verbose_name="Vecteur d'embedding"
    )
    token_count: models.IntegerField = models.IntegerField(
        null=True,
        verbose_name="Nombre de tokens"
    )
    char_count: models.IntegerField = models.IntegerField(
        null=True,
        verbose_name="Nombre de caractères"
    )
    page_number: models.IntegerField = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Numéro de page (si applicable)"
    )
    
    # Métadonnées pour le contexte RAG
    context_before: models.TextField = models.TextField(
        blank=True,
        verbose_name="Contexte précédent (preview)"
    )
    context_after: models.TextField = models.TextField(
        blank=True,
        verbose_name="Contexte suivant (preview)"
    )

    class Meta:
        db_table = "document_chunks"
        ordering = ["document", "chunk_index"]
        # Index HNSW pour la recherche vectorielle rapide (pgvector 0.5+)
        indexes = [
            models.Index(
                name="chunk_doc_idx_idx",
                fields=["document", "chunk_index"]
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="unique_chunk_per_doc"
            )
        ]
        verbose_name = "Segment de document"
        verbose_name_plural = "Segments de documents"

    def __str__(self) -> str:
        return f"Chunk {self.chunk_index} de {self.document.title}"

    @classmethod
    def search_similar(
        cls, 
        query_embedding: List[float], 
        top_k: int = 5,
        document_id: Optional[uuid.UUID] = None
    ) -> models.QuerySet:
        """
        Recherche les chunks les plus similaires par distance L2.
        
        Args:
            query_embedding: Vecteur de la requête (768 dimensions)
            top_k: Nombre de résultats à retourner
            document_id: Filtrer sur un document spécifique (optionnel)
        
        Returns:
            QuerySet ordonné par distance de similarité
        """
        queryset = cls.objects.filter(embedding__isnull=False)
        
        if document_id:
            queryset = queryset.filter(document_id=document_id)
        
        # Recherche par distance L2 (Euclidienne) - pgvector gère l'indexation
        return queryset.annotate(
            distance=L2Distance("embedding", query_embedding)
        ).order_by("distance")[:top_k]

    def get_context_window(self, window_size: int = 200) -> str:
        """
        Retourne le chunk avec un peu de contexte pour le RAG.
        """
        preview = self.content
        if len(preview) > window_size:
            return preview[:window_size] + "..."
        return preview
```

---

## 2. `apps/ai_engine/ai_router.py`

```python
"""
Routeur IA hybride : Ollama (Local) pour les embeddings, OpenRouter (Cloud) pour le LLM.
Gestion robuste des erreurs et retry logic.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

import httpx
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """Exception levée en cas d'erreur de fournisseur IA."""
    pass


class OllamaError(AIProviderError):
    """Erreur spécifique au serveur Ollama local."""
    pass


class OpenRouterError(AIProviderError):
    """Erreur spécifique à l'API OpenRouter."""
    pass


class ProviderType(Enum):
    """Types de fournisseurs IA disponibles."""
    LOCAL = "ollama"
    CLOUD = "openrouter"


@dataclass
class ChatMessage:
    """Message formaté pour l'API chat."""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class ChatResponse:
    """Réponse structurée du LLM."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None


class OllamaClient:
    """
    Client pour le serveur Ollama local (Embeddings uniquement).
    Léger et rapide sur CPU/GPU modeste.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        embedding_model: str = "nomic-embed-text",
        timeout: float = 30.0
    ):
        self.base_url = base_url.rstrip("/")
        self.embedding_model = embedding_model
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
        reraise=True
    )
    def generate_embedding(self, text: str) -> List[float]:
        """
        Génère un embedding vectoriel via Ollama (nomic-embed-text: 768 dims).
        
        Args:
            text: Texte à vectoriser
            
        Returns:
            Liste de 768 floats (embedding normalisé)
            
        Raises:
            OllamaError: Si le serveur Ollama est inaccessible ou erreur modèle
        """
        if not text or not text.strip():
            raise ValueError("Le texte ne peut pas être vide")
            
        # Troncature si nécessaire (nomic-embed-text gère ~8192 tokens)
        max_chars = 8000 * 4  # Approximation conservative
        if len(text) > max_chars:
            text = text[:max_chars]
            logger.warning(f"Texte tronqué pour embedding ({max_chars} chars)")
        
        try:
            response = self.client.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text
                }
            )
            response.raise_for_status()
            data = response.json()
            
            embedding = data.get("embedding")
            if not embedding or len(embedding) != 768:
                raise OllamaError(
                    f"Dimension d'embedding invalide: {len(embedding) if embedding else 0}"
                )
                
            logger.debug(f"Embedding généré: {len(embedding)} dimensions")
            return embedding
            
        except httpx.ConnectError as e:
            logger.error(f"Connexion Ollama impossible: {e}")
            raise OllamaError(
                f"Serveur Ollama inaccessible à {self.base_url}. "
                "Vérifiez qu'Ollama est démarré: `ollama serve`"
            ) from e
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Erreur HTTP Ollama: {e.response.status_code} - {e.response.text}")
            raise OllamaError(f"Erreur API Ollama: {e.response.status_code}") from e
            
        except Exception as e:
            logger.error(f"Erreur inattendue Ollama: {e}")
            raise OllamaError(f"Erreur embedding Ollama: {str(e)}") from e
    
    def health_check(self) -> bool:
        """Vérifie la disponibilité du serveur Ollama."""
        try:
            response = self.client.get(f"{self.base_url}/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False


class OpenRouterClient:
    """
    Client pour l'API OpenRouter (LLM Cloud).
    Supporte Claude 3.5 Sonnet, DeepSeek, etc.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        default_model: str = "anthropic/claude-3.5-sonnet",
        timeout: float = 60.0
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise OpenRouterError("Clé API OpenRouter manquante (OPENROUTER_API_KEY)")
            
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout
        self.client = httpx.Client(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": getattr(settings, "SITE_URL", "http://localhost:8000"),
                "X-Title": "Smart-Notebook",
                "Content-Type": "application/json"
            }
        )
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=15),
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException, OpenRouterError)),
        reraise=True
    )
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False
    ) -> ChatResponse:
        """
        Appelle le LLM via OpenRouter pour génération de texte/raisonnement.
        
        Args:
            messages: Liste de messages {"role": "user"/"system"/"assistant", "content": "..."}
            model: Modèle à utiliser (défaut: claude-3.5-sonnet)
            temperature: Créativité (0.0-1.0)
            max_tokens: Limite de tokens générés
            stream: Streaming (non implémenté ici)
            
        Returns:
            ChatResponse structurée
            
        Raises:
            OpenRouterError: Erreur API (rate limit, modèle indisponible, etc.)
        """
        model = model or self.default_model
        
        # Mapping des modèles alternatifs si le principal est indisponible
        fallback_models = [
            "anthropic/claude-3.5-sonnet",
            "deepseek/deepseek-chat",
            "openai/gpt-4o-mini",
        ]
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            # Routage intelligent OpenRouter
            "route": "fallback" if model != fallback_models[0] else None
        }
        
        # Nettoyer les clés None
        payload = {k: v for k, v in payload.items() if v is not None}
        
        try:
            logger.info(f"Appel OpenRouter: {model}")
            response = self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            
            # Gestion des erreurs OpenRouter spécifiques
            if "error" in data:
                error_msg = data["error"].get("message", "Erreur inconnue OpenRouter")
                raise OpenRouterError(f"OpenRouter API Error: {error_msg}")
            
            choice = data["choices"][0]
            message = choice.get("message", {})
            
            return ChatResponse(
                content=message.get("content", ""),
                model=data.get("model", model),
                usage=data.get("usage"),
                finish_reason=choice.get("finish_reason")
            )
            
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            status = e.response.status_code
            
            if status == 401:
                raise OpenRouterError("Clé API OpenRouter invalide") from e
            elif status == 429:
                raise OpenRouterError("Rate limit OpenRouter atteint") from e
            elif status == 402:
                raise OpenRouterError("Crédits OpenRouter insuffisants") from e
            elif status >= 500:
                raise OpenRouterError(f"Erreur serveur OpenRouter ({status})") from e
            else:
                raise OpenRouterError(f"Erreur HTTP {status}: {error_text}") from e
                
        except httpx.TimeoutException as e:
            logger.error("Timeout OpenRouter")
            raise OpenRouterError("Timeout lors de l'appel OpenRouter (60s)") from e
            
        except Exception as e:
            logger.error(f"Erreur inattendue OpenRouter: {e}")
            raise OpenRouterError(f"Erreur OpenRouter: {str(e)}") from e
    
    def build_rag_prompt(
        self,
        question: str,
        context_chunks: List[str],
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Construit les messages pour le RAG avec contexte.
        
        Args:
            question: Question de l'utilisateur
            context_chunks: Liste des chunks de contexte trouvés
            system_prompt: Instructions système personnalisées
            
        Returns:
            Liste formatée pour l'API chat
        """
        default_system = """Tu es un assistant expert en analyse de documents. 
Utilise UNIQUEMENT le contexte fourni ci-dessous pour répondre à la question. 
Si la réponse n'est pas dans le contexte, dis-le clairement. 
Cite les sources en référençant les passages pertinents."""

        context = "\n\n---\n\n".join([
            f"[Extrait {i+1}]\n{chunk}" 
            for i, chunk in enumerate(context_chunks)
        ])
        
        user_message = f"""Contexte des documents:
{context}

---
Question: {question}

Réponds de manière concise et précise en te basant uniquement sur le contexte ci-dessus."""

        return [
            {"role": "system", "content": system_prompt or default_system},
            {"role": "user", "content": user_message}
        ]


class AIRouter:
    """
    Routeur central qui orchestre Ollama (local) et OpenRouter (cloud).
    Point d'entrée unique pour toute l'IA du projet.
    """
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        openrouter_key: Optional[str] = None,
        embedding_model: str = "nomic-embed-text",
        llm_model: str = "anthropic/claude-3.5-sonnet"
    ):
        self.ollama = OllamaClient(
            base_url=ollama_url,
            embedding_model=embedding_model
        )
        self.openrouter = OpenRouterClient(
            api_key=openrouter_key,
            default_model=llm_model
        )
        self._ollama_available: Optional[bool] = None
        
    def check_ollama_status(self) -> bool:
        """Vérifie et cache le statut d'Ollama."""
        if self._ollama_available is None:
            self._ollama_available = self.ollama.health_check()
        return self._ollama_available
    
    def get_embedding(self, text: str) -> List[float]:
        """
        Génère un embedding via Ollama (local).
        Levée d'exception si Ollama est indisponible.
        """
        if not self.check_ollama_status():
            raise OllamaError(
                "Ollama non disponible. Démarrez le serveur: ollama pull nomic-embed-text && ollama serve"
            )
        return self.ollama.generate_embedding(text)
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> ChatResponse:
        """
        Génère une réponse LLM via OpenRouter (cloud).
        """
        return self.openrouter.chat_completion(messages, **kwargs)
    
    def rag_query(
        self,
        question: str,
        context_chunks: List[str],
        **llm_kwargs
    ) -> ChatResponse:
        """
        Pipeline RAG complet : construit le prompt avec contexte et appelle le LLM.
        """
        messages = self.openrouter.build_rag_prompt(question, context_chunks)
        return self.chat_completion(messages, **llm_kwargs)
    
    def close(self):
        """Ferme proprement les connexions HTTP."""
        self.ollama.client.close()
        self.openrouter.client.close()
```

---

## 3. `apps/documents/tasks.py`

```python
"""
Tâches Celery pour l'ingestion asynchrone de documents.
Extraction PDF → OCR → Chunking → Embeddings (Ollama) → Stockage pgvector.
"""

import logging
from typing import List, Optional
import uuid

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.db import transaction

from apps.documents.models import SourceDocument, DocumentChunk
from apps.ai_engine.ai_router import AIRouter, OllamaError
from apps.documents.services.pdf_extractor import PDFExtractorService
from apps.documents.services.ocr_service import OCRService

logger = logging.getLogger(__name__)


# Configuration du chunking
CHUNK_SIZE = 512  # Tokens approximatifs par chunk
CHUNK_OVERLAP = 50  # Chevauchement entre chunks pour la continuité


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(OllamaError, ConnectionError),
    retry_backoff=True,
    retry_backoff_max=300  # 5 minutes max entre retries
)
def process_document_ingestion(self, document_id: str) -> dict:
    """
    Pipeline complète d'ingestion d'un document PDF.
    
    Étapes:
    1. Extraction du texte (PDFExtractor + OCR si nécessaire)
    2. Découpage en chunks intelligents
    3. Génération des embeddings via Ollama (local)
    4. Stockage dans PostgreSQL/pgvector
    
    Args:
        document_id: UUID du SourceDocument à traiter
        
    Returns:
        Statistiques du traitement
    """
    doc_id = uuid.UUID(document_id)
    
    try:
        # Récupération du document
        document = SourceDocument.objects.get(pk=doc_id)
        logger.info(f"[Task {self.request.id}] Démarrage ingestion: {document.title}")
        
        # Mise à jour du statut
        document.is_processed = False
        document.processing_error = None
        document.save(update_fields=["is_processed", "processing_error"])
        
        # === ÉTAPE 1: Extraction du texte ===
        logger.info(f"Extraction texte: {document.file.path}")
        extractor = PDFExtractorService()
        
        try:
            extracted_text = extractor.extract_text(document.file.path)
            
            # Si peu de texte extrait, tentative OCR
            if len(extracted_text.strip()) < 100:
                logger.info("Peu de texte détecté, lancement OCR...")
                ocr_service = OCRService()
                extracted_text = ocr_service.extract_with_ocr(document.file.path)
                
        except Exception as e:
            raise Exception(f"Échec extraction PDF: {str(e)}")
        
        document.content_text = extracted_text
        document.save(update_fields=["content_text"])
        logger.info(f"Texte extrait: {len(extracted_text)} caractères")
        
        # === ÉTAPE 2: Chunking ===
        chunks = _create_chunks(extracted_text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        logger.info(f"Document découpé en {len(chunks)} chunks")
        
        # === ÉTAPE 3 & 4: Embeddings et stockage ===
        router = AIRouter()
        
        # Suppression des anciens chunks si retraitement
        DocumentChunk.objects.filter(document=document).delete()
        
        created_chunks = []
        errors = []
        
        # Traitement par batch pour optimiser
        for idx, chunk_text in enumerate(chunks):
            try:
                # Génération embedding local (Ollama)
                embedding = router.get_embedding(chunk_text)
                
                # Stockage immédiat
                with transaction.atomic():
                    chunk = DocumentChunk.objects.create(
                        document=document,
                        chunk_index=idx,
                        content=chunk_text,
                        embedding=embedding,
                        char_count=len(chunk_text),
                        page_number=_estimate_page_number(extracted_text, chunk_text, idx, len(chunks))
                    )
                    created_chunks.append(chunk.id)
                    
                logger.debug(f"Chunk {idx}/{len(chunks)} traité")
                
            except OllamaError as e:
                error_msg = f"Erreur Ollama sur chunk {idx}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                # On continue avec les autres chunks
                
            except Exception as e:
                error_msg = f"Erreur inattendue chunk {idx}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Finalisation
        document.total_chunks = len(created_chunks)
        document.is_processed = len(errors) == 0 or len(created_chunks) > 0
        if errors:
            document.processing_error = f"Chunks réussis: {len(created_chunks)}/{len(chunks)}. Erreurs: {errors[:3]}"
        document.save()
        
        router.close()
        
        result = {
            "document_id": str(doc_id),
            "total_chunks": len(chunks),
            "successful_chunks": len(created_chunks),
            "failed_chunks": len(errors),
            "errors": errors[:5]  # Limiter la taille
        }
        
        logger.info(f"Ingestion terminée: {result}")
        return result
        
    except SourceDocument.DoesNotExist:
        logger.error(f"Document {document_id} introuvable")
        raise
        
    except Exception as e:
        logger.exception(f"Erreur fatale ingestion {document_id}")
        
        # Mise à jour du statut d'erreur
        try:
            document = SourceDocument.objects.get(pk=doc_id)
            document.processing_error = str(e)
            document.save(update_fields=["processing_error"])
        except Exception:
            pass
            
        # Retry si possible
        if self.request.retries < self.max_retries:
            logger.info(f"Retry {self.request.retries + 1}/{self.max_retries} dans {self.default_retry_delay}s")
            raise self.retry(exc=e, countdown=self.default_retry_delay * (self.request.retries + 1))
        else:
            raise MaxRetriesExceededError(f"Échec définitif après {self.max_retries} tentatives")


def _create_chunks(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """
    Découpe le texte en chunks avec chevauchement, en respectant les limites de tokens.
    Stratégie: paragraphes > phrases > mots.
    """
    import re
    
    # Normalisation
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Séparation par paragraphes d'abord
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    
    chunks = []
    current_chunk = []
    current_length = 0
    
    # Estimation: 1 token ≈ 4 caractères pour l'anglais/français
    approx_tokens = lambda text: len(text) // 4
    
    for para in paragraphs:
        para_tokens = approx_tokens(para)
        
        if para_tokens > chunk_size:
            # Paragraphe trop long: découper par phrases
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sent in sentences:
                sent_tokens = approx_tokens(sent)
                
                if current_length + sent_tokens > chunk_size and current_chunk:
                    # Sauvegarder le chunk actuel
                    chunks.append(' '.join(current_chunk))
                    # Overlap: garder les derniers éléments
                    overlap_size = 0
                    overlap_chunk = []
                    for item in reversed(current_chunk):
                        item_tokens = approx_tokens(item)
                        if overlap_size + item_tokens <= overlap:
                            overlap_chunk.insert(0, item)
                            overlap_size += item_tokens
                        else:
                            break
                    current_chunk = overlap_chunk
                    current_length = overlap_size
                
                current_chunk.append(sent)
                current_length += sent_tokens
        else:
            if current_length + para_tokens > chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                # Overlap paragraphes
                current_chunk = current_chunk[-1:] if len(current_chunk) > 1 else []
                current_length = approx_tokens(current_chunk[0]) if current_chunk else 0
            
            current_chunk.append(para)
            current_length += para_tokens
    
    # Dernier chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    # Post-traitement: s'assurer qu'aucun chunk ne dépasse trop la limite
    final_chunks = []
    for chunk in chunks:
        if approx_tokens(chunk) > chunk_size * 1.5:
            # Découpe brute si toujours trop long
            words = chunk.split()
            temp_chunk = []
            temp_length = 0
            for word in words:
                word_tokens = len(word) // 4 + 1
                if temp_length + word_tokens > chunk_size and temp_chunk:
                    final_chunks.append(' '.join(temp_chunk))
                    temp_chunk = temp_chunk[-overlap//5:]  # ~10 mots d'overlap
                    temp_length = sum(len(w)//4 for w in temp_chunk)
                temp_chunk.append(word)
                temp_length += word_tokens
            if temp_chunk:
                final_chunks.append(' '.join(temp_chunk))
        else:
            final_chunks.append(chunk)
    
    return final_chunks


def _estimate_page_number(full_text: str, chunk_text: str, chunk_index: int, total_chunks: int) -> Optional[int]:
    """
    Estime le numéro de page basé sur la position dans le texte.
    Approximation pour documents non-OCR.
    """
    if not full_text:
        return None
    
    try:
        position = full_text.find(chunk_text[:100])  # Premiers 100 chars
        if position == -1:
            return chunk_index + 1  # Fallback
            
        ratio = position / len(full_text)
        # Estimation: 3000 chars par page moyenne
        estimated_page = int(ratio * (len(full_text) / 3000)) + 1
        return max(1, estimated_page)
    except Exception:
        return None
```

---

## 4. `apps/chat/views.py` (RAG Endpoint)

```python
"""
Vue API pour le RAG (Retrieval Augmented Generation).
Recherche vectorielle pgvector + LLM OpenRouter.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.shortcuts import get_object_or_404

from apps.documents.models import SourceDocument, DocumentChunk
from apps.ai_engine.ai_router import AIRouter, OllamaError, OpenRouterError
from apps.chat.serializers import QuestionSerializer, RAGResponseSerializer

logger = logging.getLogger(__name__)


class AskDocumentView(APIView):
    """
    Endpoint RAG principal: pose une question sur un ou plusieurs documents.
    
    Pipeline:
    1. Vectorisation de la question (Ollama/local)
    2. Recherche de similarité pgvector (L2 distance)
    3. Construction du contexte
    4. Génération de réponse (OpenRouter/cloud)
    5. Retour avec sources citées
    """
    permission_classes = [IsAuthenticated]  # Ou AllowAny selon ton auth
    
    @swagger_auto_schema(
        request_body=QuestionSerializer,
        responses={
            200: RAGResponseSerializer,
            400: "Requête invalide",
            503: "Service IA temporairement indisponible",
            500: "Erreur serveur"
        },
        operation_description="""
            Pose une question sur vos documents. 
            Le système recherche automatiquement les passages pertinents 
            et génère une réponse contextualisée.
        """
    )
    def post(self, request, *args, **kwargs):
        """
        Handler POST pour la requête RAG.
        """
        # Validation
        serializer = QuestionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Données invalides", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        question: str = data["question"]
        document_ids: List[UUID] = data.get("document_ids", [])
        top_k: int = data.get("top_k", 5)
        temperature: float = data.get("temperature", 0.7)
        
        try:
            # Initialisation du routeur IA
            router = AIRouter()
            
            # === ÉTAPE 1: Vectorisation de la question (Local/Ollama) ===
            try:
                query_embedding = router.get_embedding(question)
                logger.info(f"Question vectorisée: {question[:50]}...")
            except OllamaError as e:
                logger.error(f"Ollama indisponible: {e}")
                return Response(
                    {
                        "error": "Service d'embedding local indisponible",
                        "message": str(e),
                        "solution": "Vérifiez qu'Ollama est démarré avec nomic-embed-text"
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # === ÉTAPE 2: Recherche vectorielle pgvector ===
            if document_ids:
                # Recherche ciblée sur documents spécifiques
                all_chunks = []
                for doc_id in document_ids:
                    chunks = DocumentChunk.search_similar(
                        query_embedding=query_embedding,
                        top_k=top_k,
                        document_id=doc_id
                    )
                    all_chunks.extend(chunks)
                
                # Re-tri par distance globale
                all_chunks.sort(key=lambda x: x.distance)
                relevant_chunks = all_chunks[:top_k]
            else:
                # Recherche globale
                relevant_chunks = DocumentChunk.search_similar(
                    query_embedding=query_embedding,
                    top_k=top_k
                )
            
            if not relevant_chunks:
                return Response(
                    {
                        "answer": "Aucun document pertinent trouvé pour répondre à cette question.",
                        "sources": [],
                        "context_used": False
                    },
                    status=status.HTTP_200_OK
                )
            
            # Préparation du contexte
            context_texts = []
            sources = []
            
            for chunk in relevant_chunks:
                context_texts.append(chunk.content)
                sources.append({
                    "document_id": str(chunk.document_id),
                    "document_title": chunk.document.title,
                    "chunk_index": chunk.chunk_index,
                    "page": chunk.page_number,
                    "distance": round(float(chunk.distance), 4),
                    "excerpt": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
                })
            
            # === ÉTAPE 3: Génération LLM (Cloud/OpenRouter) ===
            try:
                chat_response = router.rag_query(
                    question=question,
                    context_chunks=context_texts,
                    temperature=temperature,
                    max_tokens=2048
                )
                
                answer = chat_response.content
                
                # Log usage pour monitoring
                if chat_response.usage:
                    logger.info(
                        f"OpenRouter usage: {chat_response.usage.get('prompt_tokens', 0)} prompt, "
                        f"{chat_response.usage.get('completion_tokens', 0)} completion tokens"
                    )
                
            except OpenRouterError as e:
                logger.error(f"Erreur OpenRouter: {e}")
                return Response(
                    {
                        "error": "Service LLM cloud indisponible",
                        "message": str(e),
                        "fallback": "Veuillez réessayer dans quelques instants"
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # Nettoyage
            router.close()
            
            # === Réponse finale ===
            response_data = {
                "answer": answer,
                "sources": sources,
                "meta": {
                    "model_used": chat_response.model,
                    "finish_reason": chat_response.finish_reason,
                    "chunks_retrieved": len(relevant_chunks),
                    "temperature": temperature
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception("Erreur inattendue RAG")
            return Response(
                {
                    "error": "Erreur interne lors du traitement",
                    "message": str(e) if settings.DEBUG else "Contactez l'administrateur"
                },
                status=status.HTTP_500_INTERNAL_ERROR
            )
    
    def get(self, request):
        """
        Health check du service RAG.
        """
        health_status = {}
        
        # Check Ollama
        try:
            router = AIRouter()
            health_status["ollama"] = {
                "status": "up" if router.check_ollama_status() else "down",
                "model": "nomic-embed-text"
            }
        except Exception as e:
            health_status["ollama"] = {"status": "down", "error": str(e)}
        
        # Check OpenRouter (via simple auth check)
        try:
            # On ne fait pas d'appel réel pour ne pas consommer de crédits
            health_status["openrouter"] = {
                "status": "configured",
                "api_key_present": bool(settings.OPENROUTER_API_KEY)
            }
        except Exception as e:
            health_status["openrouter"] = {"status": "error", "error": str(e)}
        
        all_healthy = (
            health_status.get("ollama", {}).get("status") == "up" and
            health_status.get("openrouter", {}).get("status") == "configured"
        )
        
        return Response(
            {
                "status": "healthy" if all_healthy else "degraded",
                "services": health_status
            },
            status=status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        )
```

---

## 🔧 Fichiers Complémentaires Essentiels

### `apps/chat/serializers.py`

```python
from rest_framework import serializers


class QuestionSerializer(serializers.Serializer):
    question = serializers.CharField(
        required=True, 
        min_length=3, 
        max_length=2000,
        help_text="Question à poser sur les documents"
    )
    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="IDs des documents à interroger (optionnel, sinon global)"
    )
    top_k = serializers.IntegerField(
        required=False, 
        default=5, 
        min_value=1, 
        max_value=20,
        help_text="Nombre de passages à récupérer"
    )
    temperature = serializers.FloatField(
        required=False,
        default=0.7,
        min_value=0.0,
        max_value=1.0,
        help_text="Créativité de la réponse (0=précis, 1=creatif)"
    )


class SourceSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
    document_title = serializers.CharField()
    chunk_index = serializers.IntegerField()
    page = serializers.IntegerField(allow_null=True)
    distance = serializers.FloatField()
    excerpt = serializers.CharField()


class RAGResponseSerializer(serializers.Serializer):
    answer = serializers.CharField(help_text="Réponse générée par le LLM")
    sources = SourceSerializer(many=True)
    meta = serializers.DictField(help_text="Métadonnées de la requête")
```

### Configuration Celery (`celery_app.py`)

```python
import os
from celery import Celery
from celery.signals import worker_ready

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')

app = Celery('smart_notebook')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


@worker_ready.connect
def at_start(sender, **k):
    print("Celery worker prêt - Smart Notebook")
```

### `requirements/base.txt`

```txt
# Django & DRF
Django>=5.0,<5.1
djangorestframework>=3.14.0
django-cors-headers>=4.3.0
drf-yasg>=1.21.0  # Swagger

# Base de données
psycopg[binary]>=3.1.0
pgvector>=0.2.0
django-pgvector>=0.1.0

# Asynchrone & Tâches
celery[redis]>=5.3.0
redis>=5.0.0

# IA & HTTP
httpx>=0.25.0
openai>=1.0.0  # Fallback optionnel
tenacity>=8.2.0  # Retry logic

# Documents & OCR
pikepdf>=8.0.0
PyMuPDF>=1.23.0  # fitz
pdf2image>=1.16.0
pytesseract>=0.3.10
Pillow>=10.0.0

# Audio TTS
edge-tts>=6.1.0

# Utilitaires
python-magic>=0.4.27
python-dotenv>=1.0.0
pydantic>=2.0.0
```

---

## 🚀 Instructions de Démarrage (Debian 12)

```bash
# 1. Infrastructure Docker
docker run -d \
  --name smart-notebook-db \
  -e POSTGRES_PASSWORD=smart_password \
  -e POSTGRES_USER=smart_user \
  -e POSTGRES_DB=smart_notebook \
  -p 5432:5432 \
  ankane/pgvector:latest

docker run -d --name redis-smart -p 6379:6379 redis:7-alpine

# 2. Ollama (local)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull nomic-embed-text
ollama serve  # En arrière-plan

# 3. Configuration environnement
export OPENROUTER_API_KEY="sk-or-v1-..."
export DATABASE_URL="postgres://smart_user:smart_password@localhost:5432/smart_notebook"
export CELERY_BROKER_URL="redis://localhost:6379/0"

# 4. Django
python manage.py migrate
python manage.py runserver

# 5. Celery Worker (terminal séparé)
celery -A config worker -l info -Q documents,chat,audio
```

Cette architecture respecte tes contraintes : **Ollama léger pour l'embeddings local** (nomic-embed-text tourne bien sur CPU), **OpenRouter pour le LLM puissant** (pas de charge GPU), et **edge-tts pour l'audio sans GPU**. La recherche vectorielle utilise l'index HNSW de pgvector pour des performances optimales même avec de gros volumes.