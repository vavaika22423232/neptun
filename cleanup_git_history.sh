#!/bin/bash
# СКРИПТ ОЧИСТКИ РЕПОЗИТОРИЯ - удаление всех ненужных файлов

echo "🚨 ОЧИСТКА РЕПОЗИТОРИЯ ОТ СТАРЫХ ФАЙЛОВ"
echo "========================================"

# Получаем список файлов из git истории которых больше нет в проекте
find . -type f -not -path './.git/*' -not -path './.venv/*' -not -path './node_modules/*' | sed 's|^\./||' | sort > /tmp/current_files.txt
git log --name-only --pretty=format: | sort | uniq | grep -v '^$' > /tmp/git_history_files.txt
comm -23 /tmp/git_history_files.txt /tmp/current_files.txt > /tmp/files_to_remove.txt

echo "📋 Файлы для удаления из git истории:"
cat /tmp/files_to_remove.txt | head -20
echo "... (всего $(cat /tmp/files_to_remove.txt | wc -l) файлов)"

# Удаляем файлы из git (они больше не отслеживаются)
echo ""
echo "🗑️  Удаляем файлы из git индекса..."

# Удаляем каждый файл из git
while IFS= read -r file; do
    if git ls-files --error-unmatch "$file" >/dev/null 2>&1; then
        echo "Removing: $file"
        git rm --cached "$file" 2>/dev/null || true
    fi
done < /tmp/files_to_remove.txt

echo ""
echo "✅ Файлы удалены из git индекса"
echo "⚡ Теперь нужно сделать commit и push"

# Показываем статистику
echo ""
echo "📊 СТАТИСТИКА ОЧИСТКИ:"
echo "Удалено файлов: $(cat /tmp/files_to_remove.txt | wc -l)"
echo "Оставлено файлов: $(cat /tmp/current_files.txt | wc -l)"

# Очищаем временные файлы
rm -f /tmp/current_files.txt /tmp/git_history_files.txt /tmp/files_to_remove.txt

echo ""
echo "🚀 Готово! Теперь выполните:"
echo "   git commit -m 'Очистка репозитория от старых файлов'"
echo "   git push origin main"
