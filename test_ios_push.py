#!/usr/bin/env python3
"""Test iOS push notification"""
import firebase_admin
from firebase_admin import credentials, messaging
import os
import json
import base64

# Initialize Firebase
if not firebase_admin._apps:
    # Try environment variable first (same as app.py)
    cred_json = os.environ.get('FIREBASE_CREDENTIALS')
    if cred_json:
        cred_dict = json.loads(base64.b64decode(cred_json))
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized from env")
    elif os.path.exists('firebase-credentials.json'):
        cred = credentials.Certificate('firebase-credentials.json')
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized from file")
    else:
        print("❌ No Firebase credentials found!")
        print("   Set FIREBASE_CREDENTIALS env var or create firebase-credentials.json")
        print("   Download from: Firebase Console → Project Settings → Service accounts")
        exit(1)

# Your iOS FCM token from the logs
IOS_FCM_TOKEN = "dw2Sbi5q7k4Oj-vLp7_W0T:APA91bH-Vn7tPG7K8awn3JSz-u5LtLxXWi4XqfkHlk09ZXkB9PuFbRl1yLauBQimDViR4vN3UdRCmEGkyJwZ-QN-zN7sx5gomnTYFblOcCMrylBnkEiOQ1k"

print(f"📱 Sending to token: {IOS_FCM_TOKEN[:50]}...")

try:
    message = messaging.Message(
        notification=messaging.Notification(
            title="🧪 Тест iOS Push",
            body="Якщо ви бачите це - push працює!",
        ),
        data={
            'type': 'test',
            'timestamp': '2026-01-30',
        },
        apns=messaging.APNSConfig(
            headers={
                'apns-priority': '10',
                'apns-push-type': 'alert',
            },
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title="🧪 Тест iOS Push",
                        body="Якщо ви бачите це - push працює!"
                    ),
                    sound='default',
                    badge=1,
                ),
            ),
        ),
        token=IOS_FCM_TOKEN,
    )
    
    response = messaging.send(message)
    print(f"✅ SUCCESS! Message sent: {response}")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    print(f"Error type: {type(e).__name__}")
