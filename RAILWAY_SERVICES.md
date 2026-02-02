# 🚂 Railway - Необходимые сервисы

## 📦 Что нужно создать на Railway

### 1. PostgreSQL (обязательно)

**Зачем:** Основная база данных для хранения пользователей, чатов, сообщений.

**Как добавить:**
1. В проекте Railway → "+ New"
2. Database → PostgreSQL
3. Дождаться создания (1-2 минуты)

**Что получите:**
- `DATABASE_URL` - автоматическая переменная
- Формат: `postgresql://user:pass@host:port/db`

**Для нашего приложения:**
- Нужно изменить на: `postgresql+asyncpg://user:pass@host:port/db`
- Или добавить отдельную переменную

**Объем данных:**
- Free tier: 100MB
- Paid: от 1GB
- Рекомендую: минимум 1GB для старта

---

### 2. Redis (обязательно)

**Зачем:** 
- Кэширование данных
- Хранение сессий
- Rate limiting
- Очереди задач (Celery)

**Как добавить:**
1. В проекте Railway → "+ New"
2. Database → Redis
3. Дождаться создания

**Что получите:**
- `REDIS_URL` - автоматическая переменная
- Формат: `redis://host:port`

**Память:**
- Free tier: 100MB
- Paid: от 256MB
- Рекомендую: 256MB для старта

---

### 3. Backend App (обязательно)

**Зачем:** Основное FastAPI приложение

**Как добавить:**
1. "+ New" → GitHub Repo
2. Выберите ваш репозиторий с backend
3. Railway автоматически обнаружит Dockerfile
4. Настройте переменные окружения (см. ниже)
5. Deploy

**Ресурсы:**
- Free tier: 512MB RAM, 0.5 vCPU
- Paid: настраиваемые
- Рекомендую для старта: 1GB RAM, 1 vCPU

---

## ⚙️ Переменные окружения

### Обязательные переменные для Backend:

```bash
# Секретные ключи (сгенерируйте!)
SECRET_KEY=<сгенерируйте: python -c "import secrets; print(secrets.token_urlsafe(32))">
JWT_SECRET_KEY=<сгенерируйте: python -c "import secrets; print(secrets.token_hex(32))">

# База данных (ссылка на PostgreSQL сервис)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# ВАЖНО! Замените postgresql:// на postgresql+asyncpg://
# Или создайте отдельную переменную:
# DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db

# Redis (ссылка на Redis сервис)
REDIS_URL=${{Redis.REDIS_URL}}

# LLM API ключи (получите на сайтах провайдеров)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# CORS (URL вашего фронтенда)
CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:8888

# Окружение
APP_ENV=production
DEBUG=False
```

---

## 🔗 Связи между сервисами

### Автоматическое связывание

Railway автоматически создаёт переменные для связи сервисов:

```bash
# В Backend сервисе будут доступны:
${{Postgres.DATABASE_URL}}    # URL PostgreSQL
${{Redis.REDIS_URL}}           # URL Redis
${{Postgres.POSTGRES_HOST}}    # Host PostgreSQL
${{Postgres.POSTGRES_PORT}}    # Port PostgreSQL
```

### Использование в коде

В `.env` или Railway Variables:

```bash
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
```

Railway подставит значения автоматически!

---

## 💰 Ориентировочная стоимость

### Free Tier ($5 credit/месяц)

```
PostgreSQL:           ~$2/месяц (100MB)
Redis:                ~$1/месяц (100MB)
Backend:              ~$2/месяц (512MB RAM)
---
Итого:                ~$5/месяц (влезает в Free tier!)
```

### Рекомендуемая конфигурация ($15/месяц)

```
PostgreSQL:           $5/месяц (1GB + backup)
Redis:                $2/месяц (256MB)
Backend:              $8/месяц (1GB RAM, 1 vCPU)
---
Итого:                ~$15/месяц
```

### Production конфигурация ($50-100/месяц)

```
PostgreSQL:           $15-30/месяц (10GB + replicas)
Redis:                $5-10/месяц (1GB)
Backend:              $30-60/месяц (2GB RAM, 2 vCPU, replicas)
---
Итого:                ~$50-100/месяц
```

---

## 🔍 Проверка сервисов

### После создания на Railway

**PostgreSQL:**
```bash
# Проверить подключение
railway run psql $DATABASE_URL

# Или
docker run --rm -it postgres:15 psql $DATABASE_URL
```

**Redis:**
```bash
# Проверить подключение
railway run redis-cli -u $REDIS_URL ping
```

**Backend:**
```bash
# Health check
curl https://your-app.railway.app/health

# API docs
curl https://your-app.railway.app/docs
```

---

## 📊 Мониторинг на Railway

### Метрики

Railway показывает для каждого сервиса:
- **CPU usage** - использование процессора
- **Memory usage** - использование памяти
- **Network** - входящий/исходящий трафик
- **Disk** - использование диска (для БД)

### Алерты

Настройте уведомления:
1. Settings → Notifications
2. Webhook URL для Telegram/Slack
3. Условия срабатывания (high CPU, memory, downtime)

---

## 🔄 CI/CD Workflow

### Автоматический деплой

После push в GitHub:

```bash
git add .
git commit -m "Update feature"
git push origin main
```

Railway автоматически:
1. ✅ Обнаружит изменения
2. ✅ Соберёт Docker образ
3. ✅ Запустит тесты (если настроены)
4. ✅ Задеплоит новую версию
5. ✅ Переключит трафик (zero downtime)

---

## 🆘 Troubleshooting

### Backend не стартует

```bash
# Проверьте логи
railway logs

# Проверьте переменные
railway variables

# Запустите команду вручную
railway run python app/main.py
```

### Миграции не применяются

```bash
# Примените вручную через Railway
railway run alembic upgrade head

# Или через shell
railway shell
> alembic upgrade head
```

### База данных недоступна

```bash
# Проверьте статус PostgreSQL
railway status

# Проверьте DATABASE_URL
railway variables | grep DATABASE

# Перезапустите сервис
railway restart
```

---

## 📚 Дополнительные ресурсы

### Документация
- [Railway Docs](https://docs.railway.app/)
- [Railway CLI](https://docs.railway.app/develop/cli)
- [PostgreSQL on Railway](https://docs.railway.app/databases/postgresql)
- [Redis on Railway](https://docs.railway.app/databases/redis)

### Полезные ссылки
- [Railway Status](https://status.railway.app/)
- [Railway Discord](https://discord.gg/railway)
- [Railway Changelog](https://railway.app/changelog)

---

**Храните этот файл как справочник команд! 📌**
