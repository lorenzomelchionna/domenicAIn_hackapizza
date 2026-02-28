"""RAG query pipeline: embed a question, retrieve from Qdrant, generate an answer.

Loads the full DAG pipeline from rag_config.yaml.
Usage: python 05_rag/rag_pipeline.py
Requires: COHERE_API_KEY, COHERE_ENDPOINT, OPENAI_API_KEY in .env; Qdrant running
"""
import os

from datapizza.clients.openai import OpenAIClient
from datapizza.core.vectorstore import VectorConfig
from datapizza.embedders.cohere import CohereEmbedder
from datapizza.modules import prompt
from datapizza.modules.prompt import ChatPromptTemplate
from datapizza.pipeline import DagPipeline, dag_pipeline
from datapizza.vectorstores.qdrant import QdrantVectorstore
from dotenv import load_dotenv

load_dotenv()

# embedder = CohereEmbedder(
#     api_key=os.getenv("COHERE_API_KEY"),
#     base_url=os.getenv("COHERE_ENDPOINT"),
#     model_name="embed-v4.0",
#     input_type="query"
# )

# retriever = QdrantVectorstore(
#     host=os.getenv("QDRANT_HOST"),
#     port=os.getenv("QDRANT_PORT"),
#     #api_key=os.getenv("QDRANT_API_KEY")
# )
# retriever.create_collection(
#     collection_name="knowledge_base",
#     vector_config=[VectorConfig(dimensions=1536, name="vector")]
# )

# prompt_template = ChatPromptTemplate(
#     user_prompt_template="User question: {{user_prompt}}\n:",
#     retrieval_prompt_template="Retreived content:\n{% for chunk in chunks %}{{ chunk.text }}\n{% endfor %}"
# )

# client = OpenAIClient(
#     api_key=os.getenv("OPENAI_API_KEY"),
#     model="gpt-5.2",
# )

# dag_pipeline = DagPipeline()
# dag_pipeline.add_module("embedder", embedder)
# dag_pipeline.add_module("retriever", retriever)
# dag_pipeline.add_module("prompt", prompt_template)
# dag_pipeline.add_module("generator", client)

# dag_pipeline.connect("embedder", "retriever", target_key="query_vector")
# dag_pipeline.connect("retriever", "prompt", target_key="chunks")
# dag_pipeline.connect("prompt", "generator", target_key="memory")

dag_pipeline = DagPipeline().from_yaml("datapizza_ai_practice/05_rag/rag_config.yaml")

query = "Quali sono le tre principali categorie di individui protetti (ordini)?"
result = dag_pipeline.run(
    {
        "embedder": {"text": query},
        "prompt": {"user_prompt": query},
        "retriever": {"collection_name": "hackapizza_ingestion", "k": 5},
        "generator": {"input": query}
    }
)

print(f"Generated response: {result['generator']}")
