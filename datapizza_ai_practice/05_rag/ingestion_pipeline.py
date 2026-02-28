"""Document ingestion: parse PDFs, split, embed, and store in Qdrant.

Usage: python 05_rag/ingestion_pipeline.py
Requires: COHERE_API_KEY, COHERE_ENDPOINT in .env; Qdrant running locally
"""
import os

from datapizza.core import embedder
from datapizza.core.vectorstore import VectorConfig
from datapizza.embedders import ChunkEmbedder
from datapizza.embedders.cohere import CohereEmbedder
from datapizza.modules.parsers.docling import DoclingParser
from datapizza.modules.splitters import RecursiveSplitter
from datapizza.pipeline.pipeline import IngestionPipeline
from datapizza.vectorstores.qdrant import QdrantVectorstore
from dotenv import load_dotenv
from openai import vector_stores

load_dotenv()

parser = DoclingParser()
splitter = RecursiveSplitter(max_char=2000, overlap=100)
embedder = ChunkEmbedder(
    client=CohereEmbedder(
        api_key=os.getenv("COHERE_API_KEY"),
        base_url=os.getenv("COHERE_ENDPOINT"),
        model_name="embed-v4.0",
        input_type="search_documents",
    ),
    embedding_name="embedding_vector"
)

vector_store = QdrantVectorstore(host="localhost", port=6333)
vector_store.create_collection(
    collection_name="hackapizza_ingestion",
    vector_config=[VectorConfig(
        dimensions=1536,
        name="embedding_vector"
    )],
)

pipeline = IngestionPipeline(
    modules=[parser, splitter, embedder],
    vector_store=vector_store,
    collection_name="hackapizza_ingestion",
)

pipeline.run(file_path="hackapizza_dataset/Codice Galattico/Codice Galattico.pdf")
