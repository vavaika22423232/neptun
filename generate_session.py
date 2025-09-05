from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# Simple helper to create a TELEGRAM_SESSION string for deployment (Render)
# Run locally: python generate_session.py
# Paste resulting STRING_SESSION value into Render env var TELEGRAM_SESSION

def main():
    api_id = int(input('API_ID: ').strip())
    api_hash = input('API_HASH: ').strip()
    print('> Logging in (you will get a code in Telegram)...')
    with TelegramClient(StringSession(), api_id, api_hash) as client:
        session = client.session.save()
        me = client.get_me()
        print('\nOK. User:', me.username or me.id)
        print('\nSTRING_SESSION=')
        print(session)
        print('\nAdd this value (without quotes) to Render env var TELEGRAM_SESSION')

if __name__ == '__main__':
    main()
