import asyncio
import logging
import os
import signal
import sys
from datetime import datetime

from telethon import TelegramClient, events

# Configuration
from constants import API_ID, API_HASH, CHANNELS
from db import db

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)

# Initialize Client
client = TelegramClient('anon_worker', API_ID, API_HASH)

async def main():
    """Main worker loop."""
    log.info(f"🚀 Worker starting... Channels: {len(CHANNELS)}")
    
    # Ensure Redis connection
    if not db.is_connected():
        log.error("❌ Redis not connected! Exiting.")
        return

    # Start Telegram Client
    await client.start()
    log.info("✅ Telegram Client Connected")

    # Register event handlers
    @client.on(events.NewMessage(chats=CHANNELS))
    async def handler(event):
        try:
            await process_new_message(event)
        except Exception as e:
            log.error(f"Error processing message: {e}", exc_info=True)

    # Keep running
    await client.run_until_disconnected()

from core.parser_v2 import parse_message
import uuid
import json

async def process_new_message(event):
    """
    Core processing pipeline:
    1. Deduplication
    2. Normalization
    3. Parsing (Deterministic)
    4. State Update
    """
    msg_text = event.message.message
    if not msg_text:
        return

    channel_id = event.chat_id
    msg_id = event.message.id
    
    # 1. Deduplication (Skip if already processed)
    if db.is_message_processed(channel_id, msg_id):
        return
    db.mark_message_processed(channel_id, msg_id)

    # 2. Parse
    threat_event = parse_message(msg_text)
    
    # If type is unknown or no location found, we might skip or log
    # For now, we only save if we have a valid event type
    if threat_event.type == 'unknown':
        return

    log.info(f"🚨 MATCH: {threat_event.type} @ {threat_event.location} ({threat_event.region})")
    
    # 3. Enrich & Save
    threat_id = f"evt_{int(datetime.now().timestamp())}_{str(uuid.uuid4())[:4]}"
    data = threat_event.to_dict()
    data['id'] = threat_id
    data['channel_id'] = channel_id
    data['msg_id'] = msg_id
    data['ts'] = datetime.now().isoformat()
    
    # Save to Redis
    # Calculate TTL based on type (Launch = 30m, UAV = 2h)
    ttl = 1800 if threat_event.type in ['launch', 'explosion'] else 7200
    db.save_threat(threat_id, data, ttl=ttl)
    
    # Publish Real-time Update
    db.publish_update('new_threat', data)

def shutdown_handler(sig, frame):
    log.info("🛑 Shutting down worker...")
    asyncio.create_task(client.disconnect())
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
