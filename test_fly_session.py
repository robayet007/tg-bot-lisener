import asyncio
from telethon import TelegramClient

async def test():
    client = TelegramClient("/app/sessions/telegram_listener", 37118739, "d02baf67c4f5d2e0586236c24e1248d1")
    await client.connect()
    auth = await client.is_user_authorized()
    print("Authorized:", auth)
    await client.disconnect()

asyncio.run(test())
