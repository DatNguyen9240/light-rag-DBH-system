import asyncio
import asyncpg
from config import PG_URL

async def inspect_schema():
    conn = await asyncpg.connect(PG_URL)
    
    # Get all tables and their columns
    query = """
    SELECT 
        table_name, 
        column_name, 
        data_type 
    FROM 
        information_schema.columns 
    WHERE 
        table_schema = 'public' 
        AND table_name ILIKE 'lightrag_%'
    ORDER BY 
        table_name, ordinal_position;
    """
    
    rows = await conn.fetch(query)
    
    tables = {}
    for row in rows:
        t_name = row['table_name']
        if t_name not in tables:
            tables[t_name] = []
        tables[t_name].append(f"{row['column_name']} ({row['data_type']})")
    
    print("\n--- DETAILED SUPABASE SCHEMA (LightRAG) ---")
    for t_name, cols in tables.items():
        print(f"\nTable: {t_name}")
        for col in cols:
            print(f"  - {col}")
            
    await conn.close()

if __name__ == "__main__":
    asyncio.run(inspect_schema())
