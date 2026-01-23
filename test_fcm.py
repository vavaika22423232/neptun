#!/usr/bin/env python3
import firebase_admin
from firebase_admin import credentials, messaging
import os

# Initialize Firebase if not already
if not firebase_admin._apps:
    # Try to get credentials from environment or file
    cred_json = os.environ.get('FIREBASE_CREDENTIALS_JSON')
    if cred_json:
        import json
        cred_dict = json.loads(cred_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    else:
        cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'serviceAccountKey.json')
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            print(f'ERROR: No credentials at {cred_path}')
            print('Set FIREBASE_CREDENTIALS_JSON env var or provide serviceAccountKey.json')
            exit(1)

# Your iOS FCM token from logs
FCM_TOKEN = 'd90Fa7h6K08_twbHAH8_o6:APA91bFLRQ25k6H4ba7F0e_zx5Lgxv30qPUc0G8pIz8NXLK6mXt1P_H6yabh-N5zkbqjwpFuHSK0N6Gu24LzpZ2Or_FWrXqMIakZB39dlN1MUKZ8jOgJnpU'

# Send test message directly to device token
message = messaging.Message(
    data={
        'type': 'telegram_threat',
        'title': 'ТЕСТ Telegram',
        'body': 'Тестове повідомлення для iOS',
        'location': 'Тест',
        'region': 'Тест',
        'alarm_state': 'active',
        'is_critical': 'false',
        'threat_type': 'Тест',
        'timestamp': '2026-01-22T12:00:00',
    },
    apns=messaging.APNSConfig(
        headers={
            'apns-priority': '10',
            'apns-push-type': 'alert',
        },
        payload=messaging.APNSPayload(
            aps=messaging.Aps(
                alert=messaging.ApsAlert(title='ТЕСТ прямий', body='Тестове повідомлення напряму'),
                sound='default',
                badge=1,
                content_available=True,
                mutable_content=True,
            ),
        ),
    ),
    token=FCM_TOKEN,  # Send directly to device
)

try:
    response = messaging.send(message)
    print(f'Test message sent directly to device: {response}')
except Exception as e:
    print(f'ERROR sending message: {e}')
