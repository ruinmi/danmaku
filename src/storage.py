import json
from typing import List, Dict

class Storage:
    def __init__(self, file_path: str):
        self.file_path = file_path
        
    def load(self) -> List[Dict]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
            
    def save(self, data: List[Dict]):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4) 