# 🚀 START HERE - Backend Setup

## 🎯 Быстрый старт за 3 шага

### Шаг 1: Локальное тестирование (5 минут)

```bash
cd ai-chat-backend

# Установка
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настройка
cp .env.example .env
# Отредактируйте .env

# Запуск
docker-compose up -d

# Проверка
curl http://localhost:8000/health
open http://localhost:8000/docs
```

✅ Backend работает локально!

---

### Шаг 2: Деплой на Railway (10 минут)

```bash
# 1. Загрузите на GitHub
git init
git add .
git commit -m "Backend ready"
git push origin main

# 2. На Railway.app:
#    - New Project
#    - Add PostgreSQL
#    - Add Redis  
#    - Deploy from GitHub
#    - Configure variables
#    - Deploy!

# 3. Проверьте
curl https://your-app.railway.app/health
```

✅ Backend работает на Railway!

---

### Шаг 3: Подключите Frontend (5 минут)

```javascript
// В js/app.js добавьте:
const API_URL = 'https://your-app.railway.app/api/v1';

// Замените mock функции на реальные API вызовы
// (см. FRONTEND_INTEGRATION.md)
```

✅ Frontend подключён к Backend!

---

## 📚 Документация

| Документ | Для чего |
|----------|----------|
| `README.md` | Полная документация |
| `QUICKSTART.md` | Быстрый старт |
| `RAILWAY_DEPLOY.md` | Деплой на Railway |
| `RAILWAY_SERVICES.md` | Необходимые сервисы |
| `FRONTEND_INTEGRATION.md` | Подключение фронтенда |
| `COMMANDS.md` | Справочник команд |
| `BACKEND_SUMMARY.md` | Обзор backend |

---

## 🚂 Что нужно на Railway

### 3 сервиса:

1. **PostgreSQL** (~$5/мес)
   - Database → PostgreSQL
   - 1GB памяти

2. **Redis** (~$2/мес)
   - Database → Redis
   - 256MB памяти

3. **Backend** (~$8/мес)
   - GitHub Repo → ваш backend
   - 1GB RAM, 1 vCPU

**Итого:** ~$15/мес (или FREE tier для теста)

---

## 🔑 API ключи (получите перед деплоем)

- **OpenAI**: https://platform.openai.com/
- **Anthropic**: https://console.anthropic.com/
- **Google AI**: https://makersuite.google.com/

---

## ✨ Что уже работает

- ✅ JWT аутентификация
- ✅ CRUD для чатов
- ✅ Интеграция с OpenAI, Claude, Gemini
- ✅ Streaming ответов
- ✅ Система профилирования
- ✅ Загрузка файлов
- ✅ Подсчёт токенов и стоимости
- ✅ Swagger UI документация

---

## 🎯 Следующие шаги

1. **Локально протестируйте** - `make docker-up`
2. **Получите API ключи** - OpenAI, Anthropic
3. **Деплой на Railway** - следуйте RAILWAY_DEPLOY.md
4. **Подключите фронтенд** - следуйте FRONTEND_INTEGRATION.md

---

**Начинайте с `make docker-up` и `open http://localhost:8000/docs`! 🚀**
