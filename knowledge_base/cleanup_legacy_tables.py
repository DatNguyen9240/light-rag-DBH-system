import asyncio
import asyncpg
from config import PG_URL

async def cleanup_legacy_tables():
    print(f"Connecting to Supabase to clean up legacy tables...")
    conn = await asyncpg.connect(PG_URL)
    
    # List of prefixes and names that are NO LONGER needed
    legacy_prefixes = [
        'patient_', 'admin_', 'doctor_', 'staff_', 
        'kv_', 'vdb_', 'doc_status', 'doc_chunks', 'doc_full',
        'llm_cache', 'full_entities', 'full_relations'
    ]
    
    # Get all tables in the public schema
    tables = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    
    tables_to_drop = []
    for row in tables:
        name = row['table_name'].lower()
        # Only drop if it matches legacy patterns AND is NOT one of our new LIGHTRAG_ tables
        if any(name.startswith(p) for p in legacy_prefixes) and not name.startswith('lightrag_'):
            tables_to_drop.append(row['table_name'])
            
    if not tables_to_drop:
        print("No legacy tables found. Your database is already clean!")
    else:
        print(f"Found {len(tables_to_drop)} legacy tables to remove.")
        for table in tables_to_drop:
            print(f"  - Dropping {table}...")
            await conn.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
        print("\nCleanup completed successfully!")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(cleanup_legacy_tables())
