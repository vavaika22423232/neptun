#!/bin/bash
# 🚀 ЗАПУСК Channel Forwarder Bot

echo "╔════════════════════════════════════════╗"
echo "║  🤖 Channel Forwarder Bot v1.0        ║"
echo "║  Автоматичне пересилання повідомлень  ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Перехід в робочу директорію
cd /Users/vladimirmalik/Desktop/render2

echo "📋 Вихідні канали:"
echo "   • @UkraineAlarmSignal"
echo "   • @kpszsu"
echo "   • @war_monitor"
echo "   • @napramok"
echo "   • @raketa_trevoga"
echo "   • @ukrainsiypposhnik"
echo ""
echo "📍 Цільовий канал: @mapstransler"
echo ""

# Перевірка залежностей
echo "🔍 Перевірка залежностей..."
if python3 -c "import telethon" 2>/dev/null; then
    echo "   ✅ telethon встановлено"
else
    echo "   ❌ telethon не знайдено"
    echo "   📦 Встановлюю..."
    python3 -m pip install telethon --quiet
fi

echo ""
echo "════════════════════════════════════════"
echo ""
echo "⚠️  ВАЖЛИВО:"
echo ""
echo "При ПЕРШОМУ запуску потрібно:"
echo "  1️⃣  Ввести код з SMS на +263781966038"
echo "  2️⃣  Можливо ввести 2FA пароль (якщо є)"
echo ""
echo "При НАСТУПНИХ запусках код НЕ потрібен!"
echo ""
echo "════════════════════════════════════════"
echo ""

read -p "Натисніть Enter для запуску бота..." 

echo ""
echo "🚀 Запускаю Channel Forwarder Bot..."
echo ""

# Запуск бота
python3 channel_forwarder.py

# Якщо бот зупинено
echo ""
echo "⏹️  Бот зупинено"
echo ""
