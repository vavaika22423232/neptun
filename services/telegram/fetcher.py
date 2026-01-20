"""
Telegram message fetcher.

Асинхронний fetcher повідомлень з Telegram каналів
з використанням Telethon.
"""
import asyncio
import logging
import threading
import time
from typing import Optional, List, Callable, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class FetchedMessage:
    """Single fetched message."""
    id: int
    channel: str
    text: str
    timestamp: datetime
    raw: Any = None  # Original Telethon message
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'channel': self.channel,
            'text': self.text,
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class BackfillStatus:
    """Status of backfill operation."""
    channel: str
    total: int = 0
    processed: int = 0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    
    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None
    
    @property
    def progress(self) -> float:
        if self.total == 0:
            return 0.0
        return self.processed / self.total
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'channel': self.channel,
            'total': self.total,
            'processed': self.processed,
            'progress': round(self.progress * 100, 1),
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'error': self.error,
        }


class TelegramFetcher:
    """
    Telegram message fetcher using Telethon.
    
    Features:
    - Real-time message monitoring
    - Historical backfill
    - Rate limiting
    - Callback-based message handling
    """
    
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_string: Optional[str] = None,
        channels: Optional[List[str]] = None,
        on_message: Optional[Callable[[FetchedMessage], None]] = None,
    ):
        """
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API hash
            session_string: Optional session string for auth
            channels: List of channels to monitor
            on_message: Callback for new messages
        """
        self._api_id = api_id
        self._api_hash = api_hash
        self._session_string = session_string
        self._channels = channels or []
        self._on_message = on_message
        
        self._client = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        
        # Status
        self._connected = False
        self._last_message_time: Optional[float] = None
        self._message_count = 0
        self._backfill_status: Dict[str, BackfillStatus] = {}
    
    def start(self) -> bool:
        """
        Start the fetcher in a background thread.
        
        Returns:
            True if started successfully
        """
        if self._running:
            return True
        
        try:
            self._running = True
            self._thread = threading.Thread(
                target=self._run_async_loop,
                daemon=True,
                name='TelegramFetcher',
            )
            self._thread.start()
            
            # Wait for connection
            for _ in range(30):  # 30 second timeout
                if self._connected:
                    log.info("TelegramFetcher started and connected")
                    return True
                time.sleep(1)
            
            log.warning("TelegramFetcher started but not connected yet")
            return True
            
        except Exception as e:
            log.error(f"Failed to start TelegramFetcher: {e}")
            self._running = False
            return False
    
    def stop(self) -> None:
        """Stop the fetcher."""
        if not self._running:
            return
        
        log.info("Stopping TelegramFetcher...")
        self._running = False
        
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        
        log.info("TelegramFetcher stopped")
    
    def is_connected(self) -> bool:
        """Check if connected to Telegram."""
        return self._connected
    
    def get_status(self) -> Dict[str, Any]:
        """Get fetcher status."""
        return {
            'running': self._running,
            'connected': self._connected,
            'channels': self._channels,
            'message_count': self._message_count,
            'last_message': self._last_message_time,
            'backfill': {k: v.to_dict() for k, v in self._backfill_status.items()},
        }
    
    def get_backfill_status(self) -> Dict[str, BackfillStatus]:
        """Get backfill status for all channels."""
        return dict(self._backfill_status)
    
    async def backfill_channel(
        self,
        channel: str,
        limit: int = 100,
        process_fn: Optional[Callable[[FetchedMessage], None]] = None,
    ) -> BackfillStatus:
        """
        Backfill historical messages from a channel.
        
        Args:
            channel: Channel name or ID
            limit: Maximum messages to fetch
            process_fn: Optional processing function for each message
        """
        status = BackfillStatus(channel=channel, started_at=time.time())
        self._backfill_status[channel] = status
        
        if not self._client:
            status.error = "Client not initialized"
            status.completed_at = time.time()
            return status
        
        try:
            from telethon import functions
            
            # Resolve channel
            try:
                entity = await self._client.get_entity(channel)
            except Exception as e:
                status.error = f"Channel not found: {e}"
                status.completed_at = time.time()
                return status
            
            # Fetch messages
            messages = []
            async for msg in self._client.iter_messages(entity, limit=limit):
                if msg.text:
                    messages.append(msg)
            
            status.total = len(messages)
            log.info(f"Backfill {channel}: found {status.total} messages")
            
            # Process messages
            for msg in reversed(messages):  # Oldest first
                try:
                    fetched = FetchedMessage(
                        id=msg.id,
                        channel=channel,
                        text=msg.text,
                        timestamp=msg.date.replace(tzinfo=None) if msg.date else datetime.utcnow(),
                        raw=msg,
                    )
                    
                    if process_fn:
                        process_fn(fetched)
                    elif self._on_message:
                        self._on_message(fetched)
                    
                    status.processed += 1
                    
                except Exception as e:
                    log.warning(f"Error processing message {msg.id}: {e}")
            
            status.completed_at = time.time()
            log.info(f"Backfill {channel} complete: {status.processed}/{status.total}")
            
        except Exception as e:
            status.error = str(e)
            status.completed_at = time.time()
            log.error(f"Backfill {channel} failed: {e}")
        
        return status
    
    def _run_async_loop(self) -> None:
        """Run the async event loop in a thread."""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            self._loop.run_until_complete(self._async_main())
            
        except Exception as e:
            log.error(f"Async loop error: {e}")
        finally:
            if self._loop:
                self._loop.close()
            self._loop = None
            self._connected = False
    
    async def _async_main(self) -> None:
        """Main async function."""
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
            from telethon import events
            
            # Create client
            if self._session_string:
                self._client = TelegramClient(
                    StringSession(self._session_string),
                    self._api_id,
                    self._api_hash,
                )
            else:
                self._client = TelegramClient(
                    'anon',
                    self._api_id,
                    self._api_hash,
                )
            
            await self._client.start()
            self._connected = await self._client.is_user_authorized()
            
            if not self._connected:
                log.warning("Telegram client not authorized")
                return
            
            log.info(f"Connected to Telegram, monitoring {len(self._channels)} channels")
            
            # Register message handler
            @self._client.on(events.NewMessage(chats=self._channels))
            async def handle_new_message(event):
                await self._handle_message(event)
            
            # Run until stopped
            while self._running:
                await asyncio.sleep(1)
            
            await self._client.disconnect()
            
        except Exception as e:
            log.error(f"Telegram client error: {e}")
            self._connected = False
    
    async def _handle_message(self, event) -> None:
        """Handle incoming message."""
        try:
            if not event.message or not event.message.text:
                return
            
            channel = str(event.chat_id) if event.chat_id else 'unknown'
            
            # Try to get channel username
            try:
                chat = await event.get_chat()
                if hasattr(chat, 'username') and chat.username:
                    channel = chat.username
            except Exception:
                pass
            
            fetched = FetchedMessage(
                id=event.message.id,
                channel=channel,
                text=event.message.text,
                timestamp=event.message.date.replace(tzinfo=None) if event.message.date else datetime.utcnow(),
                raw=event.message,
            )
            
            self._message_count += 1
            self._last_message_time = time.time()
            
            log.debug(f"New message from {channel}: {fetched.text[:50]}...")
            
            if self._on_message:
                try:
                    self._on_message(fetched)
                except Exception as e:
                    log.error(f"Error in message callback: {e}")
                    
        except Exception as e:
            log.error(f"Error handling message: {e}")
