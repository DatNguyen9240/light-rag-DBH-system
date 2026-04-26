import asyncio
import asyncpg

async def clear_tables():
    PG_URL = 'postgresql://postgres.dqdijzzdwscoivvqhspc:Datnguyenthanh1234@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres'
    conn = await asyncpg.connect(PG_URL)
    query = chr(68)+chr(79)+chr(32)+chr(36)+chr(36)+""" DECLARE
        r RECORD;
    BEGIN
        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema() AND tablename ILIKE 'lightrag_%') LOOP
            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
        END LOOP;
    END """+chr(36)+chr(36)+chr(59)
    await conn.execute(query)
    await conn.close()
    print('All LightRAG tables dropped successfully.')

asyncio.run(clear_tables())
