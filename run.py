import asyncio

from app.agent import run_agent


async def main() -> None:
    print("AI-агент запущен.")
    print("Для выхода напишите: exit")
    print()

    while True:
        user_message = input("Вы: ").strip()

        if user_message.lower() in {"exit", "quit", "выход"}:
            print("До свидания!")
            break

        if not user_message:
            continue

        try:
            answer = await run_agent(user_message)
            print(f"Агент: {answer}")
            print()
        except Exception as error:
            print(f"Ошибка: {error}")


if __name__ == "__main__":
    asyncio.run(main())
