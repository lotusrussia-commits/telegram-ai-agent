from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.agent import run_agent
from app.config import TELEGRAM_BOT_TOKEN


bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "Привет! Я AI-агент.\n\n"
        "Я умею:\n"
        "• искать информацию в интернете;\n"
        "• показывать погоду;\n"
        "• получать курсы валют и криптовалют;\n"
        "• читать и сохранять файлы;\n"
        "• выполнять расчёты;\n"
        "• помнить историю нашего диалога."
    )


@dp.message(F.document)
async def document_handler(message: Message) -> None:
    document = message.document

    if not document:
        return

    filename = document.file_name or "document"

    allowed_extensions = {".txt", ".pdf", ".docx"}
    extension = (
        "." + filename.lower().split(".")[-1]
        if "." in filename
        else ""
    )

    if extension not in allowed_extensions:
        await message.answer(
            "Поддерживаются только файлы TXT, PDF и DOCX."
        )
        return

    from app.documents import UPLOADS_DIR, index_document

    file_path = UPLOADS_DIR / filename

    telegram_file = await bot.get_file(document.file_id)
    await bot.download_file(telegram_file.file_path, file_path)

    try:
        chunks_count = await index_document(file_path)
    except Exception as error:
        await message.answer(
            f"Не удалось обработать файл: {error}"
        )
        return

    await message.answer(
        f"Файл «{filename}» обработан.\n"
        f"Добавлено фрагментов в память: {chunks_count}"
    )


@dp.message(F.text)
async def text_handler(message: Message) -> None:
    user_text = message.text

    if not user_text:
        return

    try:
        answer = await run_agent(user_text)
    except Exception as error:
        answer = f"Произошла ошибка при обработке запроса: {error}"

    await message.answer(answer)


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())