"""
message_filter.py — Fast pre-filter for Telegram messages.

Thin facade over parser_v2.py functions. Used BEFORE GPT call to:
1. Skip spam/summary/noise messages (no API cost)
2. Extract header oblast (context for GPT)
3. Detect allclear keywords (safety cross-check after GPT)

Does NOT extract entities — that's GPT's job now.
"""

import re
import logging
from typing import Optional

log = logging.getLogger(__name__)

# Import from parser_v2 (these functions stay in parser_v2 as the source of truth)
from core.parser_v2 import (
    normalize_text,
    extract_oblast_authority,
    ALLCLEAR_KEYWORDS,
    ALLCLEAR_WORD_BOUNDARY,
    NEGATION_KEYWORDS,
    _is_summary_message,
    _is_planning_message,
)

# Якщо в тексті є явний сигнал поточної загрози — не відсікаємо повідомлення
# лише через «адміністративні» патерни (відключення, збори, реклама).
_LIVE_THREAT_HINT = re.compile(
    r'\b(?:шахед|шахід|шахедів|герань|бпла|дронів|дрон|фпв|'
    r'ракет|крилат|баліст|каб|авіабомб|тактичн|су-3[045]|пуск|запуск|'
    r'рсзв|смерч|ураган|град|артилер|обстріл|міномет|сау|'
    r'курс\s+на|напрям(?:ок|ку)\s+на|рух\s+на|летить|летять|йдуть|йде|прямує|'
    r'загроз[аи]\s+(?:застосування|бпла|ракет)|повітрян\w+\s+ціл|'
    r'тривог\w+\s+(?:через|у\s+зв|на\s+тер)|ціл[іь]\s+на)'
    r'|[✈🛸🛵🚀💣☄]',
    re.IGNORECASE,
)

# Патерни «не бойова обстановка» — можуть співпасти з репостом під загрозу
_ADMIN_INFRA_SKIP_PATTERNS = [
    r'графік\s+(?:годин\s+)?відключень',
    r'відключення\s+електроенергії\s+станом',
    r'світло\s+буде\s+відсутн',
    r'стабілізаційн[аиі]\s+груп',
    r'опитування\s+у\s+бот',
    r'голосування\s+в\s+коментар',
    r'збір\s+на\s+(?:дрон|авто|тепловізор|пікап)',
    r'благодійн(?:ий|а)\s+(?:збір|аукціон)',
    r'рекламн[аиій]\s+(?:публікація|розсилка)',
    r'передплат\w*\s+на\s+канал',
]

_NON_THREAT_CONTEXT_PATTERNS = [
    # Weather forecast posts: city + tomorrow/hourly forecast/wind/rain. These
    # often contain real place names and numbers but are not threat tracking.
    r'\b(?:погод[аиу]|прогноз\s+погод[иы]|weather)\b',
    r'\b(?:завтра|сьогодні|сегодня)\s+у\s+[а-яіїєґ]+(?:і|е|у)?\s+від\s*[-+]?\d+\s*[℃°]',
    r'(?:[🌥☁⛅🌦🌧☀️]|☂️|🌀).{0,80}(?:[℃°]|хмарно|дощ|дожд|вітер|ветер|прояснення)',
    r'(?:^|\n)\s*[•\-–]\s*\d{2}:\d{2}\s*[:：].{0,80}(?:[℃°]|☂️|🌀)',
    r'\b(?:хмарно|пасмурно|дощ|дождь|прояснення|опади|осадки)\b',
    r'\b(?:гром|гроза|блискавка|молния)\b',
]


def is_non_threat_context(text: str, normalized: Optional[str] = None) -> bool:
    """Return True for clearly non-operational posts that must never create markers."""
    if not text or len(text.strip()) < 5:
        return True
    n = normalized if normalized is not None else normalize_text(text)
    for pat in _NON_THREAT_CONTEXT_PATTERNS:
        if re.search(pat, n, re.IGNORECASE):
            return True
    return False


def is_skip_message(text: str) -> bool:
    """
    Fast check: should this message be skipped entirely?
    Returns True for negations, spam, summaries, skip-pattern matches.
    No API call needed for these.
    """
    if not text or len(text.strip()) < 5:
        return True

    normalized = normalize_text(text)

    # Negation keywords (test messages, corrections)
    for neg in NEGATION_KEYWORDS:
        if neg in normalized:
            log.debug(f"FILTER skip [negation]: '{neg}' in '{text[:60]}'")
            return True

    if is_non_threat_context(text, normalized):
        log.debug(f"FILTER skip [non-threat-context]: '{text[:60]}'")
        return True

    has_live_threat_hint = bool(_LIVE_THREAT_HINT.search(normalized))

    # Broad safety net: long informational posts without any live-threat signal
    # should not be sent to GPT/regex where a place name can be hallucinated into
    # a marker. Short terse tracker updates are still allowed through.
    if len(normalized) > 160 and not has_live_threat_hint:
        log.debug(f"FILTER skip [long-no-live-threat]: '{text[:60]}'")
        return True

    for pat in _ADMIN_INFRA_SKIP_PATTERNS:
        if re.search(pat, normalized):
            if has_live_threat_hint:
                log.debug(
                    f"FILTER keep [live-threat overrides admin]: '{pat}' in '{text[:50]}...'"
                )
                continue
            log.debug(f"FILTER skip [admin]: '{pat}' in '{text[:60]}'")
            return True

    # Skip patterns (spam / recap / defence press — not admin-only)
    skip_patterns = [
        r'^[\s‼️!]*карта\s+повітряних\s+тривог[\s‼️!]*$',
        r'^[\s‼️!]*карта\s+тривог[\s‼️!]*$',
        r'#обстановка', r'обстановка станом', r'станом на \d{2}',
        r'станом на зараз',
        r'в повітрі\s*:', r'на даний момент в повітрі',
        r'стратегічна авіація.*не активна',
        r'збито/подавлено \d+',
        r'зафіксовано влучання',
        r'сили оборони',
        r'контрнаступальн',
        r'передислокаці',
        r'уражено склад',
        r'^\s*-1\.?\s*$',
        r'донорськ',
        r'кіно-зйомк',
        r'залучено засоби для збиття',
        r'#зведення', r'#підсумки', r'#підсумок', r'#итоги', r'#результати',
        r'не\s+треба\s+підходити',
        r'не\s+підходьте\s+до',
        r'ціллю\s+атаки\s+бул[аио]',
        r'підсумок\s+(?:за|атаки|ночі|дня)',
        r'результати\s+(?:атаки|роботи|ппо)',
        r'збито.*(?:шахед|бпла|ракет|дрон)',
        r'знищено.*(?:шахед|бпла|ракет|дрон)',
        # Planning / warning messages (future attacks, not real-time)
        r'планує\s+(?:нанесення|удар|атаку|застосування)',
        r'у\s+найближчі\s+\d+\s+(?:годин|хвилин|днів|діб)',
        r'можуть\s+бути\s+залучені',
        r'подготовк[аи]\s+к\s+пуск',
        r'пуск\w*\s+ожида\w*',
        r'ожида\w*\s+пуск',
        r'засоби\s+ураження',
        # Post-strike damage / casualty reports (not live threats)
        r'загинул\w*.*поранен',
        r'людин\w*\s+загинул',
        r'пошкоджен[іиоа]\s+(?:\d+|кілька|декілька)\s+(?:багатоквартирн|будин|приватн)',
        r'завдал[аио]\s+.*(?:масований|комбінований)\s+удар',
        r'протягом\s+(?:ночі|доби|72\s*годин)',
        r'немає\s+ознак\s+на\s+обстріл',
        r'не\s+очікуємо',
        r'петиці[яї]',
        r'\bобмін\b',
        r'\bполон[уаі]?\b',
        r'з\s+полону',
        r'повернувс[ья]\s+з\s+полону',
        r'\bсбу\b.*\bдбр\b',
        r'затримал[аи]\s+[«"“]?крот',
        # Military / tech news about drones, not live airborne threats.
        r'(?:пілот[иів]?|бійц[іів]?|військов[іий]+|підрозділ\w*|бригад[аеиіу])'
        r'.{0,120}(?:fpv[\-\s]?дрон|фпв[\-\s]?дрон|дрон\w*)'
        r'.{0,120}(?:встановил|оснастил|обладнал|саморобн|дробовик|скид|боєприпас)',
        r'(?:fpv[\-\s]?дрон|фпв[\-\s]?дрон|дрон\w*)'
        r'.{0,120}(?:встановил|оснастил|обладнал|саморобн|дробовик|скид|боєприпас)',
    ]
    for pat in skip_patterns:
        if re.search(pat, normalized):
            log.debug(f"FILTER skip [pattern]: '{pat}' in '{text[:60]}'")
            return True

    # Summary / recap message detection
    if _is_summary_message(normalized, text):
        log.debug(f"FILTER skip [summary]: '{text[:60]}'")
        return True

    # Planning / warning message detection (future attacks, not real-time)
    if _is_planning_message(normalized, text):
        log.debug(f"FILTER skip [planning]: '{text[:60]}'")
        return True

    return False


def extract_header_oblast(text: str) -> Optional[str]:
    """Extract oblast from message header (✈️Сумщина: / Харківська область:)."""
    return extract_oblast_authority(text)


def detect_allclear_keywords(text: str) -> bool:
    """
    Check if message text contains allclear keywords or emoji indicators.
    Used as safety cross-check: if regex keywords say allclear but GPT missed it,
    we force an allclear entity.
    """
    normalized = normalize_text(text)

    # Channel-specific: do not let "threat continues" heuristics suppress this
    if "ціль припинила існування" in normalized:
        return True

    # Allclear emoji indicators (🟢, ⚪, 📢)
    _ALLCLEAR_EMOJIS = {'🟢', '⚪', '📢'}
    stripped = text.strip()
    if stripped and stripped[0] in _ALLCLEAR_EMOJIS:
        return True

    # Direct keyword match
    if any(kw in normalized for kw in ALLCLEAR_KEYWORDS):
        # But check for continuation pattern (partial shootdown, threats continue)
        if re.search(r'(?:продовжу|далі|летить|летять|курс|рух на|йдуть|йде|'
                     r'залишається|залишились|решта)', normalized):
            return False  # Active threats still ongoing
        return True

    # Word-boundary keywords
    for kw, mode in ALLCLEAR_WORD_BOUNDARY.items():
        pat = r'\b' + re.escape(kw) + (r'\b' if mode == 'exact' else '')
        if re.search(pat, normalized):
            if not re.search(r'(?:продовжу|далі|летить|летять|курс|рух на|йдуть|йде|'
                             r'залишається|залишились|решта)', normalized):
                return True

    return False
