import os

from pymongo import MongoClient

_client: MongoClient | None = None


def connect():
    global _client
    uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    _client = MongoClient(uri)


def close():
    global _client
    if _client:
        _client.close()
        _client = None


def get_db():
    return _client["bhav"]
