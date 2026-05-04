import os
import json
import asyncio
import shutil

# --- SUPABASE CONFIGURATION ---
SUPABASE_PASSWORD = os.environ.get("SUPABASE_PASSWORD", "Datnguyenthanh1234")
PG_URL = f"postgresql://postgres.dqdijzzdwscoivvqhspc:{SUPABASE_PASSWORD}@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"

os.environ["POSTGRES_URL"] = PG_URL
os.environ["POSTGRES_URI"] = PG_URL
os.environ["POSTGRES_USER"] = "postgres.dqdijzzdwscoivvqhspc"
os.environ["POSTGRES_PASSWORD"] = SUPABASE_PASSWORD
os.environ["POSTGRES_DATABASE"] = "postgres"
os.environ["POSTGRES_HOST"] = "aws-1-ap-southeast-1.pooler.supabase.com"
os.environ["POSTGRES_PORT"] = "5432"

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from openai import AsyncOpenAI
from lightrag import LightRAG
from lightrag.utils import EmbeddingFunc
from lightrag.base import QueryParam


app = FastAPI(title="LightRAG DBH Server (Supabase Cloud Edition)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLM Client
client = AsyncOpenAI(
    api_key=os.environ.get("OPENAI_API_KEY", os.environ.get("OPENROUTER_API_KEY", "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")),
    base_url="https://openrouter.ai/api/v1"
)

async def custom_llm_complete(prompt, system_prompt=None, history_messages=[], **kwargs):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    allowed_params = ["temperature", "top_p", "n", "stream", "stop", "max_tokens",
                      "presence_penalty", "frequency_penalty", "logit_bias", "user"]
    openai_kwargs = {k: v for k, v in kwargs.items() if k in allowed_params}

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        **openai_kwargs
    )
    return response.choices[0].message.content

# Initialize API Embedding Model
async def embed_func(texts):
    # Call OpenRouter embeddings endpoint for ultra-fast API embedding
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

# ── INITIALIZE SEPARATE RAG INSTANCES DYNAMICALLY ────────────────────
rags = {}
base_dir = '/app/knowledge_base'
docs_dir = os.path.join(base_dir, 'docs')
mappings_file = os.path.join(base_dir, 'rbac_mappings.json')

def load_rags_dynamic():
    if not os.path.exists(base_dir):
        return
    for item in os.listdir(base_dir):
        full_path = os.path.join(base_dir, item)
        if os.path.isdir(full_path) and item.startswith('rag_storage_'):
            role = item.split('rag_storage_')[1]
            print(f"Loading dynamic role (Supabase): {role}")
            rags[role] = LightRAG(
                workspace=f"rag_{role}",       # Force prefix to map to Postgres tables
                working_dir=full_path,
                kv_storage="PGKVStorage",
                doc_status_storage="PGDocStatusStorage",
                vector_storage="PGVectorStorage",
                graph_storage="NetworkXStorage",
                addon_params={"postgresql_url": PG_URL},
                llm_model_func=custom_llm_complete,
                embedding_func=EmbeddingFunc(
                    embedding_dim=1536,
                    max_token_size=8192,
                    func=embed_func
                )
            )

load_rags_dynamic()

# ── API MODELS ────────────────────
class QueryRequest(BaseModel):
    query: str
    mode: str = "naive"   # naive = pure vector search, fastest for Q&A docs
    namespace: str = None

class DocumentPayload(BaseModel):
    filename: str
    content: str
    roles: List[str]

# ── ENDPOINTS ────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    print(f"Initializing {len(rags)} Multi-tenant LightRAG Storages ({list(rags.keys())})...")
    for role_name, rag_instance in rags.items():
        await rag_instance.initialize_storages()
    print("All LightRAG Storages Initialized")

@app.post("/query")
async def query_rag(request: QueryRequest):
    try:
        # FORCE NAIVE MODE: N8N still passes 'mode=hybrid', but hybrid fails
        # because full entity creation takes too long via OpenRouter LLM.
        # Naive mode (pure vector search) works instantly and reliably.
        forced_mode = "naive"
        query_param = QueryParam(mode=forced_mode)
        ns = request.namespace.lower() if request.namespace else 'patient'

        if ns in rags:
            print(f"[{ns.upper()}] Querying RAG {ns.upper()} (mode={request.mode}) with: {request.query}")
            # Namespace prefix busts cross-namespace LLM cache pollution
            namespaced_query = f"[{ns}] {request.query}"
            response = await rags[ns].aquery(namespaced_query, param=query_param)
        else:
            print(f"[MISSING NAMESPACE {ns.upper()}] No knowledge base found for this role.")
            return {"response": "Hệ thống chưa có cơ sở dữ liệu tri thức cho phân quyền của bạn.", "answer": "Hệ thống chưa có cơ sở dữ liệu tri thức cho phân quyền của bạn."}
        return {"response": response, "answer": response}
    except Exception as e:
        print(f"ERROR: Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ── KNOWLEDGE MANAGEMENT ENDPOINTS ────────────────────
@app.get("/api/kb/documents")
def get_documents():
    """List all documents and their roles"""
    if not os.path.exists(mappings_file):
        return []

    with open(mappings_file, 'r', encoding='utf-8') as f:
        rbac_map = json.load(f)

    docs_list = []
    for filename, roles in rbac_map.items():
        file_path = os.path.join(docs_dir, filename)
        content = ""
        size = 0
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            with open(file_path, 'r', encoding='utf-8') as cf:
                content = cf.read()

        docs_list.append({
            "filename": filename,
            "roles": roles,
            "sizeBytes": size,
            "content": content
        })
    return docs_list

@app.post("/api/kb/documents")
def save_document(payload: DocumentPayload):
    """Create or update a document and its role mappings"""
    os.makedirs(docs_dir, exist_ok=True)

    # Save content to .md file
    filename = payload.filename
    if not filename.endswith(".md"):
        filename += ".md"
    file_path = os.path.join(docs_dir, filename)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(payload.content)

    # Update mappings
    rbac_map = {}
    if os.path.exists(mappings_file):
        with open(mappings_file, 'r', encoding='utf-8') as f:
            rbac_map = json.load(f)

    rbac_map[filename] = payload.roles

    with open(mappings_file, 'w', encoding='utf-8') as f:
        json.dump(rbac_map, f, ensure_ascii=False, indent=2)

    return {"message": "Đã lưu tài liệu thành công", "filename": filename}

@app.delete("/api/kb/documents/{filename}")
def delete_document(filename: str):
    """Delete a document and its role mapping"""
    file_path = os.path.join(docs_dir, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    if os.path.exists(mappings_file):
        with open(mappings_file, 'r', encoding='utf-8') as f:
            rbac_map = json.load(f)

        if filename in rbac_map:
            del rbac_map[filename]
            with open(mappings_file, 'w', encoding='utf-8') as f:
                json.dump(rbac_map, f, ensure_ascii=False, indent=2)

    return {"message": "Đã xóa tài liệu thành công"}

@app.post("/api/kb/reindex", status_code=200)
async def trigger_reindex():
    """Synchronous reindex using fast index_docs script — wipes old storage for clean slate"""
    import time
    import subprocess
    
    start_time = time.time()
    try:
        print("[REINDEX] Starting fast synchronous reindex via index_docs.py...")
        
        # Run script
        loop = asyncio.get_running_loop()
        process = await loop.run_in_executor(None, lambda: subprocess.run(["python", "/app/knowledge_base/index_docs.py"], capture_output=True, text=True))
        
        if process.returncode != 0:
            print(f"[REINDEX] Script Error: {process.stderr}")
            raise HTTPException(status_code=500, detail=f"Reindex thất bại: {process.stderr}")
            
        print(f"[REINDEX] Script success output loaded.")
        
        # Clear LightRAG shared in-memory state so old caches are wiped
        try:
            from lightrag.kg.shared_storage import global_kg_state
            global_kg_state.clear()
            print("[REINDEX] Emptied LightRAG shared_storage in-memory cache.")
        except Exception as e:
            print(f"[REINDEX] Note: shared_storage cache clear skipped/failed: {e}")
            
        # Re-initialize the dictionaries
        global rags
        rags.clear()
        load_rags_dynamic()
        
        for role_name, rag_instance in rags.items():
            await rag_instance.initialize_storages()
        
        print("[REINDEX] Complete! All documents indexed and ready to query.")
        
        elapsed_time = time.time() - start_time
        return {
            "message": f"✅ Hệ thống đã Reindex thành công ({elapsed_time:.1f}s)! Toàn bộ Chatbot đã cập nhật nội dung.",
            "time_taken": elapsed_time
        }
        
    except Exception as e:
        print(f"[REINDEX] Critical Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9621)
