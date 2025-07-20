"""
文本嵌入處理模組
負責將文本轉換為向量表示，支援語義搜尋
"""

import os
import re
import hashlib
from typing import List, Dict, Any, Optional, Protocol
from dataclasses import dataclass
from abc import ABC, abstractmethod

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class EmbeddingProvider(Protocol):
    """嵌入提供者協議"""
    
    def embed_text(self, text: str) -> List[float]:
        """將文本轉換為向量"""
        ...
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量處理文本向量化"""
        ...


@dataclass
class EmbeddingConfig:
    """嵌入配置"""
    model_name: str = "text-embedding-3-small"
    max_tokens: int = 8192
    batch_size: int = 50
    cache_embeddings: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "batch_size": self.batch_size,
            "cache_embeddings": self.cache_embeddings
        }


class OpenAIEmbeddings:
    """OpenAI 嵌入服務"""
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not available. Install with: pip install openai")
        
        # 設定 API 金鑰
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = openai.OpenAI(api_key=api_key)
        self._cache: Dict[str, List[float]] = {}
    
    def _get_cache_key(self, text: str) -> str:
        """生成快取鍵"""
        return hashlib.md5(f"{self.config.model_name}:{text}".encode()).hexdigest()
    
    def embed_text(self, text: str) -> List[float]:
        """將單個文本轉換為向量"""
        if not text.strip():
            return [0.0] * 1536  # 預設向量維度
        
        # 檢查快取
        cache_key = self._get_cache_key(text)
        if self.config.cache_embeddings and cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            response = self.client.embeddings.create(
                model=self.config.model_name,
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            
            # 儲存快取
            if self.config.cache_embeddings:
                self._cache[cache_key] = embedding
            
            return embedding
            
        except Exception as e:
            print(f"Error creating embedding: {e}")
            # 返回零向量作為後備
            return [0.0] * 1536
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量處理文本向量化"""
        if not texts:
            return []
        
        embeddings = []
        
        # 分批處理
        for i in range(0, len(texts), self.config.batch_size):
            batch = texts[i:i + self.config.batch_size]
            
            # 檢查快取
            batch_embeddings = []
            uncached_texts = []
            uncached_indices = []
            
            for j, text in enumerate(batch):
                cache_key = self._get_cache_key(text)
                if self.config.cache_embeddings and cache_key in self._cache:
                    batch_embeddings.append(self._cache[cache_key])
                else:
                    batch_embeddings.append(None)
                    uncached_texts.append(text)
                    uncached_indices.append(j)
            
            # 處理未快取的文本
            if uncached_texts:
                try:
                    response = self.client.embeddings.create(
                        model=self.config.model_name,
                        input=uncached_texts,
                        encoding_format="float"
                    )
                    
                    # 填入結果
                    for idx, embedding_data in enumerate(response.data):
                        original_idx = uncached_indices[idx]
                        embedding = embedding_data.embedding
                        batch_embeddings[original_idx] = embedding
                        
                        # 儲存快取
                        if self.config.cache_embeddings:
                            cache_key = self._get_cache_key(uncached_texts[idx])
                            self._cache[cache_key] = embedding
                
                except Exception as e:
                    print(f"Error in batch embedding: {e}")
                    # 填入零向量
                    for idx in uncached_indices:
                        batch_embeddings[idx] = [0.0] * 1536
            
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def get_cache_stats(self) -> Dict[str, int]:
        """獲取快取統計"""
        return {
            "cached_embeddings": len(self._cache),
            "cache_size_mb": sum(len(str(v)) for v in self._cache.values()) / (1024 * 1024)
        }


class TextChunker:
    """文本分塊處理器"""
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str) -> List[str]:
        """將長文本分割為較小的塊"""
        if not text or len(text) <= self.chunk_size:
            return [text] if text else []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # 嘗試在句子邊界分割
            if end < len(text):
                # 尋找最近的句號、問號或感嘆號
                for punct in ['。', '！', '？', '.', '!', '?']:
                    punct_pos = text.rfind(punct, start, end)
                    if punct_pos > start:
                        end = punct_pos + 1
                        break
                else:
                    # 如果沒找到標點，嘗試在空格處分割
                    space_pos = text.rfind(' ', start, end)
                    if space_pos > start:
                        end = space_pos
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.overlap if end < len(text) else end
        
        return chunks
    
    def chunk_location_text(self, location_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """為地點資料創建文本塊"""
        searchable_text = location_data.get('searchable_text', '')
        
        if not searchable_text:
            return []
        
        chunks = self.chunk_text(searchable_text)
        
        result = []
        for i, chunk in enumerate(chunks):
            chunk_data = {
                'location_id': location_data.get('id'),
                'chunk_index': i,
                'text': chunk,
                'metadata': {
                    'name': location_data.get('primary_name', ''),
                    'category': location_data.get('category', ''),
                    'tags': location_data.get('all_tags', []),
                    'coordinates': location_data.get('coordinates', {}),
                    'total_chunks': len(chunks)
                }
            }
            result.append(chunk_data)
        
        return result


class EmbeddingManager:
    """嵌入管理器"""
    
    def __init__(self, provider: Optional[EmbeddingProvider] = None):
        self.provider = provider or OpenAIEmbeddings()
        self.chunker = TextChunker()
    
    def process_locations(self, locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """處理地點資料，生成嵌入向量"""
        all_chunks = []
        
        # 為每個地點生成文本塊
        for location in locations:
            chunks = self.chunker.chunk_location_text(location)
            all_chunks.extend(chunks)
        
        if not all_chunks:
            return []
        
        # 批量生成嵌入向量
        texts = [chunk['text'] for chunk in all_chunks]
        embeddings = self.provider.embed_batch(texts)
        
        # 將嵌入向量添加到塊資料中
        for chunk, embedding in zip(all_chunks, embeddings):
            chunk['embedding'] = embedding
        
        return all_chunks
    
    def process_single_query(self, query: str) -> List[float]:
        """處理單個查詢，生成嵌入向量"""
        return self.provider.embed_text(query)


# 工具函數
def normalize_text(text: str) -> str:
    """標準化文本"""
    if not text:
        return ""
    
    # 移除多餘的空白
    text = re.sub(r'\s+', ' ', text.strip())
    
    # 統一標點符號
    text = text.replace('，', ', ').replace('。', '. ')
    text = text.replace('！', '! ').replace('？', '? ')
    
    return text


def extract_key_phrases(text: str, max_phrases: int = 10) -> List[str]:
    """提取關鍵詞組"""
    if not text:
        return []
    
    # 簡單的關鍵詞提取（可以後續改進為更複雜的 NLP 方法）
    import re
    
    # 移除標點符號，分割詞語
    words = re.findall(r'\b\w+\b', text.lower())
    
    # 過濾常見停用詞
    stop_words = {
        '的', '在', '是', '和', '與', '有', '這', '那', '一個', '可以', '能夠',
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'
    }
    
    filtered_words = [w for w in words if w not in stop_words and len(w) > 1]
    
    # 返回前 N 個詞（簡化版本）
    return filtered_words[:max_phrases]


if __name__ == "__main__":
    # 測試嵌入功能
    config = EmbeddingConfig()
    embeddings = OpenAIEmbeddings(config)
    
    test_text = "福井縣的美麗神社，擁有悠久的歷史。"
    result = embeddings.embed_text(test_text)
    
    print(f"Text: {test_text}")
    print(f"Embedding dimension: {len(result)}")
    print(f"First 5 values: {result[:5]}")