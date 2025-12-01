import os
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

# --- CONFIGURATION ---
MD_PATH = "/Users/satya/Desktop/pythonProjects/aiagent/CS_multi_agent/memory/support_playbook.md"
COLLECTION_NAME = "support_playbook"
QDRANT_URL = "http://localhost:6333"

# 1. Load the Markdown File
print(f"Loading {MD_PATH}...")
with open(MD_PATH, "r", encoding="utf-8") as f:
    markdown_text = f.read()

# 2. Configure the Header Splitter
headers_to_split_on = [
    ("##", "Section_Title"),
]

markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on,
    strip_headers=False
)

# 3. Create Chunks
chunks = markdown_splitter.split_text(markdown_text)

print(f"Generated {len(chunks)} chunks.")

print("\n--- SAMPLE CHUNK ---")
print(f"Content:\n{chunks[0].page_content[:150]}...")
print(f"Metadata:\n{chunks[0].metadata}")
print("--------------------\n")

# 4. Initialize Qdrant Client & Embeddings
client = QdrantClient(url="http://localhost:6333")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small", api_key="sk-p")

# 5. Check/Create Collection
if not client.collection_exists(COLLECTION_NAME):
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )
    print(f"Created collection '{COLLECTION_NAME}'")

# 6. Index the Documents
print("Indexing chunks into Qdrant...")
vector_store = QdrantVectorStore(
    client=client,
    collection_name=COLLECTION_NAME,
    embedding=embeddings,
)

vector_store.add_documents(documents=chunks)
print("Ingestion Complete!")