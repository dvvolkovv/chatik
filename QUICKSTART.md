# ⚡ Backend Quick Start

## 🚀 Локальный запуск (5 минут)

### 1. Установка

```bash
cd ai-chat-backend

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Зависимости
pip install -r requirements.txt
```

### 2. Настройка

```bash
# Скопируйте .env
cp .env.example .env

# Отредактируйте .env
nano .env  # или любой редактор
```

**Минимальные настройки:**
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/aichat
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-key
OPENAI_API_KEY=sk-...
```

### 3. Запуск с Docker (рекомендуется)

```bash
# Запустить всё
docker-compose up -d

# Проверить
curl http://localhost:8000/health
```

Готово! API на http://localhost:8000

### 4. Или запуск без Docker

```bash
# PostgreSQL и Redis должны быть запущены отдельно

# Миграции
alembic upgrade head

# Запуск
uvicorn app.main:app --reload
```

---

## 🧪 Тестирование API

### Swagger UI
```
http://localhost:8000/docs
```

### Примеры запросов

**Регистрация:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

**Логин:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

**Создать чат:**
```bash
curl -X POST http://localhost:8000/api/v1/chats \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "title": "Мой первый чат"
  }'
```

---

## 🚂 Деплой на Railway

### Способ 1: Через GitHub

```bash
# 1. Загрузите код на GitHub
git push origin main

# 2. На Railway:
# - New Project → Deploy from GitHub
# - Выберите репозиторий
# - Добавьте PostgreSQL и Redis
# - Настройте переменные
# - Deploy!
```

### Способ 2: Railway CLI

```bash
# Установите CLI
npm i -g @railway/cli

# Войдите
railway login

# Создайте проект
railway init

# Деплой
railway up
```

Подробнее: см. `RAILWAY_DEPLOY.md`

---

## 📚 Документация

- `README.md` - основная документация
- `RAILWAY_DEPLOY.md` - подробная инструкция по деплою
- `/docs` - Swagger UI (после запуска)

---

## 🆘 Проблемы?

### Не запускается
```bash
# Проверьте зависимости
pip list

# Проверьте .env
cat .env

# Логи
docker-compose logs backend
```

### База не подключается
```bash
# Проверьте PostgreSQL
docker-compose ps postgres

# Подключитесь вручную
docker-compose exec postgres psql -U aichat_user -d aichat
```

---

**Готово! Начинайте разработку! 🎉**
