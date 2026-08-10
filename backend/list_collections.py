import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import django; django.setup()
import chromadb
from core.kiki.config import kiki_settings

client = chromadb.PersistentClient(path=kiki_settings.CHROMADB_PERSIST_DIRECTORY)
colls = client.list_collections()
print("Collections found:", len(colls))
for c in colls:
    print(f"  NAME: {c.name}  COUNT: {c.count()}  META: {c.metadata}")
