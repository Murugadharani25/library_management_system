import json
import os
from pathlib import Path
from bson import json_util
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path if env_path.exists() else None)

mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
mongo_db_name = os.getenv("MONGO_DB", "library_management")

client = MongoClient(mongo_uri)
db = client[mongo_db_name]

# Output paths
root_dir = Path(__file__).resolve().parents[1]
export_dir = root_dir / "database_export"
export_dir.mkdir(parents=True, exist_ok=True)
full_export_path = root_dir / "database_export.json"

all_data = {}
summary = {}

print(f"Exporting database '{mongo_db_name}' from {mongo_uri}...")

for col_name in sorted(db.list_collection_names()):
    docs = list(db[col_name].find())
    json_docs = json.loads(json_util.dumps(docs, indent=2))
    all_data[col_name] = json_docs
    summary[col_name] = len(json_docs)
    
    # Save individual collection JSON
    col_file = export_dir / f"{col_name}.json"
    with open(col_file, "w", encoding="utf-8") as f:
        json.dump(json_docs, f, indent=2, ensure_ascii=False)

# Save combined export
with open(full_export_path, "w", encoding="utf-8") as f:
    json.dump(all_data, f, indent=2, ensure_ascii=False)

print("Export completed successfully!")
print("Summary of exported collections:")
for col, count in summary.items():
    print(f"  - {col}: {count} records")
print(f"\nAll-in-one file: {full_export_path}")
print(f"Per-collection directory: {export_dir}")
