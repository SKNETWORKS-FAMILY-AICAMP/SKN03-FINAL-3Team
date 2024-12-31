# modules/faiss_indexer.py

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from .config import AYA_EMBEDDING_MODEL, SIMILARITY_THRESHOLD, TOP_K
from .preprocessor import sanitize_documents

class FaissIndexer:
    def __init__(self, qa_dataset):
        self.qa_dataset = qa_dataset
        self.embedding_model = SentenceTransformer(AYA_EMBEDDING_MODEL)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.qa_embeddings = None

    def build_index(self):
        embeddings = []
        for item in self.qa_dataset:
            emb = self.get_embedding(item["instruction"])
            embeddings.append(emb)
        self.qa_embeddings = np.array(embeddings, dtype='float32')

        self.index.add(self.qa_embeddings)

    def get_embedding(self, text):
        return self.embedding_model.encode([text])[0]

    def search(self, query_emb):
        # 코사인 유사도 계산
        all_sims = cosine_similarity([query_emb], self.qa_embeddings)[0]
        # threshold 이상인 인덱스
        filtered_indices = np.where(all_sims >= SIMILARITY_THRESHOLD)[0]
        # 상위 TOP_K
        sorted_indices = filtered_indices[np.argsort(-all_sims[filtered_indices])]
        top_indices = sorted_indices[:TOP_K]
        return top_indices, all_sims
