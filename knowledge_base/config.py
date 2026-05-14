import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# --- DB CONFIG ---
SUPABASE_PROJECT_ID = os.getenv("SUPABASE_PROJECT_ID", "dqdijzzdwscoivvqhspc")
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD", "Datnguyenthanh1234")
# Use PG_URL directly if provided in .env, otherwise construct it
PG_URL = os.getenv("PG_URL", f"postgresql://postgres.{SUPABASE_PROJECT_ID}:{SUPABASE_PASSWORD}@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres")

# --- RAG CONFIG ---
# Use a SINGLE workspace to reduce tables from 44 down to 11
WORKSPACE_NAME = os.getenv("WORKSPACE_NAME", "dbh_ehr_global")
RAG_PORT = int(os.getenv("RAG_PORT", 9621))

# --- API KEYS ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, 'docs')
MAPPINGS_FILE = os.path.join(BASE_DIR, 'rbac_mappings.json')
STORAGE_DIR = os.path.join(BASE_DIR, f'rag_storage_{WORKSPACE_NAME}')

# Environment setup for LightRAG
os.environ["POSTGRES_URL"] = PG_URL
os.environ["POSTGRES_URI"] = PG_URL
os.environ["POSTGRES_USER"] = f"postgres.{SUPABASE_PROJECT_ID}"
os.environ["POSTGRES_PASSWORD"] = SUPABASE_PASSWORD
os.environ["POSTGRES_DATABASE"] = "postgres"
os.environ["POSTGRES_HOST"] = "aws-1-ap-southeast-1.pooler.supabase.com"
os.environ["POSTGRES_PORT"] = "5432"
