# 🔧 Полезные команды

## 🚀 Разработка

### Запуск

```bash
# С Docker
docker-compose up -d

# Без Docker
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# В фоне
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

### Остановка

```bash
# Docker
docker-compose down

# Убить процесс
pkill -f uvicorn
```

### Логи

```bash
# Docker
docker-compose logs -f backend

# Реальное время
tail -f app.log
```

---

## 🗄️ База данных

### Миграции

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "Description"

# Применить все миграции
alembic upgrade head

# Откатить одну миграцию
alembic downgrade -1

# Откатить все
alembic downgrade base

# Текущая версия
alembic current

# История
alembic history --verbose
```

### PostgreSQL

```bash
# Подключиться к БД
docker-compose exec postgres psql -U aichat_user -d aichat

# Создать backup
docker-compose exec postgres pg_dump -U aichat_user aichat > backup.sql

# Восстановить из backup
docker-compose exec -T postgres psql -U aichat_user aichat < backup.sql

# Список таблиц
docker-compose exec postgres psql -U aichat_user -d aichat -c "\dt"

# Очистить БД
docker-compose exec postgres psql -U aichat_user -d aichat -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

### Redis

```bash
# Подключиться к Redis
docker-compose exec redis redis-cli

# Очистить кэш
docker-compose exec redis redis-cli FLUSHALL

# Посмотреть ключи
docker-compose exec redis redis-cli KEYS "*"

# Получить значение
docker-compose exec redis redis-cli GET key_name
```

---

## 🧪 Тестирование

```bash
# Все тесты
pytest

# С выводом print()
pytest -s

# Конкретный файл
pytest tests/test_auth.py

# С coverage
pytest --cov=app --cov-report=html

# Открыть coverage отчет
open htmlcov/index.html
```

---

## 🐳 Docker

```bash
# Собрать образ
docker build -t ai-chat-backend .

# Запустить контейнер
docker run -p 8000:8000 --env-file .env ai-chat-backend

# Посмотреть запущенные контейнеры
docker-compose ps

# Остановить всё
docker-compose down

# Удалить volumes
docker-compose down -v

# Пересобрать
docker-compose build --no-cache

# Рестарт сервиса
docker-compose restart backend

# Логи
docker-compose logs -f backend

# Shell в контейнере
docker-compose exec backend bash
```

---

## 🚂 Railway

```bash
# Установка CLI
npm i -g @railway/cli

# Логин
railway login

# Инициализация
railway init

# Связать с проектом
railway link

# Деплой
railway up

# Логи
railway logs

# Переменные
railway variables

# Открыть в браузере
railway open

# Запустить команду
railway run alembic upgrade head

# Shell
railway shell

# Статус
railway status
```

---

## 🔐 Безопасность

### Генерация ключей

```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Random password
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

### Проверка безопасности

```bash
# Проверка зависимостей
pip install safety
safety check

# Проверка кода
bandit -r app/
```

---

## 📦 Управление зависимостями

```bash
# Установить все
pip install -r requirements.txt

# Добавить новую
pip install package_name
pip freeze > requirements.txt

# Обновить все
pip install --upgrade -r requirements.txt

# Показать устаревшие
pip list --outdated
```

---

## 🔍 Debugging

```bash
# Запуск с debugging
python -m debugpy --listen 0.0.0.0:5678 -m uvicorn app.main:app --reload

# Проверить импорты
python -c "from app.main import app; print('OK')"

# Python shell с контекстом приложения
python -i -c "from app.main import *"
```

---

## 📊 Мониторинг

```bash
# Показать активные подключения к БД
docker-compose exec postgres psql -U aichat_user -d aichat -c "SELECT * FROM pg_stat_activity;"

# Redis info
docker-compose exec redis redis-cli INFO

# Размер БД
docker-compose exec postgres psql -U aichat_user -d aichat -c "SELECT pg_size_pretty(pg_database_size('aichat'));"

# Количество записей в таблице
docker-compose exec postgres psql -U aichat_user -d aichat -c "SELECT COUNT(*) FROM users;"
```

---

## 🧹 Очистка

```bash
# Удалить __pycache__
find . -type d -name __pycache__ -exec rm -r {} +

# Удалить .pyc файлы
find . -type f -name "*.pyc" -delete

# Очистить uploads
rm -rf uploads/*

# Очистить логи
rm -f *.log
```

---

## 🎯 Полезные API запросы

### Регистрация
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
```

### Логин
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
```

### Получить профиль
```bash
curl http://localhost:8000/api/v1/profile \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Создать чат
```bash
curl -X POST http://localhost:8000/api/v1/chats \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Chat"}'
```

### Отправить сообщение
```bash
curl -X POST http://localhost:8000/api/v1/llm/chat/CHAT_ID/message \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Привет!",
    "model": "gpt-3.5-turbo"
  }'
```

### Список моделей
```bash
curl http://localhost:8000/api/v1/llm/models
```

---

## 📝 Шпаргалка

```bash
# Быстрый старт
docker-compose up -d && docker-compose logs -f

# Пересоздать БД
docker-compose down -v && docker-compose up -d

# Миграции
alembic upgrade head

# Тесты
pytest -v

# Деплой на Railway
git push && railway up

# Проверка
curl http://localhost:8000/health
```

---

**Сохраните этот файл для быстрого доступа к командам! 📌**
