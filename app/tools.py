import ast
import operator
from pathlib import Path

import httpx
from bs4 import BeautifulSoup


TOOLS_DIR = Path("data/agent_files")
TOOLS_DIR.mkdir(parents=True, exist_ok=True)


async def web_search(query: str, max_results: int = 5) -> str:
    url = "https://html.duckduckgo.com/html/"

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(
            url,
            params={"q": query},
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/150.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for result in soup.select(".result")[:max_results]:
        title_element = result.select_one(".result__title")
        link_element = result.select_one(".result__a")
        snippet_element = result.select_one(".result__snippet")

        if not title_element:
            continue

        title = title_element.get_text(" ", strip=True)

        link = ""
        if link_element:
            link = link_element.get("href", "")

        snippet = ""
        if snippet_element:
            snippet = snippet_element.get_text(" ", strip=True)

        results.append(
            f"Название: {title}\n"
            f"Описание: {snippet}\n"
            f"Ссылка: {link}"
        )

    if not results:
        return "По вашему запросу ничего не найдено."

    return "\n\n".join(results)


async def get_weather(city: str) -> str:
    """Получает текущую погоду через Open-Meteo."""

    async with httpx.AsyncClient(timeout=15) as client:
        geocoding_response = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": city,
                "count": 1,
                "language": "ru",
                "format": "json",
            },
        )
        geocoding_response.raise_for_status()

        geocoding_data = geocoding_response.json()
        results = geocoding_data.get("results", [])

        if not results:
            return f"Не удалось найти город: {city}"

        location = results[0]

        latitude = location["latitude"]
        longitude = location["longitude"]
        city_name = location.get("name", city)
        country = location.get("country", "")

        weather_response = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "apparent_temperature,"
                    "weather_code,"
                    "wind_speed_10m"
                ),
                "timezone": "auto",
            },
        )
        weather_response.raise_for_status()

        weather_data = weather_response.json()

    current = weather_data.get("current", {})

    return (
        f"Погода в городе {city_name}"
        f"{', ' + country if country else ''}:\n"
        f"Температура: {current.get('temperature_2m')} °C\n"
        f"Ощущается как: "
        f"{current.get('apparent_temperature')} °C\n"
        f"Влажность: "
        f"{current.get('relative_humidity_2m')}%\n"
        f"Ветер: "
        f"{current.get('wind_speed_10m')} км/ч\n"
        f"Код погоды: "
        f"{current.get('weather_code')}"
    )


async def get_crypto_price(
    cryptocurrency: str,
    currency: str = "usd",
) -> str:
    """Получает цену криптовалюты через CoinGecko."""

    coin_map = {
        "bitcoin": "bitcoin",
        "btc": "bitcoin",
        "ethereum": "ethereum",
        "eth": "ethereum",
        "solana": "solana",
        "sol": "solana",
        "dogecoin": "dogecoin",
        "doge": "dogecoin",
    }

    coin_id = coin_map.get(
        cryptocurrency.lower().strip()
    )

    if not coin_id:
        return (
            f"Пока не знаю криптовалюту "
            f"«{cryptocurrency}». "
            "Попробуйте BTC, ETH или SOL."
        )

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": coin_id,
                "vs_currencies": currency.lower(),
            },
        )
        response.raise_for_status()

        data = response.json()

    price = data.get(coin_id, {}).get(currency.lower())

    if price is None:
        return (
            f"Не удалось получить цену "
            f"{cryptocurrency.upper()}."
        )

    return (
        f"{cryptocurrency.upper()} сейчас стоит "
        f"{price} {currency.upper()}."
    )


def read_file(filename: str) -> str:
    """Читает текстовый файл."""

    path = TOOLS_DIR / filename

    if not path.exists():
        return f"Файл «{filename}» не найден."

    if not path.is_file():
        return f"«{filename}» не является файлом."

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return (
            f"Не удалось прочитать «{filename}» "
            "как текстовый файл."
        )


def write_file(filename: str, content: str) -> str:
    """Записывает текст в файл."""

    path = TOOLS_DIR / filename
    path.write_text(content, encoding="utf-8")

    return f"Файл «{filename}» успешно сохранён."


async def get_currency_rate(
    base_currency: str,
    target_currency: str,
) -> str:
    """Получает курс обычной валюты через Frankfurter."""

    base = base_currency.upper()
    target = target_currency.upper()

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            "https://api.frankfurter.dev/v1/latest",
            params={
                "from": base,
                "to": target,
            },
        )
        response.raise_for_status()

        data = response.json()

    rate = data.get("rates", {}).get(target)

    if rate is None:
        return (
            f"Не удалось получить курс "
            f"{base}/{target}."
        )

    return f"1 {base} = {rate} {target}."


_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _calculate_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value

        raise ValueError("Разрешены только числа.")

    if isinstance(node, ast.BinOp):
        operation = _ALLOWED_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError(
                "Такая операция не поддерживается."
            )

        left = _calculate_node(node.left)
        right = _calculate_node(node.right)

        return operation(left, right)

    if isinstance(node, ast.UnaryOp):
        operation = _ALLOWED_OPERATORS.get(type(node.op))

        if operation is None:
            raise ValueError(
                "Такая операция не поддерживается."
            )

        operand = _calculate_node(node.operand)

        return operation(operand)

    raise ValueError(
        "Недопустимое математическое выражение."
    )


def calculate(expression: str) -> str:
    """Безопасно вычисляет математическое выражение."""

    try:
        tree = ast.parse(
            expression,
            mode="eval",
        )

        result = _calculate_node(tree.body)

        return f"Результат: {result}"

    except ZeroDivisionError:
        return "Ошибка: деление на ноль."

    except (SyntaxError, ValueError, TypeError):
        return (
            "Не удалось вычислить выражение. "
            "Используйте операции +, -, *, /, %, ** "
            "и скобки."
        )