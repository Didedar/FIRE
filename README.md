# FIRE — Freedom Intelligent Routing Engine

## Техническая документация v1.0

---

## Оглавление

1. [Обзор системы](#1-обзор-системы)
2. [Архитектура](#2-архитектура)
3. [Структура проекта](#3-структура-проекта)
4. [Стек технологий](#4-стек-технологий)
5. [Модели данных (БД)](#5-модели-данных-бд)
6. [NLP-модуль](#6-nlp-модуль)
7. [RAG-модель](#7-rag-модель)
8. [Геокодинг](#8-геокодинг)
9. [Маршрутизация (Routing Engine)](#9-маршрутизация-routing-engine)
10. [Сервисный слой (Backend)](#10-сервисный-слой-backend)
11. [API-эндпоинты](#11-api-эндпоинты)
12. [Фронтенд](#12-фронтенд)
13. [Конфигурация и развёртывание](#13-конфигурация-и-развёртывание)
14. [Обработка ошибок и отказоустойчивость](#14-обработка-ошибок-и-отказоустойчивость)
15. [Производительность](#15-производительность)

---

## 1. Обзор системы

**FIRE** (Freedom Intelligent Routing Engine) — система автоматической обработки и интеллектуальной маршрутизации обращений клиентов банка Freedom Finance.

### Что делает система

1. Принимает обращения клиентов (через CSV или API)
2. Анализирует текст с помощью LLM (Groq, модель Llama 3.3 70B)
3. Определяет геолокацию клиента (Nominatim + словарь городов)
4. Маршрутизирует обращение к оптимальному менеджеру по каскаду бизнес-правил
5. Предоставляет аналитический дашборд и ИИ-ассистента

### Масштаб

- 15 офисов по всему Казахстану
- 51 менеджер с различными навыками
- 7 типов обращений, 3 уровня тональности, 3 языка
- Целевая скорость: < 10 секунд на одно обращение
- Пакетная обработка: до 200 тикетов за сессию

---

## 2. Архитектура

### Высокоуровневая схема

```
                    +─────────────+
                    |  Frontend   |
                    |  React 19   |
                    +──────┬──────+
                           │ HTTP (Axios)
                           ▼
                    +─────────────+
                    |  FastAPI    |
                    |  Backend    |
                    +──────┬──────+
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        +──────────+ +──────────+ +──────────+
        | NLP      | | Geocoding| | RAG      |
        | Analyzer | | Service  | | Module   |
        +────┬─────+ +────┬─────+ +────┬─────+
             │             │            │
             ▼             ▼            ▼
        +──────────+ +──────────+ +──────────+
        | Groq API | | Nominatim| | PostgreSQL|
        | (LLM)    | | OSM API  | | (данные) |
        +──────────+ +──────────+ +──────────+
```

### Пайплайн обработки обращения

```
Обращение клиента
    │
    ▼
[1] Загрузка данных (CSV/API) → Ticket (status=new)
    │
    ▼
[2] NLP-анализ (TicketAnalyzer + RAG)
    ├── Тип обращения (7 категорий)
    ├── Тональность (3 уровня)
    ├── Приоритет (1-10)
    ├── Язык (KZ/ENG/RU)
    └── Summary с рекомендацией → AIAnalysis (status=analyzed)
    │
    ▼
[3] Геокодинг (каскад)
    ├── Nominatim OSM API (полный адрес)
    ├── Nominatim (упрощённый адрес)
    ├── Словарь городов КЗ
    └── Извлечение из текста → lat/lon + nearest_office
    │
    ▼
[4] Маршрутизация (каскад правил)
    ├── Географический фильтр → офис
    ├── Фильтр компетенций → VIP/язык/должность
    ├── Балансировка нагрузки → top-2 менеджера
    └── Round-Robin → выбор одного → Distribution (status=distributed)
    │
    ▼
[5] Результат
    ├── Тикет назначен менеджеру
    ├── Нагрузка менеджера обновлена
    └── Причина назначения записана
```

---

## 3. Структура проекта

```
FIRE/
├── backend/                           # FastAPI приложение
│   ├── app/
│   │   ├── main.py                   # Точка входа FastAPI
│   │   ├── config.py                 # Настройки (pydantic-settings)
│   │   ├── database.py               # SQLAlchemy engine + session
│   │   ├── __init__.py
│   │   ├── schemas/
│   │   │   └── __init__.py           # Pydantic-схемы (13 моделей)
│   │   ├── models/
│   │   │   ├── ticket.py             # Модель обращения
│   │   │   ├── manager.py            # Модель менеджера
│   │   │   ├── business_unit.py      # Модель офиса
│   │   │   ├── ai_analysis.py        # Результат NLP-анализа
│   │   │   ├── distribution.py       # Назначение тикета
│   │   │   └── __init__.py
│   │   ├── api/
│   │   │   ├── distribution.py       # Обработка, статистика, AI-ассистент
│   │   │   ├── tickets.py            # CRUD тикетов + фильтрация
│   │   │   ├── managers.py           # CRUD менеджеров + офисы
│   │   │   ├── upload.py             # Загрузка CSV
│   │   │   └── __init__.py
│   │   ├── services/
│   │   │   ├── nlp_client.py         # Оркестратор NLP-пайплайна + RAG
│   │   │   ├── distribution.py       # Движок распределения
│   │   │   ├── csv_parser.py         # Парсинг CSV (тикеты/менеджеры/офисы)
│   │   │   └── __init__.py
│   │   └── utils/
│   │       ├── geo.py                # Haversine, поиск ближайшего офиса
│   │       └── __init__.py
│   ├── migrations/                    # Alembic миграции
│   ├── csv_storage/                   # Хранилище загруженных CSV
│   ├── requirements.txt
│   ├── docker-compose.yml
│   └── .env.example
│
├── nlp_module/                        # Автономный NLP-модуль
│   ├── __init__.py                   # Экспорты модуля
│   ├── analyzer.py                   # TicketAnalyzer (Groq LLM)
│   ├── geocoding.py                  # GeocodingService (Nominatim + словарь)
│   ├── routing.py                    # RoutingEngine (каскад правил)
│   ├── rag.py                        # RAGKnowledgeBase (контекст для LLM)
│   ├── schemas.py                    # Pydantic-модели NLP
│   └── requirements.txt
│
├── frontend/                          # React-фронтенд
│   ├── src/
│   ├── public/
│   └── package.json
│
├── docker-compose.yml                 # Корневой Docker Compose
├── business_units.csv                 # Данные: 15 офисов
├── managers.csv                       # Данные: менеджеры
├── tickets.csv                        # Данные: 200 тикетов
└── .gitignore
```

---

## 4. Стек технологий

### Backend

| Компонент | Технология | Версия |
|-----------|-----------|--------|
| Web-фреймворк | FastAPI | 0.115.6 |
| ASGI-сервер | Uvicorn | 0.34.0 |
| ORM | SQLAlchemy | 2.0.36 |
| БД | PostgreSQL | 16 (Alpine) |
| Драйвер БД | psycopg2-binary | 2.9.10 |
| Миграции | Alembic | 1.14.1 |
| Валидация | Pydantic | 2.10.4 |
| Настройки | pydantic-settings | 2.7.1 |
| HTTP-клиент | httpx | 0.28.1 |
| CSV-парсинг | pandas | 2.2.3 |
| Env-файлы | python-dotenv | 1.0.1 |

### NLP-модуль

| Компонент | Технология | Версия |
|-----------|-----------|--------|
| LLM API | Groq | >= 0.13.0 |
| LLM-модель | Llama 3.3 70B | versatile |
| HTTP-клиент | httpx | 0.28.1 |
| Retry-логика | tenacity | 9.0.0 |
| Геокодинг | Nominatim OSM | API v1 |

### Frontend

| Компонент | Технология | Версия |
|-----------|-----------|--------|
| UI-фреймворк | React | 19.2.0 |
| Маршрутизация | React Router | 7.13.0 |
| HTTP-клиент | Axios | 1.13.5 |
| Графики | Recharts | 3.7.0 |
| Иконки | Lucide React | 0.575.0 |
| Анимации | Framer Motion | 12.34.3 |
| Сборка | Vite | 7.3.1 |
| Язык | TypeScript | — |

### Инфраструктура

| Компонент | Технология |
|-----------|-----------|
| Контейнеризация | Docker + Docker Compose |
| БД | PostgreSQL 16 Alpine |
| Порты | Backend: 8000, БД: 5433 |

---

## 5. Модели данных (БД)

### ER-диаграмма

```
┌───────────────┐       ┌────────────────┐       ┌───────────────┐
│   Ticket      │       │  AIAnalysis    │       │  Distribution │
├───────────────┤       ├────────────────┤       ├───────────────┤
│ id (PK, UUID) │◄──────│ ticket_id (FK) │◄──────│ ticket_id (FK)│
│ client_guid   │  1:1  │ id (PK, UUID)  │  1:1  │ id (PK, UUID) │
│ segment       │       │ type           │       │ ai_analysis_id│
│ description   │       │ tonality       │       │ manager_id(FK)│──┐
│ country       │       │ priority       │       │ reason        │  │
│ region        │       │ language       │       │ assigned_at   │  │
│ city          │       │ summary        │       └───────────────┘  │
│ street, house │       │ geo_lat/lon    │                          │
│ lat/lon       │       │ created_at     │                          │
│ status        │       └────────────────┘                          │
│ created_at    │                                                   │
└───────────────┘                                                   │
                                                                    │
┌───────────────┐       ┌────────────────┐                          │
│ BusinessUnit  │       │   Manager      │◄─────────────────────────┘
├───────────────┤       ├────────────────┤
│ id (PK, UUID) │◄──────│ business_unit  │
│ name          │  1:N  │   _id (FK)     │
│ address       │       │ id (PK, UUID)  │
│ latitude      │       │ full_name      │
│ longitude     │       │ position       │
└───────────────┘       │ skills (ARRAY) │
                        │ current_load   │
                        └────────────────┘
```

### Таблица: tickets

| Поле | Тип | Обязательное | Описание |
|------|-----|-------------|----------|
| id | UUID | PK | Уникальный идентификатор |
| client_guid | VARCHAR | Да | Идентификатор клиента |
| gender | VARCHAR | Нет | Пол клиента |
| birth_date | DATE | Нет | Дата рождения |
| segment | VARCHAR | Да | Сегмент: Mass, VIP, Priority (по умолчанию Mass) |
| description | TEXT | Нет | Текст обращения |
| attachments | TEXT | Нет | Вложения |
| country | VARCHAR | Нет | Страна |
| region | VARCHAR | Нет | Регион/область |
| city | VARCHAR | Нет | Город |
| street | VARCHAR | Нет | Улица |
| house | VARCHAR | Нет | Дом |
| latitude | FLOAT | Нет | Широта (из геокодинга) |
| longitude | FLOAT | Нет | Долгота (из геокодинга) |
| status | VARCHAR | Да | Статус: new → analyzed → distributed |
| created_at | TIMESTAMP | Да | Дата создания |

### Таблица: managers

| Поле | Тип | Обязательное | Описание |
|------|-----|-------------|----------|
| id | UUID | PK | Уникальный идентификатор |
| full_name | VARCHAR | Да | ФИО менеджера |
| position | VARCHAR | Да | Должность: Спец, Ведущий спец, Главный специалист |
| skills | ARRAY[VARCHAR] | Нет | Навыки: VIP, ENG, KZ |
| business_unit_id | UUID (FK) | Нет | Офис менеджера |
| current_load | INTEGER | Да | Текущая нагрузка (кол-во тикетов) |

### Таблица: business_units

| Поле | Тип | Обязательное | Описание |
|------|-----|-------------|----------|
| id | UUID | PK | Уникальный идентификатор |
| name | VARCHAR | Да | Название офиса (город) |
| address | VARCHAR | Нет | Адрес офиса |
| latitude | FLOAT | Нет | Широта |
| longitude | FLOAT | Нет | Долгота |

### Таблица: ai_analyses

| Поле | Тип | Обязательное | Описание |
|------|-----|-------------|----------|
| id | UUID | PK | Уникальный идентификатор |
| ticket_id | UUID (FK, unique) | Да | Связь с тикетом (1:1) |
| type | VARCHAR | Да | Тип обращения (7 категорий) |
| tonality | VARCHAR | Да | Тональность (3 значения) |
| priority | INTEGER | Да | Приоритет (1-10) |
| language | VARCHAR | Да | Язык (KZ, ENG, RU) |
| summary | TEXT | Нет | Резюме и рекомендация |
| geo_latitude | FLOAT | Нет | Широта из геокодинга |
| geo_longitude | FLOAT | Нет | Долгота из геокодинга |
| created_at | TIMESTAMP | Да | Дата создания |

### Таблица: distributions

| Поле | Тип | Обязательное | Описание |
|------|-----|-------------|----------|
| id | UUID | PK | Уникальный идентификатор |
| ticket_id | UUID (FK, unique) | Да | Связь с тикетом (1:1) |
| ai_analysis_id | UUID (FK) | Нет | Связь с анализом |
| manager_id | UUID (FK) | Да | Назначенный менеджер |
| reason | TEXT | Нет | Причина назначения |
| assigned_at | TIMESTAMP | Да | Дата назначения |

---

## 6. NLP-модуль

### 6.1 TicketAnalyzer (`nlp_module/analyzer.py`)

Основной класс для анализа текста обращений через Groq LLM.

**Модель:** `llama-3.3-70b-versatile`
**Температура:** 0.0 (детерминированный вывод)
**Макс. токенов:** 500
**Формат ответа:** JSON Object

#### Системный промпт

```
Ты — классификатор обращений клиентов банка Freedom Finance.
Проанализируй текст и верни ТОЛЬКО валидный JSON без markdown:
{
  "ticket_type": "<тип>",
  "sentiment": "<тональность>",
  "priority": <1-10>,
  "language": "<KZ|ENG|RU>",
  "summary": "<суть>. Рекомендация: <действие>"
}
```

При наличии RAG-контекста к промпту добавляется:

```
--- КОНТЕКСТ КОМПАНИИ (используй для рекомендаций) ---
[ОФИСЫ Freedom Finance — 15 городов Казахстана]
• Астана (N менеджеров)
...
[МЕНЕДЖЕРЫ]
...
[ПРАВИЛА МАРШРУТИЗАЦИИ]
...
```

#### Методы

| Метод | Сигнатура | Описание |
|-------|-----------|----------|
| `analyze` | `async (text, rag_context=None) → AnalysisResult` | Основной async-метод анализа |
| `analyze_sync` | `(text, rag_context=None) → AnalysisResult` | Синхронная версия |
| `_build_prompt` | `(rag_context=None) → str` | Сборка системного промпта |
| `_parse_response` | `(content, text) → AnalysisResult` | Парсинг и валидация JSON-ответа LLM |
| `_fallback_analysis` | `(text) → AnalysisResult` | Эвристический анализ при ошибке LLM |

#### Классификация (7 типов)

| Тип | Приоритет | Описание |
|-----|-----------|----------|
| Мошеннические действия | 9-10 | Fraud, списание без согласия, взлом |
| Претензия | 7-8 | Финансовые потери, требование возврата |
| Неработоспособность приложения | 7 | Ошибки, сбои, crash |
| Жалоба | 4-6 | Недовольство сервисом |
| Смена данных | 4 | Обновление адреса, номера |
| Консультация | 1-3 | Вопросы, информация |
| Спам | 1 | Нецелевые обращения |

#### Тональность (3 уровня)

| Значение | Ключевые слова (fallback) |
|----------|--------------------------|
| Негативный | плох, ужас, зл, недовол, отврат, жалоб, хам |
| Позитивный | спасибо, отлично, хорош, супер, доволен, рад |
| Нейтральный | (по умолчанию) |

#### Определение языка

| Язык | Критерий |
|------|---------|
| KZ | Наличие казахских символов: Ә, ғ, қ, ң, ө, ұ, ү, і, һ |
| ENG | > 70% латинских букв |
| RU | По умолчанию |

#### Retry-логика

```python
@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
```

- Повторные попытки при RateLimitError
- Экспоненциальный backoff: 2с → 4с → 8с
- Максимум 3 попытки

---

### 6.2 Схемы данных NLP (`nlp_module/schemas.py`)

```python
class GeoLocation(BaseModel):
    latitude: float
    longitude: float
    city: Optional[str] = None
    source: Literal["nominatim", "dictionary", "fallback"]

class AnalysisResult(BaseModel):
    ticket_type: Literal[7 типов]
    sentiment: Literal["Позитивный", "Нейтральный", "Негативный"]
    priority: int  # 1-10
    language: Literal["KZ", "ENG", "RU"]
    summary: str
    city: Optional[str] = None

class RoutingResult(BaseModel):
    manager_id: str
    manager_name: str
    office: str
    reason: str
    rules_applied: list[str]
```

---

## 7. RAG-модель

### 7.1 Обзор

RAG (Retrieval-Augmented Generation) обогащает промпт LLM контекстом из базы данных: информация о менеджерах, офисах и бизнес-правилах. Это позволяет LLM давать более точные рекомендации.

**Файл:** `nlp_module/rag.py`
**Класс:** `RAGKnowledgeBase`

### 7.2 Принцип работы

```
                ┌──────────────┐
                │ PostgreSQL   │
                │ (managers,   │
                │  offices)    │
                └──────┬───────┘
                       │ load_from_db()
                       ▼
                ┌──────────────┐
                │ RAGKnowledge │
                │ Base         │
                │ (кеш данных) │
                └──────┬───────┘
                       │ build_context()
                       ▼
                ┌──────────────┐
                │ Текстовый    │
                │ контекст     │
                │ (до 3000 sym)│
                └──────┬───────┘
                       │ inject into prompt
                       ▼
                ┌──────────────┐
                │ Groq LLM     │
                │ system_prompt│
                │ + контекст   │
                └──────────────┘
```

### 7.3 Структуры данных

```python
@dataclass
class ManagerInfo:
    full_name: str       # ФИО
    position: str        # Должность
    skills: list[str]    # Навыки [VIP, KZ, ENG]
    office_name: str     # Название офиса
    current_load: int    # Текущая нагрузка

@dataclass
class OfficeInfo:
    name: str            # Город
    address: str         # Адрес
    latitude: float      # Широта
    longitude: float     # Долгота
    manager_count: int   # Количество менеджеров
```

### 7.4 Методы

| Метод | Описание |
|-------|----------|
| `load_from_db(db_session)` | Загрузка данных из PostgreSQL (через SQLAlchemy) |
| `load_direct(managers, offices)` | Прямая загрузка (для тестов) |
| `build_context(nearest_office, segment, language)` | Генерация текстового контекста |
| `get_managers_for_office(office_name)` | Менеджеры конкретного офиса |
| `get_available_skills()` | Все уникальные навыки |
| `is_loaded` | Проверка загруженности данных |

### 7.5 Формат контекста

```
[ОФИСЫ Freedom Finance — 15 городов Казахстана]
• Астана (5 менеджеров)
• Алматы (7 менеджеров)
• Караганда (3 менеджера)
...

[МЕНЕДЖЕРЫ офиса Караганда] (3 чел.)
• Иванов И.И. | Ведущий спец | Навыки: VIP, KZ | Нагрузка: 2
• Петров П.П. | Спец | Навыки: — | Нагрузка: 5
• Сидорова С.С. | Главный специалист | Навыки: ENG | Нагрузка: 1

[ПРАВИЛА МАРШРУТИЗАЦИИ]
• VIP/Priority сегмент → менеджер с навыком VIP
• Тип "Смена данных" → только Главный специалист
• Язык KZ → менеджер с навыком KZ
• Язык ENG → менеджер с навыком ENG
• Мошеннические действия → приоритет 9-10, немедленная обработка
• Жалобы → приоритет 4-6, отработка с клиентом
• Если офис не определён → распределение 50/50 между Астана и Алматы
```

### 7.6 Интеграция

RAG загружается **один раз** перед обработкой батча и кешируется в синглтоне `_rag`:

```python
# В nlp_client.py
def load_rag_context(db_session):
    rag = _get_rag()
    if not rag.is_loaded:
        rag.load_from_db(db_session)

# Использование в analyze_ticket():
rag_context = rag.build_context(segment=segment)
analysis = await analyzer.analyze(text, rag_context=rag_context)
```

### 7.7 AI-ассистент с RAG

Эндпоинт `POST /api/ai-assistant` использует RAG для ответов на свободные вопросы:

```python
# Контекст для ассистента включает:
# 1. RAG-контекст (менеджеры, офисы, правила)
# 2. Текущая статистика (всего/распределено/ожидают)
# 3. Вопрос пользователя

response = groq_client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "Ты — ИИ-ассистент FIRE...\n" + rag_context + stats},
        {"role": "user", "content": query}
    ],
    temperature=0.3,
    max_tokens=500,
)
```

---

## 8. Геокодинг

### 8.1 Обзор

**Файл:** `nlp_module/geocoding.py`
**Класс:** `GeocodingService`

Каскадный геокодинг для определения координат клиента.

### 8.2 Каскад определения координат

```
Адрес: "Казахстан, Карагандинская, мкр. Центральный, 9.0"
    │
    ▼
[1] Nominatim OSM API (полный адрес)
    ├── Запрос: q="{address}, Казахстан"
    ├── Timeout: 5 секунд
    └── Результат: lat, lon, city ──→ Найдено? → ГОТОВО
    │ Не найдено
    ▼
[1b] Nominatim (упрощённый адрес)
    ├── _simplify_address() удаляет: мкр, ул, дом, кв, номера
    ├── "Карагандинская, Казахстан"
    └── Результат: lat, lon, city ──→ Найдено? → ГОТОВО
    │ Не найдено
    ▼
[2] Словарь городов Казахстана
    ├── 200+ вариантов написания (RU/KZ/EN)
    ├── Прямой match: "караганда" in address_lower
    └── Region→City: "карагандинск" → "караганда" ──→ Найдено? → ГОТОВО
    │ Не найдено
    ▼
[3] Извлечение из текста обращения
    ├── extract_city_from_text(ticket_text)
    └── Поиск в словаре ──→ Найдено? → ГОТОВО
    │ Не найдено
    ▼
[4] Гео-позиция не определена → 50/50 между Астана/Алматы
```

### 8.3 Маппинг регионов

Решает проблему: "Карагандинская" (область) не содержит подстроку "Караганда" (город).

| Регион (prefix) | Город | Офис |
|-----------------|-------|------|
| карагандинск | караганда | Караганда |
| алматинск | алматы | Алматы |
| акмолинск | кокшетау | Кокшетау |
| актюбинск | актобе | Актобе |
| атырауск | атырау | Атырау |
| восточно-казахстанск | усть-каменогорск | Усть-Каменогорск |
| жамбылск | тараз | Тараз |
| западно-казахстанск | уральск | Уральск |
| костанайск | костанай | Костанай |
| кызылординск | кызылорда | Кызылорда |
| мангистауск | актау | Актау |
| павлодарск | павлодар | Павлодар |
| северо-казахстанск | петропавловск | Петропавловск |
| туркестанск | шымкент | Шымкент |
| южно-казахстанск | шымкент | Шымкент |
| абайск | семей | Усть-Каменогорск |
| жетысуск | талдыкорган | Алматы |
| улытауск | жезказган | Караганда |

### 8.4 Упрощение адреса

Метод `_simplify_address()` удаляет детали, мешающие геокодингу:

```python
# Удаляемые паттерны:
# ^\\d+\\.?\\d*$       — номера домов (9.0, 15, 3-5)
# ^мкр\\.?             — микрорайон
# ^ул\\.?              — улица
# ^пр\\.?              — проспект
# ^д\\.?$              — дом
# ^кв\\.?              — квартира
# ^корп                — корпус
# ^стр\\.?             — строение
# ^блок                — блок

# Пример:
# Вход:  "Казахстан, Карагандинская, мкр. Центральный, 9.0"
# Выход: "Казахстан, Карагандинская"
```

### 8.5 Координаты 15 офисов

| Офис | Широта | Долгота |
|------|--------|---------|
| Актау | 43.6355 | 51.1680 |
| Актобе | 50.2839 | 57.1670 |
| Алматы | 43.2380 | 76.9458 |
| Астана | 51.1694 | 71.4491 |
| Атырау | 47.1068 | 51.9032 |
| Караганда | 49.8047 | 73.1094 |
| Кокшетау | 53.2836 | 69.3783 |
| Костанай | 53.2144 | 63.6246 |
| Кызылорда | 44.8488 | 65.5093 |
| Павлодар | 52.2873 | 76.9674 |
| Петропавловск | 54.8720 | 69.1414 |
| Тараз | 42.9000 | 71.3667 |
| Уральск | 51.2333 | 51.3667 |
| Усть-Каменогорск | 49.9482 | 82.6279 |
| Шымкент | 42.3154 | 69.5967 |

### 8.6 Haversine (расчёт расстояния)

```python
def haversine(lat1, lon1, lat2, lon2) -> float:
    """
    Расстояние в км между двумя точками на сфере (формула гаверсинуса).
    R = 6371 км (радиус Земли)
    """
```

---

## 9. Маршрутизация (Routing Engine)

### 9.1 Обзор

**Файл:** `nlp_module/routing.py`
**Класс:** `RoutingEngine`

Каскад бизнес-правил для назначения тикета оптимальному менеджеру.

### 9.2 Каскад правил

```
                    Все менеджеры (51)
                          │
                          ▼
              ┌─────────────────────┐
    Шаг 1     │ Географический      │
              │ фильтр              │
              │ (nearest office)    │
              └─────────┬───────────┘
                        │ Менеджеры в целевом офисе
                        ▼
              ┌─────────────────────┐
    Шаг 2     │ Фильтр компетенций │
              │ - VIP/Priority→VIP  │
              │ - Смена данных→Глав │
              │ - KZ→навык KZ       │
              │ - ENG→навык ENG     │
              └─────────┬───────────┘
                        │ Квалифицированные менеджеры
                        ▼
              ┌─────────────────────┐
    Шаг 3     │ Балансировка        │
              │ нагрузки            │
              │ (top-2 по min load) │
              └─────────┬───────────┘
                        │ 2 менеджера
                        ▼
              ┌─────────────────────┐
    Шаг 4     │ Round-Robin         │
              │ (чередование)       │
              └─────────┬───────────┘
                        │
                        ▼
                  1 менеджер
```

### 9.3 Географический фильтр

| Ситуация | Действие |
|----------|---------|
| Офис определён | Менеджеры только этого офиса |
| Офис не определён | Чередование 50/50: Астана → Алматы → Астана → ... |
| Зарубежный адрес | Чередование 50/50 |

Счётчик 50/50 хранится в `_office_counter` и обеспечивает равномерное распределение.

### 9.4 Фильтр компетенций

| Условие | Требование к менеджеру |
|---------|----------------------|
| Сегмент = VIP или Priority | Навык `VIP` в массиве skills |
| Тип = "Смена данных" | Должность `Главный специалист` |
| Язык = KZ | Навык `KZ` в массиве skills |
| Язык = ENG | Навык `ENG` в массиве skills |
| Язык = RU | Без ограничений |

### 9.5 Fallback-цепочка

```
1. Нет менеджеров после фильтров?
   → Убрать географический фильтр, оставить навыки

2. Всё ещё нет?
   → Убрать фильтр навыков, использовать всех менеджеров

3. Всё ещё нет?
   → Назначить менеджера с минимальной нагрузкой
```

### 9.6 Round-Robin

```python
# Состояние хранится в _rr_state: dict[tuple, int]
# Ключ: кортеж ID двух менеджеров (отсортированный)
# Значение: счётчик (чётный → первый, нечётный → второй)

key = tuple(sorted(m.id for m in top_two))
idx = rr_state[key] % 2
rr_state[key] += 1
selected = top_two[idx]
```

### 9.7 Формат причины назначения

```
"Офис: Караганда | Тип: Жалоба | Язык: RU | Сегмент: Mass | Нагрузка менеджера: 3"
```

---

## 10. Сервисный слой (Backend)

### 10.1 NLP Client (`backend/app/services/nlp_client.py`)

Оркестратор NLP-пайплайна. Управляет тремя синглтонами:

| Синглтон | Класс | Описание |
|----------|-------|----------|
| `_analyzer` | `TicketAnalyzer` / `_DummyAnalyzer` | Анализ текста через Groq LLM |
| `_geocoder` | `GeocodingService` | Геокодинг адресов |
| `_rag` | `RAGKnowledgeBase` | Контекст для LLM |

#### Основная функция

```python
async def analyze_ticket(
    text: str,              # Текст обращения
    address: str,           # Адрес клиента
    country: str = None,    # Страна
    db_session = None,      # Сессия БД (для RAG)
    segment: str = None,    # Сегмент клиента
) -> NLPResponse
```

**Возвращает:**

```python
NLPResponse(
    type="Жалоба",
    tonality="Негативный",
    priority=5,
    language="RU",
    summary="Клиент жалуется на обслуживание. Рекомендация: связаться и уточнить детали.",
    latitude=49.8047,
    longitude=73.1094,
    nearest_office="Караганда",
)
```

#### DummyAnalyzer

Эвристический fallback когда `GROQ_API_KEY` не задан:

```
Текст → keyword matching → ticket_type
     → positive/negative words → sentiment
     → kazakh chars / latin ratio → language
     → type → priority mapping → priority
```

### 10.2 Distribution Engine (`backend/app/services/distribution.py`)

Движок пакетного распределения тикетов.

```python
async def distribute_tickets(db: Session) -> dict
```

**Алгоритм:**

1. Загрузить все офисы и менеджеров
2. Загрузить RAG-контекст один раз
3. Получить нераспределённые тикеты
4. Для каждого тикета:
   - NLP-анализ (с RAG-контекстом)
   - Географический фильтр
   - Фильтр компетенций
   - Round-Robin назначение
   - Создать Distribution, обновить нагрузку
5. Commit и вернуть статистику

**Возвращает:**

```python
{
    "total": 200,
    "distributed": 195,
    "skipped": 5,
    "errors": ["Error for ticket abc: ..."],
}
```

### 10.3 CSV Parser (`backend/app/services/csv_parser.py`)

Три функции парсинга CSV с гибким маппингом колонок:

#### parse_tickets_csv

```
Колонки CSV → Поля Ticket
─────────────────────────
guid/client_guid      → client_guid
пол/gender            → gender
дата рождения/birth   → birth_date
сегмент/segment       → segment
описание/description  → description
страна/country        → country
область/region        → region
город/city            → city
улица/street          → street
дом/house             → house
```

#### parse_managers_csv

```
Колонки CSV → Поля Manager
──────────────────────────
ФИО/full_name          → full_name
должность/position     → position
навыки/skills          → skills (split по ; или ,)
офис/business_unit     → business_unit_id (lookup по name)
нагрузка/current_load  → current_load
```

#### parse_business_units_csv

```
Колонки CSV → Поля BusinessUnit
──────────────────────────────
название/name   → name
адрес/address   → address
+ автогеокодинг → latitude, longitude
```

---

## 11. API-эндпоинты

### 11.1 Обработка обращений

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/api/v1/process` | Обработка одного тикета (NLP + маршрутизация) |
| POST | `/api/v1/batch` | Пакетная обработка CSV (async, semaphore=10) |
| POST | `/api/v1/process-all` | Полный цикл: загрузка 3 CSV + обработка всех |
| POST | `/api/distribute` | Legacy: распределение нераспределённых тикетов |

#### POST /api/v1/process

**Request:**
```json
{
    "client_guid": "CL-001",
    "description": "Не могу зайти в приложение, постоянно вылетает",
    "segment": "Mass",
    "country": "Казахстан",
    "region": "Карагандинская",
    "city": "мкр. Центральный",
    "house": "9.0"
}
```

**Response:**
```json
{
    "ticket_id": "a1b2c3d4-...",
    "status": "distributed",
    "processing_time_ms": 3421.5,
    "analysis": {
        "type": "Неработоспособность приложения",
        "tonality": "Негативный",
        "priority": 7,
        "language": "RU",
        "summary": "Клиент сообщает о проблемах с мобильным приложением. Рекомендация: проверить версию ПО и направить в тех. поддержку."
    },
    "assigned_manager": {
        "id": "m1n2o3p4-...",
        "name": "Сидорова С.С.",
        "position": "Ведущий спец",
        "office": "Караганда"
    },
    "routing_reason": "Офис: Караганда | Тип: Неработоспособность приложения | Язык: RU | Сегмент: Mass"
}
```

### 11.2 Тикеты

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/api/v1/tickets` | Список с пагинацией и фильтрами |
| GET | `/api/v1/tickets/{id}` | Детали одного тикета |
| DELETE | `/api/v1/tickets/{id}` | Удалить тикет (каскад) |
| DELETE | `/api/v1/tickets` | Удалить все тикеты |

**Фильтры GET /api/v1/tickets:**

| Параметр | Тип | Пример |
|----------|-----|--------|
| page | int | 1 |
| per_page | int | 20 |
| status | string | distributed |
| segment | string | VIP |
| ticket_type | string | Жалоба |
| language | string | KZ |
| city | string | Алматы |
| office | string | Астана |
| priority | int | 7 |
| search | string | приложение |

### 11.3 Менеджеры

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/api/v1/managers` | Список всех менеджеров |
| GET | `/api/v1/managers/offices` | Список всех офисов |
| DELETE | `/api/v1/managers/{id}` | Удалить менеджера |
| DELETE | `/api/v1/managers` | Удалить всех менеджеров |
| DELETE | `/api/v1/managers/offices/{id}` | Удалить офис |
| DELETE | `/api/v1/managers/offices` | Удалить все офисы |

### 11.4 Загрузка данных

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/api/upload/tickets` | Загрузить CSV с тикетами |
| POST | `/api/upload/managers` | Загрузить CSV с менеджерами |
| POST | `/api/upload/business-units` | Загрузить CSV с офисами |

### 11.5 Аналитика

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/api/v1/stats` | Дашборд-статистика |
| POST | `/api/ai-assistant` | ИИ-ассистент (RAG + LLM) |

#### GET /api/v1/stats

**Response:**
```json
{
    "total_tickets": 200,
    "distributed_tickets": 195,
    "analyzed_tickets": 3,
    "pending_tickets": 2,
    "avg_priority": 4.7,
    "type_distribution": {
        "Жалоба": 45,
        "Консультация": 60,
        "Претензия": 25,
        "..."
    },
    "tonality_distribution": {
        "Позитивный": 30,
        "Нейтральный": 120,
        "Негативный": 50
    },
    "language_distribution": {"RU": 180, "KZ": 15, "ENG": 5},
    "manager_load": [
        {"name": "Иванов И.И.", "load": 8, "position": "Ведущий спец", "office": "Астана"},
        "..."
    ],
    "office_distribution": {"Астана": 35, "Алматы": 30, "..."}
}
```

#### POST /api/ai-assistant

**Структурированные запросы** (с графиками):

| Ключевые слова | Тип графика | Данные |
|---------------|-------------|--------|
| "тип" + "город/офис" | grouped_bar | Типы по городам |
| "нагрузка/менеджер" | bar | Нагрузка менеджеров |
| "тональность/сентимент" | pie | Распределение тональности |
| "приоритет" | bar | Распределение по приоритету |
| "язык/language" | pie | Распределение по языкам |
| "сегмент" | pie | Распределение по сегментам |

**Свободные вопросы** (RAG + LLM):

```json
// Request
{"query": "Какие менеджеры в Караганде свободны?"}

// Response
{
    "answer": "В офисе Караганда 3 менеджера. Наименьшая нагрузка у Сидоровой С.С. (1 тикет)...",
    "chart_type": null,
    "data": null
}
```

### 11.6 Служебные

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/` | Информация о сервисе |
| GET | `/api/health` | Health check |

---

## 12. Фронтенд

### Стек

- **React 19** + TypeScript
- **Vite 7** — сборка и dev-сервер
- **React Router 7** — маршрутизация
- **Axios** — HTTP-клиент к Backend API
- **Recharts** — графики и диаграммы для дашборда
- **Lucide React** — библиотека иконок
- **Framer Motion** — анимации и переходы

### Взаимодействие с Backend

Все запросы через Axios к `http://localhost:8000/api/`:

```
Frontend (React)  ←→  Backend (FastAPI :8000)
    │                       │
    ├── GET /v1/tickets     │ Список тикетов с фильтрами
    ├── GET /v1/stats       │ Статистика для дашборда
    ├── POST /v1/process    │ Обработка одного тикета
    ├── POST /v1/batch      │ Пакетная обработка
    ├── POST /ai-assistant  │ ИИ-ассистент
    ├── GET /v1/managers    │ Список менеджеров
    └── POST /upload/*      │ Загрузка CSV
```

---

## 13. Конфигурация и развёртывание

### 13.1 Переменные окружения

| Переменная | Обязательная | По умолчанию | Описание |
|-----------|-------------|-------------|----------|
| `GROQ_API_KEY` | Нет* | None | API-ключ Groq (без него — fallback-эвристика) |
| `DATABASE_URL` | Нет | postgresql://fire_user:fire_password@localhost:5433/fire_db | URL базы данных |
| `BATCH_SEMAPHORE_LIMIT` | Нет | 10 | Лимит параллельной обработки |
| `CSV_STORAGE_PATH` | Нет | csv_storage | Директория для загруженных CSV |

*Рекомендуется задать GROQ_API_KEY для полноценной работы NLP.

### 13.2 Получение GROQ_API_KEY

1. Зарегистрироваться на [console.groq.com](https://console.groq.com)
2. Создать API-ключ
3. Добавить в файл `.env`:
   ```
   GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
   ```

### 13.3 Docker Compose

```bash
# Запуск всей системы (БД + Backend)
cd backend
docker-compose up -d

# Или из корня (только БД)
docker-compose up -d
```

**Сервисы:**

| Сервис | Образ | Порт | Описание |
|--------|-------|------|----------|
| postgres | postgres:16-alpine | 5433 | PostgreSQL БД |
| backend | Dockerfile (local) | 8000 | FastAPI приложение |

**Docker Compose (backend/docker-compose.yml):**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: fire_db
      POSTGRES_USER: fire_user
      POSTGRES_PASSWORD: fire_password
    ports:
      - "5433:5432"
    volumes:
      - fire_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fire_user -d fire_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://fire_user:fire_password@postgres:5432/fire_db
      - GROQ_API_KEY=${GROQ_API_KEY}
    volumes:
      - ./csv_storage:/app/csv_storage
```

### 13.4 Локальный запуск (без Docker)

```bash
# 1. PostgreSQL (порт 5433)
# Убедиться что БД fire_db существует

# 2. Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
# Отредактировать .env: добавить GROQ_API_KEY
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Frontend
cd frontend
npm install
npm run dev
```

### 13.5 Инициализация данных

Таблицы создаются автоматически при запуске (`Base.metadata.create_all()`).

Загрузка данных через API:

```bash
# Вариант 1: Через process-all (загружает все 3 CSV и обрабатывает)
curl -X POST http://localhost:8000/api/v1/process-all

# Вариант 2: По отдельности
curl -X POST http://localhost:8000/api/upload/business-units -F "file=@business_units.csv"
curl -X POST http://localhost:8000/api/upload/managers -F "file=@managers.csv"
curl -X POST http://localhost:8000/api/upload/tickets -F "file=@tickets.csv"
curl -X POST http://localhost:8000/api/distribute
```

---

## 14. Обработка ошибок и отказоустойчивость

### 14.1 Цепочка fallback-ов

```
Уровень 1: LLM
├── Groq LLM доступен → NLP-анализ через Llama 3.3 70B
├── RateLimitError → Retry с exponential backoff (3 попытки)
└── Groq недоступен → Эвристический классификатор (keyword matching)

Уровень 2: Геокодинг
├── Nominatim найдёт полный адрес → координаты
├── Nominatim найдёт упрощённый → координаты
├── Словарь городов (match по названию) → координаты
├── Маппинг регионов (Карагандинская → Караганда) → координаты
├── Извлечение города из текста обращения → координаты
└── Не найдено → 50/50 Астана/Алматы

Уровень 3: Маршрутизация
├── Менеджеры в целевом офисе с нужными навыками → назначение
├── Менеджеры во всех офисах с нужными навыками → назначение
├── Любые менеджеры (без фильтра навыков) → назначение
└── Нет менеджеров → пропуск тикета, запись ошибки

Уровень 4: RAG
├── БД доступна → RAG-контекст загружен
└── БД недоступна → Анализ без RAG (базовый промпт)
```

### 14.2 Логирование

Структурированные логи через `logging`:

```
Формат: {время} │ {уровень} │ {модуль} │ {сообщение}

Пример полного пайплайна:
11:00:30 │ INFO    │ app.services.nlp_client │ 🔥 NLP Pipeline START
11:00:30 │ INFO    │ app.services.nlp_client │ 📝 Текст (145 символов): Не могу зайти...
11:00:30 │ INFO    │ app.services.nlp_client │ 📍 Адрес: Карагандинская, мкр. Центральный
11:00:30 │ INFO    │ app.services.nlp_client │ 📚 RAG контекст подготовлен (2847 символов)
11:00:31 │ INFO    │ nlp_module.analyzer     │ 🤖 Groq LLM: Отправляю запрос
11:00:32 │ INFO    │ nlp_module.analyzer     │ ⚡ Groq LLM: Ответ получен за 1523мс
11:00:32 │ INFO    │ nlp_module.analyzer     │ ✅ Тип: Неработоспособность приложения
11:00:32 │ INFO    │ nlp_module.geocoding    │ 🌍 Геокодинг: 'Карагандинская, мкр...'
11:00:33 │ INFO    │ nlp_module.geocoding    │ 🔍 [1b] Пробую Nominatim упрощённый
11:00:33 │ INFO    │ nlp_module.geocoding    │ ✅ Словарь: Караганда (49.8047, 73.1094)
11:00:33 │ INFO    │ app.services.nlp_client │ 🏢 Ближайший офис: Караганда
11:00:33 │ INFO    │ app.services.nlp_client │ 🔥 NLP Pipeline DONE
```

---

## 15. Производительность

### 15.1 Целевые метрики

| Метрика | Целевое значение | Узкое место |
|---------|-----------------|-------------|
| Одиночный тикет | < 10 секунд | Groq API (~1-2с) + Nominatim (~1-2с) |
| Пакет (200 шт.) | < 5 минут | Semaphore(10), параллельная обработка |
| Fallback (без LLM) | < 50 мс | Эвристика + словарь |

### 15.2 Параллельная обработка

```python
# Semaphore ограничивает одновременные запросы
semaphore = asyncio.Semaphore(10)

# asyncio.gather обрабатывает тикеты параллельно
results = await asyncio.gather(
    *[process_one(t) for t in tickets],
    return_exceptions=True,
)
```

### 15.3 Оптимизации

| Оптимизация | Описание |
|-------------|----------|
| RAG-кеширование | Загрузка из БД один раз на батч |
| Ленивая инициализация | Синглтоны создаются при первом обращении |
| Упрощение адреса | Меньше запросов к Nominatim |
| Словарь регионов | Мгновенный fallback без API-вызовов |
| Пакетный commit | Один `db.commit()` на весь батч |
| Round-Robin state | In-memory, без обращений к БД |

### 15.4 Масштабирование

| Направление | Подход |
|-------------|--------|
| Вертикальное | Увеличить `BATCH_SEMAPHORE_LIMIT` |
| Горизонтальное | Несколько инстансов Backend за балансировщиком |
| БД | Read-replicas для GET-запросов |
| Кеширование | Redis для RAG-контекста (будущее) |
| Очереди | Celery/RabbitMQ для асинхронной обработки (будущее) |

---

*Документация актуальна на 22.02.2026. Версия системы: 1.0.0.*
