# 🔗 Интеграция Frontend с Backend

Как подключить фронтенд AI Chat Platform к FastAPI backend.

---

## 📝 Изменения в Frontend

### 1. Добавьте API конфигурацию

В начало `js/app.js`:

```javascript
// API Configuration
const API_CONFIG = {
    baseURL: 'https://your-backend.railway.app/api/v1',
    // Для локальной разработки:
    // baseURL: 'http://localhost:8000/api/v1',
};

// Auth state
let authToken = localStorage.getItem('authToken');
let currentUser = JSON.parse(localStorage.getItem('currentUser') || 'null');
```

### 2. Создайте API helper функции

```javascript
// API Helper
async function apiRequest(endpoint, options = {}) {
    const url = `${API_CONFIG.baseURL}${endpoint}`;
    
    const config = {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    };
    
    // Add auth token if available
    if (authToken && !options.skipAuth) {
        config.headers['Authorization'] = `Bearer ${authToken}`;
    }
    
    try {
        const response = await fetch(url, config);
        
        // Handle 401 Unauthorized
        if (response.status === 401) {
            logout();
            throw new Error('Unauthorized. Please login again.');
        }
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API Error');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Request failed:', error);
        throw error;
    }
}
```

### 3. Реализуйте Auth функции

```javascript
// Authentication
async function register(email, password) {
    const data = await apiRequest('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
        skipAuth: true,
    });
    
    // Save tokens
    authToken = data.access_token;
    localStorage.setItem('authToken', authToken);
    localStorage.setItem('refreshToken', data.refresh_token);
    localStorage.setItem('currentUser', JSON.stringify(data.user));
    currentUser = data.user;
    
    // Update UI
    AppState.user.balance = data.user.balance;
    updateBalance();
    
    return data;
}

async function login(email, password) {
    const data = await apiRequest('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
        skipAuth: true,
    });
    
    authToken = data.access_token;
    localStorage.setItem('authToken', authToken);
    localStorage.setItem('refreshToken', data.refresh_token);
    localStorage.setItem('currentUser', JSON.stringify(data.user));
    currentUser = data.user;
    
    AppState.user.balance = data.user.balance;
    updateBalance();
    
    return data;
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('currentUser');
    
    // Redirect to login page or show login modal
    showLoginModal();
}

async function getCurrentUser() {
    const data = await apiRequest('/auth/me');
    currentUser = data;
    localStorage.setItem('currentUser', JSON.stringify(data));
    AppState.user.balance = data.balance;
    updateBalance();
    return data;
}
```

### 4. Замените mock Chat API

```javascript
// Create Chat
async function createChatAPI(title = "Новый чат") {
    return await apiRequest('/chats', {
        method: 'POST',
        body: JSON.stringify({ title }),
    });
}

// Get user's chats
async function getUserChats() {
    return await apiRequest('/chats');
}

// Get specific chat with messages
async function getChatWithMessages(chatId) {
    return await apiRequest(`/chats/${chatId}`);
}

// Update chat
async function updateChatAPI(chatId, updates) {
    return await apiRequest(`/chats/${chatId}`, {
        method: 'PATCH',
        body: JSON.stringify(updates),
    });
}

// Delete chat
async function deleteChatAPI(chatId) {
    await apiRequest(`/chats/${chatId}`, {
        method: 'DELETE',
    });
}
```

### 5. Интегрируйте LLM API

```javascript
// Send message (non-streaming)
async function sendMessage(chatId, content, model) {
    return await apiRequest(`/llm/chat/${chatId}/message`, {
        method: 'POST',
        body: JSON.stringify({
            content: content,
            model: model,
            attachments: AppState.attachments,
        }),
    });
}

// Send message with streaming
async function sendMessageStream(chatId, content, model) {
    const url = `${API_CONFIG.baseURL}/llm/chat/${chatId}/message/stream`;
    
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({
            content: content,
            model: model,
            attachments: AppState.attachments,
        }),
    });
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    let assistantMessage = '';
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = JSON.parse(line.slice(6));
                
                if (data.type === 'content') {
                    assistantMessage += data.content;
                    // Update UI with new content
                    updateStreamingMessage(assistantMessage);
                } else if (data.type === 'end') {
                    // Streaming complete
                    return {
                        content: assistantMessage,
                        tokens: data.tokens,
                        cost: data.cost,
                        message_id: data.message_id,
                    };
                } else if (data.type === 'error') {
                    throw new Error(data.error);
                }
            }
        }
    }
}

// Get available models
async function getAvailableModels() {
    const data = await apiRequest('/llm/models');
    return data.models;
}
```

### 6. Обновите Profile API

```javascript
// Get profile
async function getProfile() {
    return await apiRequest('/profile');
}

// Update profile
async function updateProfile(profileData) {
    return await apiRequest('/profile', {
        method: 'PUT',
        body: JSON.stringify(profileData),
    });
}
```

### 7. Загрузка файлов

```javascript
// Upload file
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_CONFIG.baseURL}/files/upload`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${authToken}`,
        },
        body: formData,
    });
    
    if (!response.ok) {
        throw new Error('File upload failed');
    }
    
    return await response.json();
}
```

---

## 🔐 Добавьте Login/Register UI

### HTML для модального окна

```html
<!-- Auth Modal -->
<div class="modal" id="authModal" style="display: none;">
    <div class="modal-overlay"></div>
    <div class="modal-content">
        <div class="modal-header">
            <h3 id="authModalTitle">Вход</h3>
            <button class="modal-close" onclick="closeAuthModal()">✕</button>
        </div>
        <div class="modal-body">
            <div id="loginForm">
                <input type="email" id="loginEmail" placeholder="Email">
                <input type="password" id="loginPassword" placeholder="Пароль">
                <button onclick="handleLogin()">Войти</button>
                <a href="#" onclick="switchToRegister()">Нет аккаунта? Регистрация</a>
            </div>
            
            <div id="registerForm" style="display: none;">
                <input type="email" id="registerEmail" placeholder="Email">
                <input type="password" id="registerPassword" placeholder="Пароль">
                <input type="password" id="registerPasswordConfirm" placeholder="Подтвердите пароль">
                <button onclick="handleRegister()">Зарегистрироваться</button>
                <a href="#" onclick="switchToLogin()">Уже есть аккаунт? Вход</a>
            </div>
        </div>
    </div>
</div>
```

### JavaScript обработчики

```javascript
async function handleLogin() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        await login(email, password);
        closeAuthModal();
        showNotification('Вход выполнен успешно!', 'success');
        loadUserData();
    } catch (error) {
        showNotification('Ошибка входа: ' + error.message, 'error');
    }
}

async function handleRegister() {
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    const passwordConfirm = document.getElementById('registerPasswordConfirm').value;
    
    if (password !== passwordConfirm) {
        showNotification('Пароли не совпадают', 'error');
        return;
    }
    
    try {
        await register(email, password);
        closeAuthModal();
        showNotification('Регистрация успешна!', 'success');
        loadUserData();
    } catch (error) {
        showNotification('Ошибка регистрации: ' + error.message, 'error');
    }
}

// Load user data after login
async function loadUserData() {
    try {
        // Get user info
        const user = await getCurrentUser();
        
        // Get profile
        const profile = await getProfile();
        AppState.user.profile = profile;
        
        // Get chats
        const chats = await getUserChats();
        AppState.chats = chats;
        renderChatList();
        
    } catch (error) {
        console.error('Failed to load user data:', error);
    }
}
```

---

## 🌊 Streaming Implementation

### Полная реализация streaming

```javascript
async function sendMessageWithStreaming(chatId, content, model) {
    // Show typing indicator
    addTypingIndicator();
    
    try {
        const response = await sendMessageStream(chatId, content, model);
        
        // Remove typing indicator
        removeTypingIndicator();
        
        // Add complete message to UI
        const chat = AppState.chats.find(c => c.id === chatId);
        const assistantMessage = {
            role: 'assistant',
            model: model,
            content: response.content,
            timestamp: new Date(),
            tokens: response.tokens,
            cost: response.cost,
        };
        
        chat.messages.push(assistantMessage);
        
        // Update balance
        AppState.user.balance -= response.cost;
        updateBalance();
        
    } catch (error) {
        removeTypingIndicator();
        showNotification('Ошибка: ' + error.message, 'error');
    }
}

function updateStreamingMessage(content) {
    let streamingMsg = document.getElementById('streamingMessage');
    
    if (!streamingMsg) {
        // Create streaming message element
        const container = document.getElementById('messagesContainer');
        removeTypingIndicator();
        
        streamingMsg = createMessageElement({
            role: 'assistant',
            content: content,
            model: AppState.currentModel,
            timestamp: new Date(),
        });
        streamingMsg.id = 'streamingMessage';
        container.appendChild(streamingMsg);
    } else {
        // Update content
        const body = streamingMsg.querySelector('.message-body');
        body.innerHTML = marked.parse(content);
    }
    
    // Auto-scroll
    const container = document.getElementById('messagesContainer');
    container.scrollTop = container.scrollHeight;
}
```

---

## 🧪 Тестирование интеграции

### Checklist

- [ ] Регистрация работает
- [ ] Логин работает
- [ ] Токен сохраняется
- [ ] Создание чата работает
- [ ] Отправка сообщения работает
- [ ] Получен ответ от LLM
- [ ] Баланс обновляется
- [ ] Профиль загружается
- [ ] Файлы загружаются
- [ ] Выход работает

### Тестовый сценарий

```javascript
// 1. Регистрация
await register('test@example.com', 'password123');
// ✅ Должен получить токен

// 2. Создать чат
const chat = await createChatAPI('Test Chat');
// ✅ Должен получить chat.id

// 3. Отправить сообщение
const response = await sendMessage(chat.id, 'Привет!', 'gpt-3.5-turbo');
// ✅ Должен получить ответ от GPT

// 4. Проверить баланс
await getCurrentUser();
// ✅ Баланс должен уменьшиться
```

---

## 🔄 Обновление существующего кода

### Замените в `sendMessage()`:

**Было (mock):**
```javascript
const response = await simulateAIResponse(content, AppState.currentModel);
```

**Стало (real API):**
```javascript
const response = await sendMessage(
    AppState.currentChatId, 
    content, 
    AppState.currentModel
);
```

### Обновите `createNewChat()`:

**Было:**
```javascript
const chatId = `chat_${Date.now()}`;
const newChat = {
    id: chatId,
    title: 'Новый чат',
    messages: [],
    // ...
};
AppState.chats.unshift(newChat);
```

**Стало:**
```javascript
const newChat = await createChatAPI('Новый чат');
AppState.chats.unshift(newChat);
AppState.currentChatId = newChat.id;
```

### Обновите `loadSampleChats()`:

```javascript
async function loadUserChats() {
    try {
        const chats = await getUserChats();
        AppState.chats = chats;
        renderChatList();
    } catch (error) {
        console.error('Failed to load chats:', error);
        showNotification('Не удалось загрузить чаты', 'error');
    }
}
```

---

## 🎨 Добавьте Login UI

### Простой вариант (модальное окно)

```javascript
function showLoginModal() {
    // Create and show login modal
    const modal = document.createElement('div');
    modal.className = 'auth-modal';
    modal.innerHTML = `
        <div class="auth-content">
            <h2>Вход в AI Chat Platform</h2>
            <input type="email" id="authEmail" placeholder="Email">
            <input type="password" id="authPassword" placeholder="Пароль">
            <button onclick="handleQuickLogin()">Войти</button>
            <button onclick="handleQuickRegister()">Регистрация</button>
        </div>
    `;
    document.body.appendChild(modal);
}

async function handleQuickLogin() {
    const email = document.getElementById('authEmail').value;
    const password = document.getElementById('authPassword').value;
    
    try {
        await login(email, password);
        document.querySelector('.auth-modal').remove();
        await loadUserData();
    } catch (error) {
        alert('Ошибка входа: ' + error.message);
    }
}
```

---

## 🌐 Environment-based configuration

### Для разных окружений

```javascript
// Определение окружения
const ENV = {
    API_URL: window.location.hostname === 'localhost' 
        ? 'http://localhost:8000/api/v1'
        : 'https://your-backend.railway.app/api/v1'
};

// Использование
const response = await fetch(`${ENV.API_URL}/chats`);
```

---

## 📊 Обработка ошибок

### Global error handler

```javascript
async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_CONFIG.baseURL}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...(authToken && { 'Authorization': `Bearer ${authToken}` }),
                ...options.headers,
            },
        });
        
        if (!response.ok) {
            const error = await response.json();
            
            // Handle specific errors
            switch (response.status) {
                case 401:
                    logout();
                    showNotification('Сессия истекла. Войдите снова.', 'error');
                    break;
                case 402:
                    showNotification('Недостаточно средств. Пополните баланс.', 'warning');
                    break;
                case 429:
                    showNotification('Слишком много запросов. Подождите немного.', 'warning');
                    break;
                default:
                    showNotification(error.detail || 'Ошибка сервера', 'error');
            }
            
            throw new Error(error.detail);
        }
        
        return await response.json();
        
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}
```

---

## 🔄 Полный пример интеграции

### Обновлённый `sendMessage()`:

```javascript
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const content = input.value.trim();
    
    if (!content && AppState.attachments.length === 0) return;
    
    // Check if user is logged in
    if (!authToken) {
        showLoginModal();
        return;
    }
    
    // Get or create current chat
    let chatId = AppState.currentChatId;
    
    if (!chatId) {
        try {
            const newChat = await createChatAPI();
            chatId = newChat.id;
            AppState.currentChatId = chatId;
            AppState.chats.unshift(newChat);
            renderChatList();
            showChat(chatId);
        } catch (error) {
            showNotification('Не удалось создать чат', 'error');
            return;
        }
    }
    
    // Add user message to UI immediately
    const userMessage = {
        role: 'user',
        content: content,
        timestamp: new Date(),
        attachments: [...AppState.attachments]
    };
    
    const container = document.getElementById('messagesContainer');
    container.appendChild(createMessageElement(userMessage));
    container.scrollTop = container.scrollHeight;
    
    // Clear input
    input.value = '';
    AppState.attachments = [];
    document.getElementById('attachmentPreview').style.display = 'none';
    updateSendButton();
    
    // Show typing indicator
    addTypingIndicator();
    
    try {
        // Send to backend with streaming
        await sendMessageWithStreaming(chatId, content, AppState.currentModel);
        
        // Reload chat to get updated data
        await loadChatMessages(chatId);
        
    } catch (error) {
        removeTypingIndicator();
        showNotification('Ошибка: ' + error.message, 'error');
    }
}

async function sendMessageWithStreaming(chatId, content, model) {
    const url = `${API_CONFIG.baseURL}/llm/chat/${chatId}/message/stream`;
    
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({ content, model }),
    });
    
    if (!response.ok) {
        throw new Error('API Error');
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let assistantContent = '';
    
    removeTypingIndicator();
    
    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = JSON.parse(line.slice(6));
                
                if (data.type === 'content') {
                    assistantContent += data.content;
                    updateStreamingMessage(assistantContent);
                } else if (data.type === 'end') {
                    // Update balance
                    AppState.user.balance -= data.cost;
                    updateBalance();
                }
            }
        }
    }
}
```

---

## 🎯 Инициализация при загрузке

### Обновите `initializeApp()`:

```javascript
async function initializeApp() {
    // Configure marked.js...
    // (existing code)
    
    // Check if user is logged in
    if (authToken) {
        try {
            // Load user data
            await getCurrentUser();
            await getProfile();
            await loadUserChats();
            
            // Load available models from backend
            const modelsData = await getAvailableModels();
            AppState.models = modelsData;
            
        } catch (error) {
            console.error('Failed to load user data:', error);
            // Token might be expired
            logout();
        }
    } else {
        // Show login modal or welcome screen
        showLoginModal();
    }
}
```

---

## ✅ Чеклист интеграции

### Frontend изменения:

- [ ] Добавить API_CONFIG с URL backend
- [ ] Создать apiRequest() helper
- [ ] Реализовать register()
- [ ] Реализовать login()
- [ ] Реализовать logout()
- [ ] Обновить sendMessage() для использования API
- [ ] Добавить streaming support
- [ ] Обновить loadChats()
- [ ] Обновить profile functions
- [ ] Добавить Login/Register UI
- [ ] Обработка ошибок
- [ ] Тестирование

### Backend готовность:

- [✅] API endpoints работают
- [ ] Задеплоено на Railway
- [ ] PostgreSQL подключен
- [ ] Redis подключен
- [ ] API ключи настроены
- [ ] CORS настроен для фронтенда
- [ ] Health check проходит

---

## 🎉 Результат

После интеграции:
- ✅ Реальная регистрация/авторизация
- ✅ Сохранение чатов в БД
- ✅ Настоящие ответы от GPT/Claude/Gemini
- ✅ Персонализация на основе профиля
- ✅ Реальный подсчёт стоимости
- ✅ Синхронизация между устройствами

---

**Следуйте инструкциям и интеграция пройдёт гладко! 🚀**
