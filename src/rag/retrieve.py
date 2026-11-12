"""Лексический поиск (BM25) по чанкам.

Это baseline, который работает без эмбеддингов и GPU. Следующий шаг —
гибрид: BM25 + векторный поиск + реранкер. Интерфейс Retriever при этом
не меняется, поэтому API и UI трогать не придётся.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

TOKEN_RE = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)

# Минимальный набор стоп-слов: нужен, чтобы не считать служебные слова
# доказательством релевантности. Список можно расширять по golden-set.
STOPWORDS = {
    "а", "без", "более", "бы", "был", "была", "были", "было", "быть", "в",
    "вам", "вас", "вдруг", "ведь", "во", "вот", "впрочем", "все", "всего",
    "всех", "всю", "вы", "где", "да", "даже", "два", "для", "до", "другой",
    "его", "ее", "ей", "ему", "если", "есть", "еще", "ж", "же", "за",
    "зачем", "здесь", "и", "из", "или", "им", "иногда", "их", "к", "как",
    "какая", "какие", "какой", "когда", "кто", "куда", "ли", "лучше",
    "между", "меня", "мне", "много", "может", "можно", "мой", "моя", "мы",
    "на", "над", "надо", "наконец", "нас", "не", "него", "нее", "ней",
    "нельзя", "нет", "ни", "нибудь", "никогда", "ним", "них", "ничего",
    "но", "ну", "о", "об", "один", "он", "она", "они", "опять", "от",
    "перед", "по", "под", "после", "потом", "потому", "почти", "при",
    "про", "раз", "разве", "с", "сам", "себе", "себя", "сейчас", "со",
    "совсем", "так", "также", "такой", "там", "тебе", "тебя", "тем",
    "теперь", "то", "тогда", "того", "тоже", "только", "том", "тот",
    "три", "тут", "ты", "у", "уж", "уже", "хорошо", "хоть", "чего", "чем",
    "через", "что", "чтоб", "чтобы", "чуть", "эта", "эти", "это", "этого",
    "этой", "этом", "этот", "эту", "я",
}


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def content_terms(text: str) -> set[str]:
    """Значимые слова запроса: без стоп-слов и односимвольных токенов."""
    return {term for term in tokenize(text) if term not in STOPWORDS and len(term) > 1}



class Retriever:
    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.docs = [tokenize(chunk.get("text", "")) for chunk in chunks]
        self.doc_freq: Counter[str] = Counter()
        for doc in self.docs:
            self.doc_freq.update(set(doc))
        self.n_docs = max(len(self.docs), 1)
        self.avg_len = (sum(len(doc) for doc in self.docs) / self.n_docs) or 1.0

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "Retriever":
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        chunks = [json.loads(line) for line in lines if line.strip()]
        return cls(chunks)

    def search(
        self,
        query: str,
        k: int = 5,
        university: str | None = None,
    ) -> list[dict]:
        terms = tokenize(query)
        if not terms:
            return []

        k1, b = 1.5, 0.75
        scored: list[tuple[float, dict]] = []

        for chunk, doc in zip(self.chunks, self.docs):
            if university and chunk.get("university") not in (None, university):
                continue

            term_freq = Counter(doc)
            score = 0.0
            for term in terms:
                if term not in term_freq:
                    continue
                df = self.doc_freq[term]
                idf = math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))
                tf = term_freq[term]
                denominator = tf + k1 * (1 - b + b * len(doc) / self.avg_len)
                score += idf * (tf * (k1 + 1)) / denominator

            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [{"score": round(score, 4), **chunk} for score, chunk in scored[:k]]

    def coverage(self, query: str, chunk: dict) -> float:
        """Доля значимых слов запроса, которые есть в чанке.

        Простой guard от ответов на вопросы «не по теме»: BM25 найдёт хоть
        что-нибудь почти всегда, а coverage позволяет честно отказаться.
        Порог подбирается на golden-set.
        """
        terms = content_terms(query)
        if not terms:
            return 1.0
        document = set(tokenize(chunk.get("text", "")))
        return len(terms & document) / len(terms)
