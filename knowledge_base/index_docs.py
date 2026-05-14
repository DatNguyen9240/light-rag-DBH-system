import os
import json
import asyncio
import hashlib
from openai import AsyncOpenAI
from lightrag import LightRAG
from lightrag.utils import EmbeddingFunc

# Import centralized config
from config import (
    PG_URL, WORKSPACE_NAME, OPENROUTER_API_KEY, 
    DOCS_DIR, MAPPINGS_FILE, STORAGE_DIR
)

# Initialize Client
client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

async def dummy_llm(prompt, system_prompt=None, history_messages=[], **kwargs):
    return "" # No LLM needed for pure indexing

async def embedding_func(texts):
    try:
        response = await client.embeddings.create(
            model="openai/text-embedding-3-small",
            input=texts
        )
        import numpy as np
        return np.array([data.embedding for data in response.data])
    except Exception as e:
        print(f"[INDEX] Embedding Error: {e}")
        raise e

async def main():
    print(f"[INDEX] Starting Indexing for Workspace: [{WORKSPACE_NAME}]")
    
    # 1. Clean old local tracking
    import shutil
    if os.path.exists(STORAGE_DIR):
        shutil.rmtree(STORAGE_DIR)
    os.makedirs(STORAGE_DIR, exist_ok=True)

    # 2. Load mappings
    if not os.path.exists(MAPPINGS_FILE):
        print("No mappings found. Exiting.")
        return

    with open(MAPPINGS_FILE, 'r', encoding='utf-8') as f:
        rbac_map = json.load(f)

    # 3. Initialize Global RAG
    rag = LightRAG(
        workspace=WORKSPACE_NAME,
        working_dir=STORAGE_DIR,
        kv_storage="PGKVStorage",
        doc_status_storage="PGDocStatusStorage",
        vector_storage="PGVectorStorage",
        graph_storage="NetworkXStorage", # Reverted to local because Supabase lacks Apache AGE support
        addon_params={"postgresql_url": PG_URL},
        llm_model_func=dummy_llm,
        embedding_func=EmbeddingFunc(
            embedding_dim=1536,
            max_token_size=8192,
            func=embedding_func
        )
    )
    await rag.initialize_storages()

    # 4. Process documents
    # To keep RBAC simple in a single workspace, we tag content with roles.
    # If a document has 2 roles, we insert it twice with different role tags.
    # This ensures high retrieval relevance for the specific role prefix.
    
    for filename, roles in rbac_map.items():
        file_path = os.path.join(DOCS_DIR, filename)
        if not os.path.exists(file_path): continue

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Optimized: Combine all roles into a single header to save time and API costs
        role_header = "[" + ", ".join([r.upper() for r in roles]) + "]"
        print(f"[INDEX] Inserting [{filename}] for Roles: {role_header}...")
        
        tagged_content = f"{role_header}\n{content}"
        
        try:
            await rag.ainsert(tagged_content, doc_id=filename)
        except Exception as e:
            print(f"Error inserting {filename}: {e}")

    print("[INDEX] All documents indexed efficiently in shared workspace.")

if __name__ == "__main__":
    asyncio.run(main())
