"""
Тест подключения к apinet.cloud API
"""
import asyncio
import httpx
from openai import AsyncOpenAI

async def test_apinet():
    api_key = "sk-xuMYv6qrZrvab5SmGVhMd7uOIzOpAYBPRh37IMA2wONHJyVS"
    base_url = "https://apinet.cloud/v1"
    
    print(f"🔍 Тестирование подключения к apinet.cloud")
    print(f"   API ключ: {api_key[:20]}...")
    print(f"   Base URL: {base_url}")
    print()
    
    try:
        # Тест 1: Проверка HTTP подключения
        print("1️⃣ Проверка базового HTTP подключения...")
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            resp = await client.get(f"{base_url}/models")
            print(f"   ✅ HTTP 200: Статус {resp.status_code}")
            print(f"   Ответ: {resp.text[:200]}")
    except Exception as e:
        print(f"   ❌ Ошибка: {type(e).__name__}: {e}")
    
    print()
    
    try:
        # Тест 2: Инициализация OpenAI клиента
        print("2️⃣ Инициализация AsyncOpenAI клиента...")
        http_client = httpx.AsyncClient(verify=False, timeout=httpx.Timeout(60.0, connect=30.0))
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client,
            timeout=60.0
        )
        print(f"   ✅ Клиент инициализирован")
    except Exception as e:
        print(f"   ❌ Ошибка: {type(e).__name__}: {e}")
        return
    
    print()
    
    try:
        # Тест 3: Простой запрос
        print("3️⃣ Отправка тестового запроса к модели gpt-4o...")
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Привет"}],
            max_tokens=10,
            temperature=0.7,
            timeout=60.0
        )
        print(f"   ✅ Ответ получен: {response.choices[0].message.content}")
    except Exception as e:
        print(f"   ❌ Ошибка: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    print("✅ Все тесты пройдены успешно!")

if __name__ == "__main__":
    asyncio.run(test_apinet())
