import os
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from openai import AsyncOpenAI
from lightrag import LightRAG
from lightrag.utils import EmbeddingFunc
from lightrag.base import QueryParam

# Import centralized config
from config import (
    PG_URL, WORKSPACE_NAME, RAG_PORT, OPENROUTER_API_KEY, 
    DOCS_DIR, MAPPINGS_FILE, STORAGE_DIR
)

app = FastAPI(title="LightRAG DBH Server (Clean & Optimized)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLM Client
client = AsyncOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

async def llm_complete_func(prompt, system_prompt=None, history_messages=[], **kwargs):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=kwargs.get("temperature", 0),
    )
    return response.choices[0].message.content

async def embedding_func(texts):
    try:
        response = await client.embeddings.create(
            model="openai/text-embedding-3-small",
            input=texts
        )
        import numpy as np
        return np.array([data.embedding for data in response.data])
    except Exception as e:
        print(f"Embedding API Error: {e}")
        raise e

# --- INITIALIZE SINGLE GLOBAL RAG INSTANCE ---
# This reduces Supabase tables from 44+ down to just 11.
os.makedirs(STORAGE_DIR, exist_ok=True)
global_rag = LightRAG(
    workspace=WORKSPACE_NAME,
    working_dir=STORAGE_DIR,
    kv_storage="PGKVStorage",
    doc_status_storage="PGDocStatusStorage",
    vector_storage="PGVectorStorage",
    graph_storage="NetworkXStorage", # Reverted to local because Supabase lacks Apache AGE support
    addon_params={"postgresql_url": PG_URL},
    llm_model_func=llm_complete_func,
    embedding_func=EmbeddingFunc(
        embedding_dim=1536,
        max_token_size=8192,
        func=embedding_func
    )
)

# --- MODELS ---
class QueryRequest(BaseModel):
    query: str
    mode: str = "naive"
    namespace: str = "patient" # The Role (Admin/Patient/Doctor/Staff)

class DocumentPayload(BaseModel):
    filename: str
    content: str
    roles: List[str]

# --- ENDPOINTS ---
@app.on_event("startup")
async def startup_event():
    print(f"Initializing Shared LightRAG Workspace: [{WORKSPACE_NAME}]...")
    await global_rag.initialize_storages()
    print("LightRAG Storage Initialized successfully.")

@app.post("/query")
async def query_rag(request: QueryRequest):
    try:
        # Use 'naive' for speed or 'hybrid' for better quality
        query_param = QueryParam(mode=request.mode)
        
        # Security: Prefix query with the role to guide the RAG to relevant chunks
        role_prefix = request.namespace.upper()
        namespaced_query = f"[{role_prefix}] {request.query}"
        
        print(f"Querying RAG (role={role_prefix}): {request.query}")
        response = await global_rag.aquery(namespaced_query, param=query_param)
        
        return {"response": response, "answer": response}
    except Exception as e:
        print(f"Query Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/kb/documents")
def get_documents():
    if not os.path.exists(MAPPINGS_FILE): return []
    with open(MAPPINGS_FILE, 'r', encoding='utf-8') as f:
        rbac_map = json.load(f)

    docs_list = []
    for filename, roles in rbac_map.items():
        file_path = os.path.join(DOCS_DIR, filename)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as cf:
                content = cf.read()
            docs_list.append({
                "filename": filename,
                "roles": roles,
                "sizeBytes": os.path.getsize(file_path),
                "content": content
            })
    return docs_list

@app.post("/api/kb/documents")
def save_document(payload: DocumentPayload):
    os.makedirs(DOCS_DIR, exist_ok=True)
    filename = payload.filename if payload.filename.endswith(".md") else f"{payload.filename}.md"
    file_path = os.path.join(DOCS_DIR, filename)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(payload.content)

    rbac_map = {}
    if os.path.exists(MAPPINGS_FILE):
        with open(MAPPINGS_FILE, 'r', encoding='utf-8') as f:
            rbac_map = json.load(f)
    rbac_map[filename] = payload.roles
    with open(MAPPINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(rbac_map, f, ensure_ascii=False, indent=2)

    return {"message": "Document saved successfully", "filename": filename}

@app.delete("/api/kb/documents/{filename}")
def delete_document(filename: str):
    file_path = os.path.join(DOCS_DIR, filename)
    if os.path.exists(file_path): os.remove(file_path)
    if os.path.exists(MAPPINGS_FILE):
        with open(MAPPINGS_FILE, 'r', encoding='utf-8') as f:
            rbac_map = json.load(f)
        if filename in rbac_map:
            del rbac_map[filename]
            with open(MAPPINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(rbac_map, f, ensure_ascii=False, indent=2)
    return {"message": "Document deleted successfully"}

@app.post("/api/kb/reindex")
async def trigger_reindex():
    import subprocess
    import time
    start_time = time.time()
    try:
        # Run indexing script as a separate process
        process = await asyncio.create_subprocess_exec(
            "python", os.path.join(os.path.dirname(__file__), "index_docs.py"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise Exception(stderr.decode())

        # Reset global instance to clear in-memory caches
        await global_rag.initialize_storages()
        
        elapsed = time.time() - start_time
        return {"message": f"Reindex complete in {elapsed:.1f}s", "time_taken": elapsed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=RAG_PORT)
