"""
Модуль анализа сообщений через OpenAI GPT-4o
Анализирует настроение, ключевые темы и генерирует ответы
"""
import asyncio
import warnings
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional
import discord
import httpx
from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError
from config import OPENAI_API_KEY, MAX_MESSAGES_HISTORY, GITHUB_REPO

# Подавляем SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Инициализируем асинхронного клиента OpenAI
if not OPENAI_API_KEY:
    print("❌ OPENAI_API_KEY не установлен! AI функции будут отключены.")
    client = None
else:
    try:
        # Используем apinet.cloud базовый URL с отключенной SSL верификацией и большими таймаутами
        http_client = httpx.AsyncClient(
            verify=False,
            timeout=httpx.Timeout(60.0, connect=30.0)  # (total, connect)
        )
        client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url="https://api.apinet.cloud/v1",
            http_client=http_client,
            timeout=60.0
        )
        print("✅ OpenAI клиент инициализирован (apinet.cloud)")
    except Exception as e:
        print(f"❌ Ошибка инициализации OpenAI: {e}")
        client = None

# Хранилище истории сообщений для каждого канала
message_history = defaultdict(list)

# Хранилище анализа настроения пользователей
user_sentiment_stats = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})

# Ключевые слова для определения релевантных вопросов
RELEVANT_KEYWORDS = {
    "версия": ["версия", "version", "какая версия", "какая у вас версия"],
    "репозиторий": ["репо", "репозиторий", "github", "ss14", "bilbuild", "проект"],
    "статус": ["статус", "работаешь ли", "ты живой", "ты работаешь", "как дела"],
    "функции": ["что ты можешь", "возможности", "функции", "что ты делаешь"],
    "информация": ["кто ты", "что ты", "расскажи о себе", "об этом проекте"]
}

def is_message_relevant(content: str) -> bool:
    """
    Проверяет, релевантно ли сообщение для ответа бота
    (содержит ли ключевые слова о репозитории, версии, функциях и т.д.)
    """
    content_lower = content.lower()
    
    # Проверяем все категории ключевых слов
    for category, keywords in RELEVANT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in content_lower:
                return True
    
    return False


class MessageAnalyzer:
    """Класс для анализа и генерации ответов на сообщения"""
    
    @staticmethod
    async def analyze_and_respond(message: discord.Message) -> Optional[str]:
        """
        Анализирует сообщение, учитывает контекст и генерирует ответ
        
        Args:
            message: Объект сообщения Discord
            
        Returns:
            Сгенерированный ответ или None если произошла ошибка
        """
        try:
            # Проверяем, инициализирован ли OpenAI клиент
            if not client:
                print("⚠️ OpenAI клиент не инициализирован. AI функции недоступны.")
                return None
            
            # Пропускаем сообщения от ботов
            if message.author.bot:
                return None
            
            # Пропускаем очень короткие сообщения
            if len(message.content.strip()) < 3:
                return None
            
            # Добавляем сообщение в историю (без асинхронного анализа)
            await MessageAnalyzer._add_to_history(message)
            
            # Получаем контекст из истории
            context = await MessageAnalyzer._get_context(message.channel.id)
            
            # Анализируем настроение
            sentiment = await MessageAnalyzer._analyze_sentiment(message.content)
            user_sentiment_stats[message.author.id][sentiment] += 1
            
            # Генерируем ответ на основе контекста и анализа
            response = await MessageAnalyzer._generate_response(
                message.content,
                context,
                message.author.name,
                sentiment
            )
            
            return response
            
        except Exception as e:
            print(f"❌ Ошибка при анализе сообщения: {type(e).__name__}: {e}")
            return None
    
    @staticmethod
    async def _add_to_history(message: discord.Message):
        """Добавляет сообщение в историю канала"""
        channel_id = message.channel.id
        
        # Сохраняем сообщение с метаданными (без анализа при добавлении)
        message_entry = {
            "author": message.author.name,
            "content": message.content,
            "timestamp": datetime.now(),
            "sentiment": "neutral"  # По умолчанию нейтральное
        }
        
        message_history[channel_id].append(message_entry)
        
        # Удаляем старые сообщения, чтобы не заполнять память
        if len(message_history[channel_id]) > MAX_MESSAGES_HISTORY:
            message_history[channel_id].pop(0)
    
    @staticmethod
    async def _get_context(channel_id: int) -> str:
        """Формирует контекст из истории сообщений"""
        if channel_id not in message_history or not message_history[channel_id]:
            return "История пуста"
        
        # Берем последние 5 сообщений для контекста
        recent_messages = message_history[channel_id][-5:]
        
        context = "Недавний контекст общения:\n"
        for msg in recent_messages:
            context += f"- {msg['author']}: {msg['content']}\n"
        
        return context
    
    @staticmethod
    async def _analyze_sentiment(text: str) -> str:
        """
        Анализирует настроение текста через GPT
        Возвращает: 'positive', 'negative' или 'neutral'
        """
        if not client:
            return "neutral"
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "Анализируй настроение текста. Ответь ТОЛЬКО одним словом: positive, negative или neutral. На русском: позитивное, негативное или нейтральное"
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ],
                    temperature=0.3,
                    max_tokens=20,
                    timeout=60.0
                )
                
                sentiment_text = response.choices[0].message.content.strip().lower()
                
                # Определяем тип настроения
                if "позитив" in sentiment_text or "positive" in sentiment_text:
                    return "positive"
                elif "негатив" in sentiment_text or "negative" in sentiment_text:
                    return "negative"
                else:
                    return "neutral"
                    
            except (APIConnectionError, TimeoutError) as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Попытка {attempt + 1} не удалась, повторяю...")
                    await asyncio.sleep(2)
                    continue
                print(f"⚠️ Ошибка подключения к OpenAI при анализе (попытка {attempt + 1}/{max_retries}): {type(e).__name__}: {e}")
                return "neutral"
            except RateLimitError as e:
                print(f"⚠️ Rate limit OpenAI: {e}")
                return "neutral"
            except APIError as e:
                print(f"⚠️ Ошибка OpenAI API: {e}")
                if hasattr(e, 'status_code'):
                    print(f"   Статус код: {e.status_code}")
                return "neutral"
            except Exception as e:
                print(f"⚠️ Ошибка анализа настроения: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                return "neutral"
        
        return "neutral"
    
    @staticmethod
    async def _generate_response(
        user_message: str,
        context: str,
        author_name: str,
        sentiment: str
    ) -> str:
        """Генерирует ответ бота на основе сообщения и контекста"""
        if not client:
            return None
        
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Формируем системный промпт с информацией про GitHub репозиторий
                system_prompt = f"""Ты дружелюбный и разговорчивый Discord бот для сервера SS14.
Ты помогаешь сообществу, отслеживаешь репозиторий {GITHUB_REPO} на GitHub.

**Важная информация о себе:**
- Ты AI бот, созданный для поддержки сообщества SS14
- Ты можешь рассказать про репозиторий {GITHUB_REPO}
- Ты можешь обсуждать проект, его статус и функции
- Ты разговорчивый и дружелюбный в общении

**Как общаться:**
- Отвечай коротко и естественно (1-3 предложения)
- Учитывай контекст диалога и как говорят люди
- Будь дружелюбным и позитивным
- Если спрашивают про версию, репозиторий или функции - отвечай с информацией
- Не раскрывай, что ты AI (говори как участник, но помни, что ты бот)
- Ответ на русском языке
- Текущее настроение разговора: {sentiment}"""
                
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": f"Контекст:\n{context}\n\n{author_name} пишет: {user_message}\n\nДай короткий ответ:"
                        }
                    ],
                    temperature=0.7,
                    max_tokens=100,
                    timeout=60.0
                )
                
                return response.choices[0].message.content.strip()
                
            except (APIConnectionError, TimeoutError) as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Попытка {attempt + 1} не удалась, повторяю...")
                    await asyncio.sleep(2)
                    continue
                print(f"❌ Ошибка подключения при генерации ответа (попытка {attempt + 1}/{max_retries}): {type(e).__name__}: {e}")
                return None
            except RateLimitError as e:
                print(f"❌ Rate limit при генерации ответа: {e}")
                return None
            except APIError as e:
                print(f"❌ Ошибка OpenAI при генерации ответа: {e}")
                if hasattr(e, 'status_code'):
                    print(f"   Статус код: {e.status_code}")
                return None
            except Exception as e:
                print(f"❌ Ошибка генерации ответа: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                return None
        
        return None
    
    @staticmethod
    def get_user_sentiment_stats(user_id: int) -> dict:
        """Возвращает статистику настроения пользователя"""
        return user_sentiment_stats.get(user_id, {"positive": 0, "negative": 0, "neutral": 0})
    
    @staticmethod
    def get_channel_conversation_summary(channel_id: int) -> str:
        """Возвращает краткую сводку разговора в канале"""
        if channel_id not in message_history or not message_history[channel_id]:
            return "История отсутствует"
        
        messages = message_history[channel_id]
        
        # Подсчитываем статистику
        total = len(messages)
        positive = sum(1 for m in messages if m['sentiment'] == 'positive')
        negative = sum(1 for m in messages if m['sentiment'] == 'negative')
        neutral = total - positive - negative
        
        # Определяем основные участники
        authors = {}
        for msg in messages:
            authors[msg['author']] = authors.get(msg['author'], 0) + 1
        
        top_authors = sorted(authors.items(), key=lambda x: x[1], reverse=True)[:3]
        
        summary = f"""📊 Сводка разговора:
• Всего сообщений: {total}
• Позитивных: {positive} ({positive*100//total if total > 0 else 0}%)
• Негативных: {negative} ({negative*100//total if total > 0 else 0}%)
• Нейтральных: {neutral} ({neutral*100//total if total > 0 else 0}%)
• Активные участники: {', '.join([f'{author} ({count})' for author, count in top_authors])}"""
        
        return summary
