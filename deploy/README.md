# Деплой Neptun (VPS)

## Швидкий старт з Mac

```bash
# З кореня репозиторію (render2/)
make deploy-validate                    # або: bash deploy/validate-before-deploy.sh
bash deploy/deploy-from-mac.sh        # сам викликає validate (SKIP_VALIDATE=1 щоб пропустити)
```

На сервері виконується [`deploy.sh`](deploy.sh): `npm ci` / `next build`, Python venv, перебудова gazetteer, `systemctl restart` neptun-web / neptun-worker. Photon Docker/import tooling лежить окремо в [`../infra/photon`](../infra/photon).

## Змінні середовища

Шаблон: [`.env.example`](.env.example) — копіюється вручну на сервер як `/home/neptun/app/.env` (rsync **не** перезаписує `.env`).

Обов’язково для продакшену:

| Змінна | Призначення |
|--------|-------------|
| `AUTH_SECRET` | Базовий fallback secret |
| `INGEST_SECRET` | Опційно: окремий ключ воркера для `/api/ingest` |
| `ADMIN_API_SECRET` | Опційно: `X-Auth-Secret` для admin JSON/moderator tools |
| `INGEST_URL` | Напр. `http://127.0.0.1:3000/api/ingest` |
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION` | Воркер Telegram |
| `OPENAI_API_KEY` | Потрібен лише якщо GPT увімкнено (`DISABLE_GPT_PARSER=0`). Інакше — regex-primary + basic analysis |
| `DISABLE_GPT_PARSER` | За замовчуванням у коді **вимкнено** OpenAI для парсингу та `ai_message_analyzer`. Щоб увімкнути GPT: `DISABLE_GPT_PARSER=0` (або `false` / `no` / `off`) |
| `GROQ_API_KEY` | Опційно: LLM для траєкторії (`ai_trajectory.py`) замість OpenAI |
| `DATA_DIR` | Зазвичай `/data` для messages.json тощо |

Опційно: `ADMIN_SECRET` як deprecated alias для `ADMIN_API_SECRET`, `VISICOM_API_KEY`, `OPENCAGE_API_KEY`.

Канал `@kherson_non_drone` підключається **кодом** (`worker/constants.py` + `channel_profiles/`), окремих змінних не потрібно.

## Повна перебудова gazetteer (`settlements.db`)

Після змін у `worker/geo/data/build_gazetteer.py` або якщо на сервері застаріла БД:

```bash
REBUILD_GAZETTEER=1 bash deploy/deploy-from-mac.sh
```

Або на VPS:

```bash
sudo bash /home/neptun/app/deploy/rebuild-gazetteer.sh
sudo systemctl restart neptun-worker
```

Стандартний `deploy.sh` уже викликає `build_gazetteer.py --download` (оновлення CSV + БД). Прапорець `REBUILD_GAZETTEER=1` додатково в кінці запускає [`rebuild-gazetteer.sh`](rebuild-gazetteer.sh) (чиста перебудова `settlements.db` з `geo/data/build_gazetteer.py` у каталозі `geo/data`) і перезапускає воркер — вмикайте після змін у захардкожених рядках gazetteer (наприклад raion для Херсона).

## Після деплою

```bash
bash /home/neptun/app/deploy/check-post-deploy.sh
journalctl -u neptun-web -n 30 --no-pager
journalctl -u neptun-worker -n 50 --no-pager
```

Перевірка здоров’я: `curl -s http://127.0.0.1:3000/api/health`.

## Nginx: ліміти та пікове навантаження

Якщо в `error.log` є `limiting requests` або `no live upstreams`:

1. У `http { }` підключіть [nginx-http-limits-snippet.conf](nginx-http-limits-snippet.conf) **один раз** (або замініть старі `limit_req_zone` / `limit_conn_zone` з тими ж іменами зон).
2. Сайт [nginx-neptun-optimized.conf](nginx-neptun-optimized.conf) роздає `shahed3.webp`, `rozvedka2.webp` та `icon_*.svg` **з диска** (`.next/standalone/public`) через зону `neptun_static_nolimit` (сумісно з nginx без `limit_req off`).
3. Після зміни `PM2_INSTANCES` перегенеруйте upstream: `source /home/neptun/app/.env && bash deploy/print-nginx-upstream.sh` і вставте блок у `nginx.conf`, потім `sudo nginx -t && sudo systemctl reload nginx` та `pm2 reload neptun`.

## Статичні файли карти

Іконка `fpvdrone.png` має бути в `nextjs-app/public/` (шлях на сайті `/fpvdrone.png`). Потрапляє на сервер через rsync Next.js. Растер `shahed3.webp` також має лежати в `public/`, інакше nginx поверне 404 для прямого `alias`.

## Canonical configs

| Файл | Для чого |
|------|----------|
| [`nginx-neptun.conf`](nginx-neptun.conf) | базовий nginx site config |
| [`nginx-neptun-optimized.conf`](nginx-neptun-optimized.conf) | production nginx з оптимізаціями статичних файлів |
| [`nginx-http-limits-snippet.conf`](nginx-http-limits-snippet.conf) | `http {}` snippet для limit zones |
| [`nginx-upstream-nextjs.conf`](nginx-upstream-nextjs.conf) | upstream block для кількох Next.js/PM2 instance |
| [`legacy/`](legacy/) | старі конфіги лише для reference |

## CI

GitHub Actions (`.github/workflows/tests.yml`) ганяє canonical worker unit tests, Next.js lint і domain tests; продакшен-деплой — вручну скриптом вище.
