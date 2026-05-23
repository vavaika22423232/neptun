import assert from 'node:assert/strict';
import { validateChatMessageInput, CHAT_MESSAGE_MAX_LENGTH } from './chatMessageValidation';

assert.equal(validateChatMessageInput('   ').ok, false);
assert.equal(validateChatMessageInput('Привіт').ok, true);
assert.equal(validateChatMessageInput('a'.repeat(CHAT_MESSAGE_MAX_LENGTH + 1)).ok, false);
assert.equal(validateChatMessageInput('z'.repeat(60)).ok, false);
console.log('chatMessageValidation.test.ts: ok');
