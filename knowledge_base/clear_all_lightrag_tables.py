import asyncio
import asyncpg
import os
from config import PG_URL

async def clear_all_tables():
    print(f"Connecting to Supabase to wipe all LightRAG tables...")
    conn = await asyncpg.connect(PG_URL)
    
    # SQL to find and drop all tables starting with 'lightrag_'
    drop_query = """
    DO $$ DECLARE
        r RECORD;
    BEGIN
        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema() AND tablename ILIKE 'lightrag_%') LOOP
            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
        END LOOP;
    END $$;
    """
    
    try:
        await conn.execute(drop_query)
        print("✅ ALL LightRAG tables have been dropped successfully.")
        print("Now you can run 'python index_docs.py' to rebuild with only 11 tables.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(clear_all_tables())
