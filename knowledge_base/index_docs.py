import os

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
import json
import asyncio
import shutil
import hashlib
import uuid
import collections
from openai import AsyncOpenAI
from lightrag import LightRAG
from lightrag.utils import EmbeddingFunc

# --- SUPABASE CONFIGURATION ---


API_KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
if not API_KEY:
    raise ValueError("Missing OPENAI_API_KEY or OPENROUTER_API_KEY in environment variables.")

client = AsyncOpenAI(
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

async def dummy_llm(prompt, system_prompt=None, history_messages=[], **kwargs):
    return ""

async def embed_func(texts):
    try:
        response = await client.embeddings.create(
            model="openai/text-embedding-3-small",
            input=texts
        )
        import numpy as np
        return np.array([data.embedding for data in response.data])
    except Exception as e:
        print(f"[INDEX] Embedding API Error: {e}")
        raise e

async def main():
    print("[INDEX] Starting fast embedding (OpenRouter API + SUPABASE POSTGRES)...")

    # --- WIPE STAGE: FORCE CLEAN SLATE ---
    print("[INDEX] Wiping existing vector databases to enforce strict RBAC syncing...")
    try:
        import asyncpg
        conn = await asyncpg.connect(os.environ.get("POSTGRES_URL"))
        # Drop all tables starting with lightrag_
        await conn.execute('''
        DO $$ DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema() AND tablename ILIKE 'lightrag_%') LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
        END $$;
        ''')
        await conn.close()
        print("[INDEX] Cloud Supabase Tables Dropped.")
    except Exception as e:
        print(f"[INDEX] Note: Table drop skipped/failed: {e}")

    # Remove local tracking folders
    # Support both Docker (/app/knowledge_base) and local execution
    base_dir = os.path.dirname(os.path.abspath(__file__))
    import glob
    for p in glob.glob(os.path.join(base_dir, 'rag_storage_*')):
        try:
            if os.path.isfile(p):
                os.remove(p)
            elif os.path.isdir(p):
                shutil.rmtree(p)
        except: pass
    print("[INDEX] Local hashes wiped.")
    
    docs_dir = os.path.join(base_dir, 'docs')
    mappings_file = os.path.join(base_dir, 'rbac_mappings.json')

    if not os.path.exists(mappings_file):
        print(f"[INDEX] ERROR: {mappings_file} not found!")
        return

    with open(mappings_file, 'r', encoding='utf-8') as mf:
        rbac_map = json.load(mf)

    all_roles = set()
    for roles in rbac_map.values():
        all_roles.update(roles)

    print(f"[INDEX] Building vector stores for {len(all_roles)} roles: {list(all_roles)} on Supabase.")

    async def process_role(role):
        print(f"[INDEX] Processing Role: {role.upper()}")
        storage_dir = os.path.join(base_dir, f'rag_storage_{role}')
        hash_file = os.path.join(base_dir, f'rag_storage_{role}_hash_supabase.txt')
        
        m = hashlib.md5()
        files_for_role = [f for f, roles in rbac_map.items() if role in roles]
        files_for_role.sort()
        for filename in files_for_role:
            file_path = os.path.join(docs_dir, filename)
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    m.update(filename.encode('utf-8'))
                    m.update(f.read())
        current_hash = m.hexdigest()
        
        # Note: Local storage_dir is kept just for the hash trackers and basic local state.
        # But Vector, KV, Graph are now isolated per Workspace prefix in Postgres.
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)
            
        with open(hash_file, 'w', encoding='utf-8') as f:
            f.write(current_hash)
        
        # LIGHTRAG POSTGRESQL INITIALIZATION
        rag = LightRAG(
            workspace=f"rag_{role}",
            working_dir=storage_dir,
            kv_storage="PGKVStorage",
            doc_status_storage="PGDocStatusStorage",
            vector_storage="PGVectorStorage",
            graph_storage="NetworkXStorage",
            addon_params={"postgresql_url": PG_URL},
            llm_model_func=dummy_llm,
            embedding_func=EmbeddingFunc(
                embedding_dim=1536,
                max_token_size=8192,
                func=embed_func
            )
        )
        await rag.initialize_storages()
        
        # In this Supabase mode, since we don't automatically DROP tables, LightRAG dedups inserts automatically.
        for filename, roles_allowed in rbac_map.items():
            if role in roles_allowed:
                file_path = os.path.join(docs_dir, filename)
                if not os.path.exists(file_path):
                    continue

                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                print(f"[INDEX] Embedding [{filename}] -> DB:[{role.upper()}] (Supabase Cloud)...")
                try:
                    role_specific_content = f"[{role.upper()}]\n{content}"
                    await rag.ainsert(role_specific_content)
                except Exception as e:
                    print(f"[INDEX] Skipped [{filename}] for [{role.upper()}]: {e}")
                    
        await asyncio.sleep(2)

    # Process roles sequentially to prevent Supabase connection pool exhaustion
    for role in all_roles:
        await process_role(role)
    print("[INDEX] Done! All vector databases ready on Supabase Cloud.")
    os._exit(0)

if __name__ == "__main__":
    asyncio.run(main())
