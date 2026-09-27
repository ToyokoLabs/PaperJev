import json
import os
from pathlib import Path

class Config:
    def __init__(self):
        self.ncbi_config = self._load_json("config.json")
        self.ollama_config = self._load_json("ollama_config.json")

    def _load_json(self, path: str) -> dict:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    @property
    def ncbi_email(self):
        return self.ncbi_config.get("NCBI_EMAIL")

    @property
    def ncbi_api_key(self):
        return self.ncbi_config.get("NCBI_API_KEY")

    @property
    def typesafe_api_key(self):
        return self.ncbi_config.get("TYPESAFE_API_KEY")

    @property
    def ollama_url(self):
        return os.environ.get("OLLAMA_URL") or self.ollama_config.get("ollama_url", "http://localhost:11434")

    @property
    def ollama_model(self):
        return self.ollama_config.get("model", "llama3")

    @property
    def ollama_params(self):
        return self.ollama_config.get("parameters", {})

config = Config()
