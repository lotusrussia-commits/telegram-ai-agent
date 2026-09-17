import inspect
import json
import logging
from pathlib import Path

from app.llm import client
from app.config import LLM_MODEL
from app.tools import (
    calculate,
    get_currency_rate,
    get_crypto_price,
    get_weather,
    read_file,
    web_search,
    write_file,
)

MEMORY_FILE = Path("memory.json")
LOG_FILE = Path("agent.log")
MAX_HISTORY_MESSAGES = 20


logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
)

logger = logging.getLogger(__name__)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Ищет информацию в интернете через DuckDuckGo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Максимальное количество результатов.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Получает текущую погоду в указанном городе.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Название города.",
                    }
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto_price",
            "description": "Получает текущую цену криптовалюты.",
            "parameters": {
                "type": "object",
                "properties": {
                    "cryptocurrency": {
                        "type": "string",
                        "description": "Название или тикер криптовалюты, например BTC или ETH.",
                    },
                    "currency": {
                        "type": "string",
                        "description": "Валюта цены, например USD или EUR.",
                    },
                },
                "required": ["cryptocurrency"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Читает текстовый файл из папки агента.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Имя файла.",
                    }
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Записывает текст в файл в папке агента.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Имя файла.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Текст для записи.",
                    },
                },
                "required": ["filename", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_currency_rate",
            "description": "Получает текущий курс одной обычной валюты к другой.",
            "parameters": {
                "type": "object",
                "properties": {
                    "base_currency": {
                        "type": "string",
                        "description": "Исходная валюта, например EUR.",
                    },
                    "target_currency": {
                        "type": "string",
                        "description": "Целевая валюта, например USD.",
                    },
                },
                "required": ["base_currency", "target_currency"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Вычисляет математическое выражение.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Математическое выражение.",
                    }
                },
                "required": ["expression"],
            },
        },
    },
]


TOOL_FUNCTIONS = {
    "web_search": web_search,
    "get_weather": get_weather,
    "get_crypto_price": get_crypto_price,
    "read_file": read_file,
    "write_file": write_file,
    "get_currency_rate": get_currency_rate,
    "calculate": calculate,
}


def load_memory() -> list[dict]:
    if not MEMORY_FILE.exists():
        return []

    try:
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass

    return []


def save_memory(messages: list[dict]) -> None:
    MEMORY_FILE.write_text(
        json.dumps(messages, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def execute_tool(name: str, arguments: dict) -> str:
    function = TOOL_FUNCTIONS.get(name)

    if function is None:
        logger.error("Инструмент не найден: %s", name)
        return f"Инструмент «{name}» не найден."

    logger.info("Вызов инструмента: %s | аргументы: %s", name, arguments)

    try:
        result = function(**arguments)

        if inspect.isawaitable(result):
            result = await result

        result = str(result)

        logger.info("Инструмент завершён: %s | результат: %s", name, result)

        return result

    except Exception as error:
        logger.exception("Ошибка инструмента: %s", name)
        return f"Ошибка инструмента {name}: {error}"


async def run_agent(user_message: str) -> str:
    logger.info("Новый запрос пользователя: %s", user_message)

    history = load_memory()

    messages = [
        {
            "role": "system",
            "content": (
                "Ты полезный AI-агент. "
                "Ты можешь использовать инструменты для поиска информации "
                "в интернете, получения погоды, криптовалютных и обычных "
                "валютных курсов, чтения и записи файлов и вычислений. "
                "Используй инструменты, когда они нужны для точного ответа. "
                "Не выдумывай результаты инструментов."
            ),
        }
    ]

    messages.extend(history[-MAX_HISTORY_MESSAGES:])
    messages.append({"role": "user", "content": user_message})

    while True:
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message

        assistant_dict = {
            "role": "assistant",
            "content": assistant_message.content or "",
        }

        if assistant_message.tool_calls:
            assistant_dict["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in assistant_message.tool_calls
            ]

        messages.append(assistant_dict)

        if not assistant_message.tool_calls:
            answer = assistant_message.content or "Не удалось получить ответ."

            history.extend(
                [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": answer},
                ]
            )
            save_memory(history[-MAX_HISTORY_MESSAGES:])

            logger.info("Запрос завершён: %s", answer)

            return answer

        for tool_call in assistant_message.tool_calls:
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                arguments = {}
                logger.error(
                    "Не удалось разобрать аргументы инструмента: %s",
                    tool_call.function.name,
                )

            result = await execute_tool(
                tool_call.function.name,
                arguments,
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )