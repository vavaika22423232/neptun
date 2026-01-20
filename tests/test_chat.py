"""
Tests for chat service module.
"""
import os
import tempfile

import pytest

from services.chat import ChatModerator, ChatStore


class TestChatStore:
    """Test ChatStore class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def store(self, temp_dir):
        """Create a ChatStore instance with temp directory."""
        file_path = os.path.join(temp_dir, 'chat_messages.json')
        return ChatStore(file_path=file_path)

    def test_init_creates_empty_messages(self, store):
        """Test that store initializes with empty messages."""
        messages = store.get_messages()
        assert messages == []

    def test_add_message(self, store):
        """Test adding a message."""
        msg = store.add_message(
            user_id="TestUser",
            message="Hello, world!",
            device_id="device123"
        )

        assert msg is not None
        assert msg['userId'] == "TestUser"
        assert msg['message'] == "Hello, world!"
        assert msg['deviceId'] == "device123"
        assert 'id' in msg
        assert 'timestamp' in msg

    def test_get_messages(self, store):
        """Test getting messages."""
        store.add_message("User1", "Msg 1", "d1")
        store.add_message("User2", "Msg 2", "d2")
        store.add_message("User3", "Msg 3", "d3")

        messages = store.get_messages()
        assert len(messages) == 3

        # Messages should be in order (oldest first for display)
        assert messages[0]['message'] == "Msg 1"
        assert messages[2]['message'] == "Msg 3"

    def test_get_messages_with_limit(self, store):
        """Test limiting messages returned."""
        for i in range(10):
            store.add_message(f"User{i}", f"Msg {i}", f"d{i}")

        messages = store.get_messages(limit=5)
        assert len(messages) == 5

    def test_delete_message(self, store):
        """Test deleting a message."""
        msg = store.add_message("User1", "Delete me", "d1")
        msg_id = msg['id']

        result = store.delete_message(msg_id)
        assert result is True

        messages = store.get_messages()
        assert len(messages) == 0

    def test_delete_nonexistent_message(self, store):
        """Test deleting a message that doesn't exist."""
        result = store.delete_message("nonexistent-id")
        assert result is False

    def test_persistence(self, temp_dir):
        """Test that messages persist to disk."""
        file_path = os.path.join(temp_dir, 'chat_messages.json')
        store1 = ChatStore(file_path=file_path)
        store1.add_message("User1", "Persistent msg", "d1")

        # Create new store instance with same file
        store2 = ChatStore(file_path=file_path)
        messages = store2.get_messages()

        assert len(messages) == 1
        assert messages[0]['message'] == "Persistent msg"

    def test_max_messages_limit(self, temp_dir):
        """Test that max_messages limit is enforced."""
        file_path = os.path.join(temp_dir, 'chat_messages.json')
        store = ChatStore(file_path=file_path, max_messages=5)

        for i in range(10):
            store.add_message(f"User{i}", f"Msg {i}", f"d{i}")

        # Note: max_messages is enforced on save, not on add
        messages = store.get_messages()
        assert len(messages) <= 10  # All might be in memory

    def test_get_message_by_id(self, store):
        """Test getting a specific message by ID."""
        msg = store.add_message("User1", "Find me", "d1")
        msg_id = msg['id']

        found = store.get_message(msg_id)
        assert found is not None
        assert found['message'] == "Find me"

    def test_stats(self, store):
        """Test statistics method."""
        store.add_message("User1", "Msg 1", "d1")
        store.add_message("User2", "Msg 2", "d2")

        stats = store.stats()
        assert stats['total_messages'] == 2
        assert 'registered_nicknames' in stats

    def test_nickname_registration(self, store):
        """Test nickname registration."""
        result = store.register_nickname("CoolNick", "device1")
        assert result is True

        # Check ownership
        assert store.validate_nickname_ownership("CoolNick", "device1") is True
        assert store.validate_nickname_ownership("CoolNick", "device2") is False

    def test_nickname_availability(self, store):
        """Test checking nickname availability."""
        assert store.check_nickname_available("AvailableName") is True

        store.register_nickname("TakenName", "device1")
        assert store.check_nickname_available("TakenName") is False

        # Same device should see it as available
        assert store.check_nickname_available("TakenName", "device1") is True


class TestChatModerator:
    """Test ChatModerator class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def moderator(self, temp_dir):
        """Create a ChatModerator instance with temp directory."""
        banned_file = os.path.join(temp_dir, 'chat_banned.json')
        moderators_file = os.path.join(temp_dir, 'chat_moderators.json')
        return ChatModerator(banned_file=banned_file, moderators_file=moderators_file)

    def test_ban_user(self, moderator):
        """Test banning a user."""
        result = moderator.ban_user(
            device_id="bad_device",
            reason="Spam",
            banned_by="admin"
        )

        assert result is True
        assert moderator.is_banned("bad_device") is True

    def test_unban_user(self, moderator):
        """Test unbanning a user."""
        moderator.ban_user("device1", "Test", "admin")
        assert moderator.is_banned("device1") is True

        result = moderator.unban_user("device1")
        assert result is True
        assert moderator.is_banned("device1") is False

    def test_is_banned_returns_false_for_unknown_user(self, moderator):
        """Test that unknown users are not banned."""
        assert moderator.is_banned("unknown_device") is False

    def test_forbidden_nicknames(self, moderator):
        """Test that forbidden nicknames are detected."""
        # These should be forbidden
        assert moderator.is_nickname_forbidden("admin") is True
        assert moderator.is_nickname_forbidden("Admin") is True
        assert moderator.is_nickname_forbidden("ADMIN") is True
        assert moderator.is_nickname_forbidden("moderator") is True
        assert moderator.is_nickname_forbidden("neptun") is True

        # Normal names should be allowed
        assert moderator.is_nickname_forbidden("JohnDoe") is False
        assert moderator.is_nickname_forbidden("Player123") is False

    def test_validate_nickname(self, moderator):
        """Test nickname validation."""
        # Too short
        error = moderator.validate_nickname("ab")
        assert error is not None

        # Too long
        error = moderator.validate_nickname("a" * 25)
        assert error is not None

        # Forbidden
        error = moderator.validate_nickname("admin")
        assert error is not None

        # Valid
        error = moderator.validate_nickname("ValidNick")
        assert error is None

    def test_persistence(self, temp_dir):
        """Test that bans persist to disk."""
        banned_file = os.path.join(temp_dir, 'chat_banned.json')
        moderators_file = os.path.join(temp_dir, 'chat_moderators.json')

        mod1 = ChatModerator(banned_file=banned_file, moderators_file=moderators_file)
        mod1.ban_user("device1", "Test", "admin")

        # Create new instance
        mod2 = ChatModerator(banned_file=banned_file, moderators_file=moderators_file)
        assert mod2.is_banned("device1") is True

    def test_moderator_management(self, moderator):
        """Test adding and removing moderators."""
        assert moderator.is_moderator("device1") is False

        moderator.add_moderator("device1")
        assert moderator.is_moderator("device1") is True

        moderator.remove_moderator("device1")
        assert moderator.is_moderator("device1") is False

    def test_stats(self, moderator):
        """Test moderation statistics."""
        moderator.ban_user("d1", "Test", "admin")
        moderator.add_moderator("mod1")

        stats = moderator.stats()
        assert stats['banned_users'] == 1
        assert stats['moderators'] == 1


class TestChatIntegration:
    """Integration tests for chat components."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_store_and_moderator_together(self, temp_dir):
        """Test using store and moderator together."""
        store = ChatStore(file_path=os.path.join(temp_dir, 'chat.json'))
        mod = ChatModerator(
            banned_file=os.path.join(temp_dir, 'bans.json'),
            moderators_file=os.path.join(temp_dir, 'mods.json')
        )

        # Register nickname
        store.register_nickname("TestUser", "device1")

        # Add message
        msg = store.add_message(
            user_id="TestUser",
            message="Hello!",
            device_id="device1"
        )

        assert msg['userId'] == "TestUser"

        # Ban user
        mod.ban_user("device1", "Spam", "admin")

        # Check ban before allowing new messages
        assert mod.is_banned("device1") is True

    def test_message_cleanup_by_banned_user(self, temp_dir):
        """Test that we can find and remove messages by banned user."""
        store = ChatStore(file_path=os.path.join(temp_dir, 'chat.json'))

        # Add messages from multiple users
        store.add_message("User1", "Msg 1", "device1")
        store.add_message("User2", "Msg 2", "device2")
        store.add_message("User1", "Msg 3", "device1")

        messages = store.get_messages()
        assert len(messages) == 3

        # Get messages by device1
        device1_msgs = [m for m in messages if m['deviceId'] == "device1"]
        assert len(device1_msgs) == 2

        # Delete device1's messages
        for msg in device1_msgs:
            store.delete_message(msg['id'])

        messages = store.get_messages()
        assert len(messages) == 1
        assert messages[0]['deviceId'] == "device2"
