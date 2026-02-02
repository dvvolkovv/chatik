# 🚀 AI Chat Platform - Backend

Backend API на Python + FastAPI для платформы персонализированного AI-чата.

## 📋 Возможности

- ✅ **Аутентификация** - JWT токены, регистрация/логин
- ✅ **Чаты и сообщения** - CRUD операции, история
- ✅ **Multi-LLM** - Интеграция OpenAI, Claude, Gemini
- ✅ **Streaming** - Потоковая передача ответов
- ✅ **Профилирование** - Система персонализации пользователей
- ✅ **Файлы** - Загрузка изображений и документов
- ✅ **Async/Await** - Высокая производительность
- ✅ **Auto docs** - Swagger UI из коробки

## 🛠 Технологический стек

- **Python 3.11+**
- **FastAPI** - современный async фреймворк
- **PostgreSQL** - основная БД
- **Redis** - кэш и сессии
- **SQLAlchemy 2.0** - async ORM
- **Alembic** - миграции БД
- **OpenAI SDK** - интеграция GPT моделей
- **Anthropic SDK** - интеграция Claude
- **Google AI SDK** - интеграция Gemini

## 📁 Структура проекта

```
ai-chat-backend/
├── app/
│   ├── api/                    # API endpoints
│   │   ├── auth.py            # Аутентификация
│   │   ├── chat.py            # Чаты
│   │   ├── llm.py             # LLM endpoints
│   │   ├── profile.py         # Профили
│   │   └── files.py           # Файлы
│   ├── core/                  # Ядро приложения
│   │   ├── config.py          # Настройки
│   │   ├── database.py        # БД подключение
│   │   └── security.py        # JWT, безопасность
│   ├── models/                # SQLAlchemy модели
│   │   ├── user.py
│   │   ├── chat.py
│   │   ├── message.py
│   │   ├── profile.py
│   │   ├── file.py
│   │   └── transaction.py
│   ├── schemas/               # Pydantic схемы
│   │   ├── user.py
│   │   ├── chat.py
│   │   ├── message.py
│   │   └── profile.py
│   ├── services/              # Бизнес-логика
│   │   └── llm_service.py    # LLM интеграции
│   └── main.py                # FastAPI приложение
├── alembic/                   # Database migrations
├── tests/                     # Тесты
├── requirements.txt           # Python зависимости
├── Dockerfile                 # Docker образ
├── docker-compose.yml         # Локальная разработка
├── railway.json               # Railway конфигурация
├── .env.example               # Пример переменных окружения
└── README.md                  # Этот файл
```

## 🚀 Быстрый старт

### 1. Клонируйте и установите зависимости

```bash
cd ai-chat-backend

# Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установите зависимости
pip install -r requirements.txt
```

### 2. Настройте переменные окружения

```bash
cp .env.example .env
# Отредактируйте .env файл с вашими настройками
```

**Обязательно укажите:**
- `SECRET_KEY` - секретный ключ приложения
- `JWT_SECRET_KEY` - ключ для JWT
- `DATABASE_URL` - URL PostgreSQL
- `OPENAI_API_KEY` - ключ OpenAI API

### 3. Запустите с Docker Compose (рекомендуется)

```bash
# Запустить все сервисы (PostgreSQL + Redis + Backend)
docker-compose up -d

# Проверить логи
docker-compose logs -f backend

# Остановить
docker-compose down
```

Приложение будет доступно на: http://localhost:8000

### 4. Или запустите локально

```bash
# Убедитесь, что PostgreSQL и Redis запущены

# Применить миграции
alembic upgrade head

# Запустить сервер
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 API Документация

После запуска приложения:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Основные endpoints:

#### Аутентификация
```
POST   /api/v1/auth/register       # Регистрация
POST   /api/v1/auth/login          # Вход
GET    /api/v1/auth/me             # Текущий пользователь
POST   /api/v1/auth/logout         # Выход
```

#### Чаты
```
GET    /api/v1/chats               # Список чатов
POST   /api/v1/chats               # Создать чат
GET    /api/v1/chats/{id}          # Получить чат
PATCH  /api/v1/chats/{id}          # Обновить чат
DELETE /api/v1/chats/{id}          # Удалить чат
```

#### LLM
```
POST   /api/v1/llm/chat/{id}/message         # Отправить сообщение
POST   /api/v1/llm/chat/{id}/message/stream  # Streaming сообщение
GET    /api/v1/llm/models                    # Доступные модели
```

#### Профиль
```
GET    /api/v1/profile             # Получить профиль
PUT    /api/v1/profile             # Обновить профиль
POST   /api/v1/profile/analyze     # Анализ для профиля
```

#### Файлы
```
POST   /api/v1/files/upload        # Загрузить файл
GET    /api/v1/files/{id}          # Получить файл
DELETE /api/v1/files/{id}          # Удалить файл
```

## 🗄️ База данных

### Создание миграции

```bash
# Автоматически создать миграцию
alembic revision --autogenerate -m "Add new table"

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1

# Посмотреть текущую версию
alembic current

# История миграций
alembic history
```

### Схема базы данных

Основные таблицы:
- `users` - пользователи
- `user_profiles` - профили персонализации
- `chats` - чаты
- `messages` - сообщения
- `files` - файлы
- `transactions` - транзакции

## 🧪 Тестирование

```bash
# Запустить все тесты
pytest

# С coverage
pytest --cov=app --cov-report=html

# Конкретный тест
pytest tests/test_auth.py -v
```

## 🚂 Деплой на Railway

### Вариант 1: Через Railway CLI

```bash
# Установите Railway CLI
npm i -g @railway/cli

# Войдите в аккаунт
railway login

# Инициализируйте проект
railway init

# Добавьте PostgreSQL
railway add

# Выберите PostgreSQL из списка

# Добавьте Redis
railway add
# Выберите Redis

# Установите переменные окружения
railway variables set OPENAI_API_KEY=your-key
railway variables set ANTHROPIC_API_KEY=your-key
railway variables set SECRET_KEY=your-secret
railway variables set JWT_SECRET_KEY=your-jwt-secret

# Деплой
railway up
```

### Вариант 2: Через GitHub

1. Создайте репозиторий на GitHub
2. Загрузите код:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin your-repo-url
   git push -u origin main
   ```
3. На Railway.app:
   - New Project → Deploy from GitHub
   - Выберите ваш репозиторий
   - Add PostgreSQL и Redis из маркетплейса
   - Настройте переменные окружения
   - Deploy!

### Переменные окружения на Railway

```bash
# Обязательные
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
DATABASE_URL=${{Postgres.DATABASE_URL}}  # Автоматически
REDIS_URL=${{Redis.REDIS_URL}}           # Автоматически

# LLM API ключи
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Frontend URL для CORS
CORS_ORIGINS=https://your-frontend.com,http://localhost:8888
```

### Подключение к Railway PostgreSQL

Railway автоматически предоставит переменную `DATABASE_URL`. Просто используйте её в настройках.

## 🔒 Безопасность

### Перед продакшеном:

1. **Смените все секреты** в `.env`
2. **Настройте CORS** - укажите реальный домен фронтенда
3. **Включите HTTPS** - Railway предоставляет автоматически
4. **Rate limiting** - уже встроен
5. **Валидация данных** - через Pydantic
6. **SQL injection защита** - через SQLAlchemy

### Генерация секретных ключей

```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

## 📊 Мониторинг

### Проверка здоровья

```bash
curl http://localhost:8000/health
# Response: {"status": "healthy"}
```

### Логи в Docker

```bash
docker-compose logs -f backend
```

### Логи на Railway

```bash
railway logs
```

## 🔧 Разработка

### Запуск в dev режиме

```bash
# С автоперезагрузкой
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Форматирование кода

```bash
# Установите dev зависимости
pip install black isort flake8

# Форматирование
black app/
isort app/

# Линтинг
flake8 app/
```

### Debugging

```python
# В коде добавьте breakpoint
import pdb; pdb.set_trace()

# Или используйте IDE debugger (VS Code, PyCharm)
```

## 🌍 Переменные окружения

Полный список см. в `.env.example`

Основные:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - Application secret
- `JWT_SECRET_KEY` - JWT signing key
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic (Claude) API key
- `GOOGLE_API_KEY` - Google (Gemini) API key
- `CORS_ORIGINS` - Allowed origins (frontend URLs)

## 📦 Зависимости

### Основные

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy` - ORM
- `alembic` - Migrations
- `psycopg2-binary` - PostgreSQL driver
- `redis` - Redis client

### LLM

- `openai` - OpenAI SDK
- `anthropic` - Anthropic SDK
- `google-generativeai` - Google AI SDK
- `langchain` - LLM orchestration

### Утилиты

- `python-jose` - JWT
- `passlib` - Password hashing
- `pydantic` - Data validation
- `aiofiles` - Async file operations

## 🐛 Troubleshooting

### База данных не подключается

```bash
# Проверьте, что PostgreSQL запущен
docker-compose ps

# Проверьте подключение
docker-compose exec postgres psql -U aichat_user -d aichat

# Пересоздайте контейнеры
docker-compose down -v
docker-compose up -d
```

### Ошибка миграций

```bash
# Сбросьте БД и примените миграции заново
alembic downgrade base
alembic upgrade head
```

### OpenAI API ошибка

- Проверьте, что `OPENAI_API_KEY` установлен корректно
- Убедитесь, что у вас есть баланс на OpenAI аккаунте
- Проверьте rate limits

## 📚 Дополнительные ресурсы

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [OpenAI API](https://platform.openai.com/docs)
- [Anthropic API](https://docs.anthropic.com/)
- [Railway Docs](https://docs.railway.app/)

## 🤝 Contributing

1. Fork репозиторий
2. Создайте ветку: `git checkout -b feature/amazing-feature`
3. Commit: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Создайте Pull Request

## 📝 Лицензия

MIT License

## 📧 Контакты

Для вопросов: support@example.com

---

**Разработано с ❤️ для AI Chat Platform**
