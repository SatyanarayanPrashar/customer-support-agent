from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from typing import Dict,  Any

from utils.logger import get_logger
logger = get_logger()

class RAGRetriever:
    def __init__(self, config: Dict[str, Any]):
        self.qdrant_url = config['vector_store']['url']
        self.collection_name = config['vector_store']['collection_name']
        self.api_key: str = config['api_keys']['openai_api']
        self.embedding_model: str = config['embedder']['model']

        self.retriever = self._init_client()

    def _init_client(self):
        client = QdrantClient(url=self.qdrant_url)
        embeddings = OpenAIEmbeddings(model=self.embedding_model, api_key=self.api_key)

        vector_store = QdrantVectorStore(
            client=client,
            collection_name=self.collection_name,
            embedding=embeddings,
        )

        return vector_store.as_retriever(search_kwargs={'k': 1})

    def extract(self, query):
        context = ""
        logger.info(f"(RAGRetriever) - Retrieving context for query: {query}")
        # for query in queries:
        docs = self.retriever.invoke(query)

        for i, doc in enumerate(docs):
            context += doc.page_content + "\n"
        
        return context

# if __name__ == "__main__":
#     test_queries = [
#         "what are the accepted payment methods"
#         # "refund policy for damaged goods",
#     ]
#     context = retrieve_policy(test_queries)

#     print("Aggregated Context: ", context["context"])