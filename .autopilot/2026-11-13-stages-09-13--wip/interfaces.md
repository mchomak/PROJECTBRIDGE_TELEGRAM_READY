# Границы

Доменные приложения владеют собственными данными; AI Router — единая граница вызовов моделей; Project State изменяется через свои сервисы. Подробности — в технических документах и брифах.

Начальное пространство эмбеддингов: `text-embedding-3-small`, 1536 измерений; договорённый интерфейс этапа 09 — `apps.ai_assistant.embedding.embed_texts(texts, *, task_key="document_embedding") -> EmbeddingBatch(vectors, profile_key, model_name, profile_version)`, этап 10 подключает его к маршрутизатору.
