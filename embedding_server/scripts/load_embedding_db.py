"""Script to refresh embeddings.json with new data from sentences.txt."""
import asyncio
import logging
from pathlib import Path
import sys
import os

# Fix the path issue
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

# Now import from the correct location
os.chdir(project_root)
from embedding_server.src.embedding_server.gibson.database import AsyncEmbeddingDatabase
from embedding_server.src.embedding_server.gibson.embedding import AsyncEmbeddingService

logger = logging.getLogger(__name__)

root_path = Path(__file__).parent.parent
embedding_database_file = root_path / "src" / "data" / "embeddings.json"

# Remove existing embeddings file
embedding_database_file.unlink(missing_ok=True)
print(f"Removed existing embeddings.json at {embedding_database_file}")

async def process_data(text, embedding_service, database):
    print(f"Processing: {text[:50]}...")
    embedding = await embedding_service.embed(text=text)
    await database.insert(text=text, embeddings=embedding)

async def main():
    print("Starting to refresh embeddings...")
    
    embedding_service = AsyncEmbeddingService()
    database = AsyncEmbeddingDatabase(cache_path=embedding_database_file)
    await database.setup()
    
    sentences_file = root_path / "data" / "sentences.txt"
    with open(sentences_file) as file:
        data = file.read().splitlines()
    
    print(f"Found {len(data)} sentences to process")
    
    for i, text in enumerate(data):
        print(f"[{i+1}/{len(data)}] ", end="")
        await process_data(text, embedding_service, database)
    
    print("Done! Embeddings refreshed.")

if __name__ == "__main__":
    asyncio.run(main())