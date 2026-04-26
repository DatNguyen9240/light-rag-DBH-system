import os, asyncio
os.environ['POSTGRES_URL'] = 'postgresql://postgres.dqdijzzdwscoivvqhspc:Datnguyenthanh1234@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres'
from lightrag import LightRAG
from lightrag.utils import EmbeddingFunc

async def embed_func(texts):
    return [[0.0]*1536 for _ in texts] # Dummy embeddings to bypass API completely

async def test():
    rag = LightRAG(
        workspace='./test_workspace',
        embedding_func=EmbeddingFunc(embedding_dim=1536, max_token_size=8192, func=embed_func),
        kv_storage='PGKVStorage', doc_status_storage='PGKVStorage', vector_storage='PGVectorStorage', graph_storage='NetworkXStorage'
    )
    await rag.initialize_storages()
    try:
        await rag.ainsert("This is a test document.")
    except Exception as e:
        print('ERROR:', e)
asyncio.run(test())
