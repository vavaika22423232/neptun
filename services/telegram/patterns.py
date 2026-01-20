"""
Regex patterns for parsing Telegram messages.

Централізовані regex-патерни для парсингу повідомлень
з Telegram каналів про загрози (БПЛА, ракети, вибухи тощо).
"""
import re
from typing import Dict, List, Tuple, Pattern

# ==============================================================================
# THREAT TYPE PATTERNS
# ==============================================================================

# Ballistic missiles - highest priority, immediate danger
BALLISTIC_PATTERNS: List[Pattern] = [
    re.compile(r'балістик[аи]?\b', re.IGNORECASE),
    re.compile(r'балістичн(?:а|ий|их|ою|і)\s+(?:загроз|ракет|небезпек)', re.IGNORECASE),
    re.compile(r'загроз(?:а|и)?\s+(?:балістик|застосування)', re.IGNORECASE),
    re.compile(r'пуск\s+(?:балістик|ракет)', re.IGNORECASE),
]

# Cruise missiles
CRUISE_MISSILE_PATTERNS: List[Pattern] = [
    re.compile(r'крилат(?:а|і|их)\s+ракет', re.IGNORECASE),
    re.compile(r'КР\b', re.IGNORECASE),
    re.compile(r'(?:x-101|x-555|калібр|томагавк|kh-101|kh-555)', re.IGNORECASE),
]

# Any rockets/missiles
ROCKET_PATTERNS: List[Pattern] = [
    re.compile(r'ракет(?:а|и|у|ою|ні|ний|них)?\b', re.IGNORECASE),
    re.compile(r'(?:іскандер|точка-у|с-300|с-400)', re.IGNORECASE),
]

# UAVs / Drones / Shaheds
DRONE_PATTERNS: List[Pattern] = [
    re.compile(r'бпла\b', re.IGNORECASE),
    re.compile(r'дрон(?:и|ів|а|ом)?\b', re.IGNORECASE),
    re.compile(r'шахед(?:и|ів|а|ом)?\b', re.IGNORECASE),
    re.compile(r'shahed', re.IGNORECASE),
    re.compile(r'безпілотн(?:ик|ий|ого|их)', re.IGNORECASE),
    re.compile(r'ударн(?:ий|ого|их)\s+(?:бпла|дрон)', re.IGNORECASE),
    re.compile(r'герань?(?:\s*-?\s*\d+)?', re.IGNORECASE),
]

# KABs (Guided aerial bombs)
KAB_PATTERNS: List[Pattern] = [
    re.compile(r'каб(?:и|ів|ами)?\b', re.IGNORECASE),
    re.compile(r'(?:керован(?:а|і|их)\s+)?авіабомб', re.IGNORECASE),
    re.compile(r'(?:fab|фаб)(?:\s*-?\s*\d+)?', re.IGNORECASE),
]

# Explosions
EXPLOSION_PATTERNS: List[Pattern] = [
    re.compile(r'вибух(?:и|ів|у|нув)?', re.IGNORECASE),
    re.compile(r'(?:луна|звук)\s+вибух', re.IGNORECASE),
    re.compile(r'пролунав', re.IGNORECASE),
    re.compile(r'детонаці[яї]', re.IGNORECASE),
]

# Air alarms
ALARM_PATTERNS: List[Pattern] = [
    re.compile(r'повітрян(?:а|ий|ої)\s+тривог', re.IGNORECASE),
    re.compile(r'тривог(?:а|и|у)\s+(?:оголошен|повітрян)', re.IGNORECASE),
    re.compile(r'🚨\s*тривог', re.IGNORECASE),
]

# All clear / Alarm ended
ALL_CLEAR_PATTERNS: List[Pattern] = [
    re.compile(r'відбій(?:\s+тривоги)?', re.IGNORECASE),
    re.compile(r'відміна\s+(?:тривоги|загрози)', re.IGNORECASE),
    re.compile(r'тривогу?\s+(?:знят|скасован|відмін)', re.IGNORECASE),
    re.compile(r'загроз(?:а|у)?\s+(?:минул|знят)', re.IGNORECASE),
    re.compile(r'✅\s*(?:відбій|знято)', re.IGNORECASE),
]

# MiG takeoff warnings
MIG_PATTERNS: List[Pattern] = [
    re.compile(r'(?:міг|миг|mig)(?:\s*-?\s*31)?', re.IGNORECASE),
    re.compile(r'(?:зліт|взліт)\s+(?:міг|мигів|тактичної)', re.IGNORECASE),
    re.compile(r'тактичн(?:а|ої)\s+авіаці', re.IGNORECASE),
]

# ==============================================================================
# COURSE / DIRECTION PATTERNS
# ==============================================================================

# "БпЛА курсом з [source] на [target]"
COURSE_FROM_TO: Pattern = re.compile(
    r'(?:бпла|дрон|шахед)\s+.*?курс(?:ом)?\s+з\s+([а-яіїєё\s\-\']+?)\s+на\s+([а-яіїєё\s\-\']+?)(?:\s|$|[,\.\!])',
    re.IGNORECASE
)

# "БпЛА курсом на [target] з [source]"
COURSE_TO_FROM: Pattern = re.compile(
    r'(?:бпла|дрон|шахед)\s+.*?курс(?:ом)?\s+на\s+([а-яіїєё\s\-\']+?)\s+з\s+([а-яіїєё\s\-\']+?)(?:\s|$|[,\.\!])',
    re.IGNORECASE
)

# "БпЛА з [source] курсом на [target]"
COURSE_SOURCE_TO: Pattern = re.compile(
    r'(?:бпла|дрон|шахед)\s+з\s+([а-яіїєё\s\-\']+?)\s+курс(?:ом)?\s+на\s+([а-яіїєё\s\-\']+?)(?:\s|$|[,\.\!])',
    re.IGNORECASE
)

# "БпЛА з [source] у напрямку [target]"
COURSE_SOURCE_DIRECTION: Pattern = re.compile(
    r'(?:бпла|дрон|шахед)\s+з\s+([а-яіїєё\s\-\']+?)\s+у\s+напрямк[уи]\s+([а-яіїєё\s\-\']+?)(?:\s|$|[,\.\!])',
    re.IGNORECASE
)

# "БпЛА курсом на [target]" (target only)
COURSE_TARGET_ONLY: Pattern = re.compile(
    r'(?:бпла|дрон|шахед)\s+.*?курс(?:ом)?\s+на\s+([а-яіїєё\s\-\']+?)(?=\s*(?:\n|$|[,\.\!\?;]))',
    re.IGNORECASE
)

# "[count]х БпЛА курс [source]-[target]"
COURSE_DASH: Pattern = re.compile(
    r'\d*х?\s*(?:бпла|дрон|шахед)\s+курс\s+([а-яіїєё\s\-\']+?)\s*[-–—]\s*([а-яіїєё\s\-\']+?)(?:\s|$|[,\.\!])',
    re.IGNORECASE
)

# All course patterns in order of specificity
COURSE_PATTERNS: List[Tuple[str, Pattern, Tuple[int, int]]] = [
    ('from_to', COURSE_FROM_TO, (0, 1)),        # source, target
    ('to_from', COURSE_TO_FROM, (1, 0)),        # target, source -> swap
    ('source_to', COURSE_SOURCE_TO, (0, 1)),    # source, target
    ('source_dir', COURSE_SOURCE_DIRECTION, (0, 1)),  # source, target
    ('target_only', COURSE_TARGET_ONLY, (-1, 0)),     # no source, target
    ('dash', COURSE_DASH, (0, 1)),              # source, target
]


# ==============================================================================
# LOCATION EXTRACTION PATTERNS
# ==============================================================================

# Oblast extraction
OBLAST_PATTERN: Pattern = re.compile(
    r'([\w\-]+(?:ська|ький|ка)\s*область)',
    re.IGNORECASE
)

# District extraction  
DISTRICT_PATTERN: Pattern = re.compile(
    r'([\w\-]+(?:ський|ська|ське)\s*район)',
    re.IGNORECASE
)

# City/settlement extraction (near/in/over patterns)
CITY_PATTERNS: List[Pattern] = [
    # над містом X
    re.compile(r'над\s+(?:містом\s+)?([А-ЯІЇЄа-яіїє][а-яіїє\'\-]+)', re.IGNORECASE),
    # в районі X
    re.compile(r'в\s+район[іу]\s+([А-ЯІЇЄа-яіїє][а-яіїє\'\-]+)', re.IGNORECASE),
    # біля X
    re.compile(r'біля\s+([А-ЯІЇЄа-яіїє][а-яіїє\'\-]+)', re.IGNORECASE),
    # поблизу X
    re.compile(r'поблизу\s+([А-ЯІЇЄа-яіїє][а-яіїє\'\-]+)', re.IGNORECASE),
    # на X (direction)
    re.compile(r'на\s+([А-ЯІЇЄа-яіїє][а-яіїє\'\-]+)', re.IGNORECASE),
]


# ==============================================================================
# COUNT PATTERNS (для "2х БПЛА", "3 ракети" тощо)
# ==============================================================================

COUNT_PATTERNS: List[Pattern] = [
    re.compile(r'(\d+)\s*[xхX]\s*(?:бпла|дрон|шахед)', re.IGNORECASE),
    re.compile(r'(\d+)\s*(?:бпла|дрон|шахед)', re.IGNORECASE),
    re.compile(r'(?:група|групи)\s+(?:з\s+)?(\d+)', re.IGNORECASE),
    re.compile(r'(\d+)\s*(?:ворожих|ударних)?\s*(?:бпла|дрон)', re.IGNORECASE),
]


# ==============================================================================
# DIRECTION MAPPING (Ukrainian -> Cardinal)
# ==============================================================================

DIRECTION_MAP: Dict[str, str] = {
    # Full names
    'північ': 'N',
    'північний': 'N',
    'південь': 'S',
    'південний': 'S',
    'схід': 'E',
    'східний': 'E',
    'захід': 'W',
    'західний': 'W',
    
    # Compound directions
    'північно-східний': 'NE',
    'північно-східний': 'NE',
    'північно-західний': 'NW',
    'південно-східний': 'SE',
    'південно-західний': 'SW',
    
    # Abbreviated
    'пн': 'N',
    'пд': 'S',
    'сх': 'E',
    'зх': 'W',
    'пн-сх': 'NE',
    'пн-зх': 'NW',
    'пд-сх': 'SE',
    'пд-зх': 'SW',
}

# Reverse mapping for display
DIRECTION_MAP_REVERSE: Dict[str, str] = {
    'N': 'Північ',
    'S': 'Південь',
    'E': 'Схід',
    'W': 'Захід',
    'NE': 'Північний схід',
    'NW': 'Північний захід',
    'SE': 'Південний схід',
    'SW': 'Південний захід',
}


# ==============================================================================
# NOISE WORDS (to filter from extracted locations)
# ==============================================================================

NOISE_WORDS: set = {
    'область', 'обл', 'район', 'р-н', 'на', 'з', 'від', 'до',
    'курсом', 'напрямку', 'напрямок', 'через', 'біля', 'над',
    'громада', 'місто', 'село', 'селище', 'смт',
}


# ==============================================================================
# EMOJI PATTERNS (for cleaning text)
# ==============================================================================

EMOJI_PATTERN: Pattern = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F700-\U0001F77F"  # alchemical
    "\U0001F780-\U0001F7FF"  # geometric
    "\U0001F800-\U0001F8FF"  # supplemental arrows
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess
    "\U0001FA70-\U0001FAFF"  # symbols extended
    "\U00002702-\U000027B0"  # dingbats
    "\U0001F926-\U0001F937"  # gestures
    "]+",
    flags=re.UNICODE
)


# ==============================================================================
# CONVENIENCE CLASS FOR TESTING
# ==============================================================================

class ThreatPatterns:
    """Compiled patterns for threat detection - for easy import."""
    
    SHAHED = re.compile(
        r'шахед|дрон|бпла|безпілотн|камікадзе|герань',
        re.IGNORECASE
    )
    
    MISSILE = re.compile(
        r'ракет|балістик|крилат|калібр|кінжал|іскандер|х-101|х-22',
        re.IGNORECASE
    )
    
    LOCATION = re.compile(
        r'(?:над|біля|в|у|до|через|поблизу)\s+([А-ЯІЇЄҐа-яіїєґ\'\-]+(?:ськ[аоіий]+)?)',
        re.IGNORECASE
    )
    
    DIRECTION = re.compile(
        r'(?:курс(?:ом)?|напрям(?:ок|ку)?|рух(?:ається)?)\s+(?:на|до|в)\s+([А-ЯІЇЄҐа-яіїєґ\'\-\s]+)',
        re.IGNORECASE
    )
    
    REGION = re.compile(
        r'([А-ЯІЇЄҐа-яіїєґ]+ськ[аоіий]+)\s+(?:област|район)',
        re.IGNORECASE
    )
    
    COUNT = re.compile(
        r'(\d+)\s*(?:од\.?|одиниц|шт\.?|штук|дрон|шахед|бпла)',
        re.IGNORECASE
    )
    
    ALTITUDE = re.compile(
        r'(?:висот[аі]|altitude)\s*[-:]?\s*(\d+)\s*(?:м|метр|m)',
        re.IGNORECASE
    )
    
    SPEED = re.compile(
        r'(?:швидкіст[ьі]|speed)\s*[-:]?\s*(\d+)\s*(?:км|km)',
        re.IGNORECASE
    )


# ==============================================================================
# THREAT_PATTERNS - Dictionary of patterns for string matching
# ==============================================================================

THREAT_PATTERNS: Dict[str, List[str]] = {
    'shahed': ['шахед', 'shahed', 'герань', 'бпла', 'дрон', 'безпілотн', 'камікадзе'],
    'missile': ['ракет', 'крилат'],
    'ballistic': ['балістик', 'іскандер', 'кінжал'],
    'drone': ['дрон', 'бпла', 'безпілотн'],
    'kab': ['каб', 'авіабомб', 'fab', 'фаб'],
    'explosion': ['вибух', 'детонаці', 'пролунав'],
    'alarm': ['тривог', 'повітрян'],
}
