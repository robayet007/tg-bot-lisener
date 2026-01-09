#!/usr/bin/env python3
"""Test if local session file is valid"""
import asyncio
from telegram_listener import TelegramBotListener

async def test_session():
    print("Testing local session file...")
    listener = TelegramBotListener()
    
    try:
        await listener.client.connect()
        authorized = await listener.client.is_user_authorized()
        
        if authorized:
            print("[OK] Session file is VALID and authorized!")
            print("You can upload this file to Fly.io")
            return True
        else:
            print("[ERROR] Session file exists but is NOT authorized")
            print("You need to authenticate locally first")
            return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False
    finally:
        try:
            await listener.client.disconnect()
        except:
            pass

if __name__ == "__main__":
    result = asyncio.run(test_session())
    exit(0 if result else 1)
