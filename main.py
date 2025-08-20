# Центры областей Украины (можно расширять)
OBLAST_CENTERS = {
    'черниговская': (51.4982, 31.2893),
    'чернігівська': (51.4982, 31.2893),
    'киевская': (50.4501, 30.5234),
    'київська': (50.4501, 30.5234),
    'одесская': (46.4825, 30.7233),
    'одеська': (46.4825, 30.7233),
    'львовская': (49.8397, 24.0297),
    'львівська': (49.8397, 24.0297),
    'харьковская': (49.9935, 36.2304),
    'харківська': (49.9935, 36.2304),
    'днепропетровская': (48.4647, 35.0462),
    'дніпропетровська': (48.4647, 35.0462),
    'запорожская': (47.8388, 35.1396),
    'запорізька': (47.8388, 35.1396),
    'миколаївська': (46.9750, 31.9946),
    'николаевская': (46.9750, 31.9946),
    # ... остальные области ...
}
import langdetect
try:
    from deeppavlov import build_model, configs
    dp_ner = build_model(configs.ner.ner_ontonotes_bert_mult, download=True)
except Exception:
    dp_ner = None
import json
import asyncio
import time
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, jsonify, request
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import re
import aiohttp
import ssl
import googlemaps
import threading
from unidecode import unidecode
import spacy
import os
import math
import pickle
import hashlib
import logging
import random
import functools
from collections import defaultdict
import subprocess
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from deep_translator import GoogleTranslator
import openai
import pytz

# Настройки
api_id = 24031340
api_hash = '2daaa58652e315ce52adb1090313d36a'
channel_usernames = ['UkraineAlarmSignal', 'war_monitor', 'kpszsu', 'napramok', 'kudy_letyt', 'AerisRimor']
# GOOGLE_MAPS_API_KEY = 'AIzaSyB7iVZpFP8-8e3-OAdawEGpp2or6PQwMgU'
# gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
OPENCAGE_API_KEY = os.environ.get('OPENCAGE_API_KEY', '')

os.environ["OPENAI_API_KEY"] = os.environ.get('OPENAI_API_KEY', '')

client = TelegramClient('anon', api_id, api_hash)
app = Flask(__name__)

# Настройка логирования
import os
DATA_DIR = os.environ.get('DATA_DIR', '/data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)
LOG_PATH = os.path.join(DATA_DIR, 'app.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Приоритетные локации с координатами
PRIORITY_LOCATIONS = {
    # Велика Писарівка (Сумська область)
    "велика писарівка": (50.4264, 35.4848),
    # Областные центры
    "київ": (50.4501, 30.5234),
    "одеса": (46.4825, 30.7233),
    "львів": (49.8397, 24.0297),
    "харків": (49.9935, 36.2304),
    "дніпро": (48.4647, 35.0462),
    "запоріжжя": (47.8388, 35.1396),
    "миколаїв": (46.9750, 31.9946),
    "херсон": (46.6354, 32.6169),
    "хмельницький": (49.4229, 26.9873),
    "чернігів": (51.4982, 31.2893),
    "черкаси": (49.4444, 32.0597),
    "суми": (50.9077, 34.7981),
    "полтава": (49.5884, 34.5514),
    "житомир": (50.2547, 28.6587),
    "рівне": (50.6199, 26.2516),
    "луцьк": (50.7472, 25.3254),
    "тернопіль": (49.5535, 25.5947),
    "вінниця": (49.2328, 28.4810),
    "івано-франківськ": (48.9226, 24.7111),
    "ужгород": (48.6208, 22.2879),
    "чернівці": (48.2917, 25.9354),
    "кропивницький": (48.5079, 32.2623),
    "біла церква": (49.8094, 30.1121),
    "обухів": (50.1072, 30.6181),
    "святошино": (50.4561, 30.3554),
    "троєщина": (50.5122, 30.6297),
    "лісовий масив": (50.4747, 30.6566),
    "дврз": (50.4542, 30.6706),
    "оболонь": (50.5167, 30.4981),
    "дарниця": (50.4500, 30.6333),
    "осокорки": (50.3872, 30.6292),
    "жуляни": (50.4017, 30.4431),
    "гостомель": (50.5833, 30.2667),
    "шулявка": (50.4567, 30.4431),
    "нивки": (50.4581, 30.4106),
    "вишневе": (50.3833, 30.3667),
    "борщагівка": (50.4292, 30.3556),
    "мінський масив": (50.5150, 30.4640),
    # Ключевые военные объекты
    "очаків": (46.6158, 31.5400),
    "енергодар": (47.4989, 34.6578),
    "чаплинка": (46.3625, 33.5308),
    "генічеськ": (46.1711, 34.8164),
    "бердянськ": (46.7550, 36.7889),
    "мелітополь": (46.8480, 35.3653),
    "мариуполь": (47.0971, 37.5434),
    "бахмут": (48.5956, 38.0000),
    "соледар": (48.6797, 38.0897),
    "авдіївка": (48.1394, 37.7442),
    "краматорськ": (48.7386, 37.5844),
    "славут": (50.3011, 26.8728),
    "яворів": (49.9386, 23.3906),
    "канів": (49.7500, 31.4667),
    
    # Дополнительные важные локации
    "чаплинка": (46.3625, 33.5308),
    "генічеськ": (46.1711, 34.8164),
    "очаков": (46.6158, 31.5400),
    "бердянск": (46.7550, 36.7889),
    "мелитополь": (46.8480, 35.3653),
    "оріхів": (47.5678, 35.7858),
    "полог": (47.4833, 36.2500),
    "гуляйполе": (47.6667, 36.2667),
    "василівка": (47.4333, 35.2833),
    "томак": (47.8167, 34.7667),
    "приморськ": (46.6500, 36.3500),
    "приазовське": (46.7333, 35.6500),
    "якимівка": (46.7000, 35.1667),
    "веселе": (47.0167, 34.9167),
    "більмак": (47.3500, 36.4667),
    "чернігівка": (47.2000, 36.2000),
    "куйбишеве": (47.3667, 37.2000),
    "новоазовськ": (47.1167, 38.0833),
    "волноваха": (47.6010, 37.4967),
    "покровськ": (48.2814, 37.1758),
    "купянськ": (49.7064, 37.6167),
    "изюм": (49.2122, 37.2569),
    "лиман": (48.9892, 37.8022),
    "синельникове": (48.3178, 35.5119),
    "павлоград": (48.5200, 35.8700),
    "кривий ріг": (47.9105, 33.3918),
    "суми": (50.9077, 34.7981),
    "конотоп": (51.2403, 33.2026),
    "шостка": (51.8667, 33.4833),
    "рівне": (50.6199, 26.2516),
    "дубно": (50.4000, 25.7500),
    "кременець": (50.1000, 25.7333),
    "чортків": (49.0167, 25.8000),
    
    # Синонимы
    "одесса": (46.4825, 30.7233),
    "киев": (50.4501, 30.5234),
    "львов": (49.8397, 24.0297),
    "харьков": (49.9935, 36.2304),
    "днепр": (48.4647, 35.0462),
    "николаев": (46.9750, 31.9946),
    "херсон": (46.6354, 32.6169),
    "ровно": (50.6199, 26.2516),
    "ивано-франківск": (48.9226, 24.7111),
    "ужгород": (48.6208, 22.2879),
    "черновцы": (48.2917, 25.9354),
    "чаплынка": (46.3625, 33.5308),
    "геническ": (46.1711, 34.8164),
    "очаков": (46.6158, 31.5400),
    "бердянск": (46.7550, 36.7889),
    "мелитополь": (46.8480, 35.3653),
    
    # Черное море
    "чорне море": (44.8, 33.5),
    "черное море": (44.8, 33.5),
    "black sea": (44.8, 33.5),
    "акватория чорного моря": (44.8, 33.5),
    "акватория черного моря": (44.8, 33.5),
    "акватория black sea": (44.8, 33.5),
    # Добавлено для корректного отображения в море
    "чорноморський біосферний заповідник": (45.5, 30.5),
    "черноморский биосферный заповедник": (45.5, 30.5),
    
    # Новые приоритетные локации
    "південне": (46.6667, 31.2333),  # Южное, Одесская область, побережье
    "коблево": (46.6247, 31.2022),  # Коблево, побережье
    # Локації за межами України
    "енгельс-2": (51.4778, 46.2106),  # Аеродром Енгельс-2, Росія
    "энгельс-2": (51.4778, 46.2106),  # Аэродром Энгельс-2, Россия
    # Аэродром Балтимор (Воронеж, Россия)
    "балтимор": (51.6717, 39.2006),  # Аеродром Балтимор, Воронеж, Россия
    "baltimor": (51.6717, 39.2006),  # translit
    "воронеж": (51.6615, 39.2003),  # город Воронеж, Россия
}

# Приоритетные топонимы для Днепропетровской и Запорожской областей
DNZP_PRIORITY = {
    "славгород": "Дніпропетровська область",
    "чаплі": "Дніпропетровська область",
    "грізне": "Дніпропетровська область",
    "придніпровський": "Дніпропетровська область",
    "ігрен": "Дніпропетровська область",
    "солоне": "Дніпропетровська область",
    "покровське": "Дніпропетровська область",
    "письменне": "Дніпропетровська область",
    "синельникове": "Дніпропетровська область",
    "звоницьке": "Дніпропетровська область",
    "петрівське": "Дніпропетровська область",
    "зелений гай": "Дніпропетровська область",
    "запоріжжя": "Запорізька область",
    "придніпрянське": "Запорізька область",
    "космос": "Запорізька область",
    "шевчік": "Запорізька область",
    "заводський": "Запорізька область",
}

# Загрузка spaCy модели
try:
    nlp_uk = spacy.load("uk_core_news_sm")
    logger.info("spaCy Ukrainian model loaded successfully")
except Exception as e:
    nlp_uk = None
    logger.warning(f"spaCy Ukrainian model not found: {e}. Run: python -m spacy download uk_core_news_sm")

# Загрузка HuggingFace NER pipeline (украинский/русский)
try:
    hf_tokenizer = AutoTokenizer.from_pretrained("ukr-models/xlm-roberta-base-finetuned-uk-ner")
    hf_model = AutoModelForTokenClassification.from_pretrained("ukr-models/xlm-roberta-base-finetuned-uk-ner")
    hf_ner = pipeline("ner", model=hf_model, tokenizer=hf_tokenizer, aggregation_strategy="simple")
    logger.info("HuggingFace NER model loaded successfully")
except Exception as e:
    hf_ner = None
    logger.warning(f"HuggingFace NER model not loaded: {e}")

# Кэш для геокодирования
GEOCODING_CACHE = {}
GEOCODING_CACHE_FILE = 'geocoding_cache.json'

def load_geocoding_cache():
    if os.path.exists(GEOCODING_CACHE_FILE):
        try:
            with open(GEOCODING_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_geocoding_cache():
    with open(GEOCODING_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(GEOCODING_CACHE, f, ensure_ascii=False)

# Загружаем кэш при старте
GEOCODING_CACHE = load_geocoding_cache()

SYNONYM_MAP = {
    # Украинские ↔ Русские ↔ Транслит
    'київ': 'киев', 'kyiv': 'киев', 'kiev': 'киев',
    'одеса': 'одесса', 'odesa': 'одесса',
    'львів': 'львов', 'lviv': 'львов',
    'харків': 'харьков', 'kharkiv': 'харьков',
    'дніпро': 'днепр', 'dnipro': 'днепр',
    'миколаїв': 'николаев', 'mykolaiv': 'николаев',
    'чернівці': 'черновцы', 'chernivtsi': 'черновцы',
    'івано-франківськ': 'ивано-франковск', 'ivano-frankivsk': 'ивано-франковск',
    'ужгород': 'ужгород', 'uzhhorod': 'ужгород',
    'рівне': 'ровно', 'rivne': 'ровно',
    'луцьк': 'луцк', 'lutsk': 'луцк',
    'тернопіль': 'тернополь', 'ternopil': 'тернополь',
    'черкаси': 'черкассы', 'cherkasy': 'черкассы',
    'житомир': 'житомир', 'zhytomyr': 'житомир',
    'вінниця': 'винница', 'vinnytsia': 'винница',
    'суми': 'суми', 'sumy': 'суми',
    'полтава': 'полтава', 'poltava': 'полтава',
    'херсон': 'херсон', 'kherson': 'херсон',
    'запоріжжя': 'запорожье', 'zaporizhzhia': 'запорожье',
    'кропивницький': 'кировоград', 'kropyvnytskyi': 'кировоград',
    'чернігів': 'чернигов', 'chernihiv': 'чернигов',
    'маріуполь': 'мариуполь', 'mariupol': 'мариуполь',
    'бахмут': 'бахмут', 'bakhmut': 'бахмут',
    'соледар': 'соледар', 'soledar': 'соледар',
    'авдіївка': 'авдеевка', 'avdiivka': 'авдеевка',
    'краматорськ': 'краматорск', 'kramatorsk': 'краматорск',
    'енергодар': 'энергодар', 'enerhodar': 'энергодар',
    'мелітополь': 'мелитополь', 'melitopol': 'мелитополь',
    'бердянськ': 'бердянск', 'berdyansk': 'бердянск',
    'генічеськ': 'геническ', 'henichesk': 'геническ',
    'очаків': 'очаков', 'ochakiv': 'очаков',
    'чаплинка': 'чаплынка', 'chaplynka': 'чаплынка',
    # ... можно расширять ...
}

# Расширенный словарь синонимов и сокращений
SYNONYM_MAP.update({
    'днiпро': 'днепр', 'днiпропетровськ': 'днепр',
    'киевская': 'киев', 'київська': 'киев',
    'одесская': 'одесса', 'одеська': 'одесса',
    'львовская': 'львов', 'львівська': 'львов',
    'харьковская': 'харьков', 'харківська': 'харьков',
    'днепропетровск': 'днепр', 'дніпропетровськ': 'днепр',
    'запорожская': 'запорожье', 'запорізька': 'запорожье',
    'черниговская': 'чернигов', 'чернігівська': 'чернигов',
    'винницкая': 'винница', 'вінницька': 'винница',
    'житомирская': 'житомир', 'житомирська': 'житомир',
    'черкасская': 'черкассы', 'черкаська': 'черкассы',
    'полтавская': 'полтава', 'полтавська': 'полтава',
    'сумская': 'суми', 'сумська': 'суми',
    'херсонская': 'херсон', 'херсонська': 'херсон',
    'миколаївська': 'николаев', 'николаевская': 'николаев',
    'ивано-франковская': 'ивано-франковск', 'івано-франківська': 'ивано-франковск',
    'луганская': 'луганск', 'луганська': 'луганск',
    'донецкая': 'донецк', 'донецька': 'донецк',
    'крым': 'крым', 'crimea': 'крым',
    'кировоградская': 'кировоград', 'кропивницкий': 'кировоград',
    'черновицкая': 'черновцы', 'чернівецька': 'черновцы',
    'тернопольская': 'тернополь', 'тернопільська': 'тернополь',
    'волынская': 'луцк', 'волинська': 'луцк',
    'закарпатская': 'ужгород', 'закарпатська': 'ужгород',
    'ровенская': 'ровно', 'рівненська': 'ровно',
    'хмельницкая': 'хмельницкий', 'хмельницька': 'хмельницкий',
    'черноморск': 'ильичевск', 'чорноморськ': 'ильичевск',
    'ильичевск': 'ильичевск',
    # ... можно расширять ...
})

# Исправляем normalize_place_name
def normalize_place_name(name):
    """Нормализует название места для сравнения, учитывая синонимы и транслитерацию"""
    # Функция очистки названия от артефактов
    def clean_name(n):
        n = n.lower().strip()
        n = re.sub(r'\s+', ' ', n)  # множественные пробелы
        n = n.replace('`', "'")  # разные апострофы
        n = n.replace('´', "'")
        n = n.replace('"', "'")
        n = re.sub(r'[\(\)\[\]\{\}]', '', n)  # скобки
        return n

    name = clean_name(unidecode(name))
    
    # Убираем суффиксы районов/областей
    suffixes = ['район', 'область', 'обл.', 'р-н', 'міськрада', 'мр', 'отг', 'тг', 'громада']
    for suffix in suffixes:
        if name.endswith(' ' + suffix):
            name = name.replace(' ' + suffix, '').strip()
    
    # Убираем префиксы
    prefixes = ['місто', 'село', 'селище', 'смт', 'м.', 'с.', 'сел.']
    for prefix in prefixes:
        if name.startswith(prefix + ' '):
            name = name.replace(prefix + ' ', '', 1).strip()

    # Исправляем типичные опечатки
    fixes = {
        'киів': 'київ',
        'кіев': 'київ', 
        'днепр': 'дніпро',
        'днiпро': 'дніпро',
        'запорожье': 'запоріжжя',
        'запоріжжа': 'запоріжжя',
        'харьков': 'харків',
        'николаев': 'миколаїв',
        'миколаів': 'миколаїв'
    }
    name = fixes.get(name, name)
    
    # Применяем синонимы
    if name in SYNONYM_MAP:
        name = SYNONYM_MAP[name]
    return name

# Автоматическая подстановка региона для известных городов
CITY_TO_REGION = {
    'велика писарівка': 'Сумська область',
    'київ': 'Київська область',
    'киев': 'Київська область',
    'одеса': 'Одеська область',
    'одесса': 'Одеська область',
    'львів': 'Львівська область',
    'львов': 'Львівська область',
    'харків': 'Харківська область',
    'харьков': 'Харківська область',
    'дніпро': 'Дніпропетровська область',
    'днепр': 'Дніпропетровська область',
    'запоріжжя': 'Запорізька область',
    'запорожье': 'Запорізька область',
    'вінниця': 'Вінницька область',
    'винница': 'Вінницька область',
    'житомир': 'Житомирська область',
    'черкаси': 'Черкаська область',
    'черкассы': 'Черкаська область',
    'полтава': 'Полтавська область',
    'суми': 'Сумська область',
    'херсон': 'Херсонська область',
    'миколаїв': 'Миколаївська область',
    'николаев': 'Миколаївська область',
    'івано-франківськ': 'Івано-Франківська область',
    'ивано-франковск': 'Івано-Франківська область',
    'луцьк': 'Волинська область',
    'луцк': 'Волинська область',
    'ужгород': 'Закарпатська область',
    'рівне': 'Рівненська область',
    'ровно': 'Рівненська область',
    'тернопіль': 'Тернопільська область',
    'тернополь': 'Тернопільська область',
    'чернівці': 'Чернівецька область',
    'черновцы': 'Чернівецька область',
    'чернігів': 'Чернігівська область',
    'чернигов': 'Чернігівська область',
    'хмельницький': 'Хмельницька область',
    'хмельницкий': 'Хмельницька область',
    'кропивницький': 'Кіровоградська область',
    'кропивницкий': 'Кіровоградська область',
    # Важные города
    'біла церква': 'Київська область',
    'белая церковь': 'Київська область',
    'бердичів': 'Житомирська область',
    'бердичев': 'Житомирська область',
    'кременчук': 'Полтавська область',
    'кременчуг': 'Полтавська область',
    'кривий ріг': 'Дніпропетровська область',
    'кривой рог': 'Дніпропетровська область',
    'маріуполь': 'Донецька область',
    'мариуполь': 'Донецька область',
    'мелітополь': 'Запорізька область',
    'мелитополь': 'Запорізька область',
    'бердянськ': 'Запорізька область',
    'бердянск': 'Запорізька область',
    'ізмаїл': 'Одеська область',
    'измаил': 'Одеська область',
    'умань': 'Черкаська область',
    'умань': 'Черкаська область',
    'ніжин': 'Чернігівська область',
    'нежин': 'Чернігівська область',
    'конотоп': 'Сумська область',
    'коростень': 'Житомирська область',
    'новоград-волинський': 'Житомирська область',
    'новоград-волынский': 'Житомирська область',
    'ковель': 'Волинська область',
    'мукачево': 'Закарпатська область',
    'дрогобич': 'Львівська область',
    'дрогобыч': 'Львівська область',
    'стрий': 'Львівська область',
    'стрый': 'Львівська область',
    'червоноград': 'Львівська область',
    'червоноград': 'Львівська область',
    'калуш': 'Івано-Франківська область',
    'коломия': 'Івано-Франківська область',
    'новодністровськ': 'Чернівецька область',
    'новоднестровск': 'Чернівецька область',
    'каховка': 'Херсонська область',
    'нова каховка': 'Херсонська область',
    'новая каховка': 'Херсонська область',
    'первомайськ': 'Миколаївська область',
    'первомайск': 'Миколаївська область',
    'южноукраїнськ': 'Миколаївська область',
    'южноукраинск': 'Миколаївська область',
    'вознесенськ': 'Миколаївська область',
    'вознесенск': 'Миколаївська область',
    'олександрія': 'Кіровоградська область',
    'александрия': 'Кіровоградська область',
    'світловодськ': 'Кіровоградська область',
    'светловодск': 'Кіровоградська область',
    'знам`янка': 'Кіровоградська область',
    'знаменка': 'Кіровоградська область',
    'павлоград': 'Дніпропетровська область',
    'нікополь': 'Дніпропетровська область',
    'никополь': 'Дніпропетровська область',
    'новомосковськ': 'Дніпропетровська область',
    'новомосковск': 'Дніпропетровська область',
    'кам`янське': 'Дніпропетровська область',
    'каменское': 'Дніпропетровська область',
    'лозова': 'Харківська область',
    'лозовая': 'Харківська область',
    'ізюм': 'Харківська область',
    'изюм': 'Харківська область',
    'чугуїв': 'Харківська область',
    'чугуев': 'Харківська область',
    'бахмут': 'Донецька область',
    'краматорськ': 'Донецька область',
    'краматорск': 'Донецька область',
    'слов`янськ': 'Донецька область',
    'славянск': 'Донецька область',
    'покровськ': 'Донецька область',
    'покровск': 'Донецька область',
    'костянтинівка': 'Донецька область',
    'константиновка': 'Донецька область',
    'авдіївка': 'Донецька область',
    'авдеевка': 'Донецька область',
    'сєвєродонецьк': 'Луганська область',
    'северодонецк': 'Луганська область',
    'лисичанськ': 'Луганська область',
    'лисичанск': 'Луганська область',
    'рубіжне': 'Луганська область',
    'рубежное': 'Луганська область',
    'енергодар': 'Запорізька область',
    'энергодар': 'Запорізька область'
}

def get_region_for_place(place):
    norm = normalize_place_name(place)
    return CITY_TO_REGION.get(norm)

def normalize_place_name(name):
    """Нормализует название места для сравнения, учитывая синонимы и транслитерацию"""
    # Функция очистки названия от артефактов
    def clean_name(n):
        n = n.lower().strip()
        n = re.sub(r'\s+', ' ', n)  # множественные пробелы
        n = n.replace('`', "'")  # разные апострофы
        n = n.replace('´', "'")
        n = n.replace("'", "'")
        n = re.sub(r'[\(\)\[\]\{\}]', '', n)  # скобки
        return n

    name = clean_name(unidecode(name))
    
    # Убираем суффиксы районов/областей
    suffixes = ['район', 'область', 'обл.', 'р-н', 'міськрада', 'мр', 'отг', 'тг', 'громада']
    for suffix in suffixes:
        if name.endswith(' ' + suffix):
            name = name.replace(' ' + suffix, '').strip()
    
    # Убираем префиксы
    prefixes = ['місто', 'село', 'селище', 'смт', 'м.', 'с.', 'сел.']
    for prefix in prefixes:
        if name.startswith(prefix + ' '):
            name = name.replace(prefix + ' ', '', 1).strip()

    # Исправляем типичные опечатки
    fixes = {
        'киів': 'київ',
        'кіев': 'київ',
        'днепр': 'дніпро',
        'днiпро': 'дніпро',
        'запорожье': 'запоріжжя',
        'запоріжжа': 'запоріжжя',
        'харьков': 'харків',
        'николаев': 'миколаїв',
        'миколаів': 'миколаїв'
    }
    name = fixes.get(name, name)
    
    # Применяем синонимы
    if name in SYNONYM_MAP:
        name = SYNONYM_MAP[name]
    return name

def load_manual_coords():
    path = 'manual_coords.json'
    if not os.path.exists(path):
        return {}
    coords = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                rec = json.loads(line)
                place = rec.get('place')
                coord = rec.get('coord')
                if place and coord:
                    lat, lng = map(float, coord.split(','))
                    coords[normalize_place_name(place)] = (lat, lng)
            except Exception:
                continue
    return coords

MANUAL_COORDS = load_manual_coords()

def threat_analyzer(text):
    """
    Анализирует текст и возвращает тип угрозы и степень (count/confidence).
    Использует ансамбль: эвристика, ML, LLM (если доступно).
    """
    t = text.lower()
    # 1. Эвристика по ключевым словам
    threat_types = [
        ("shahed", ["шахед", "shahed", "дрон", "бпла", "герой-2", "герaнь", "герань", "uav", "drone"]),
        ("raketa", ["ракета", "кр", "крылатая", "крылата", "крм", "missile", "rocket", "рк", "ркк", "ркм", "ркб"]),
        ("avia", ["авиация", "авіація", "авиаудар", "авіаудар", "літак", "самолет", "aircraft", "airstrike"]),
        ("pvo", ["пво", "зрк", "зенит", "зеніт", "s-300", "s300", "s-400", "s400", "buk", "бук", "patriot", "патриот"]),
        ("artillery", ["артилерія", "артиллерия", "артобстрел", "артобстріл", "обстрел", "shelling", "minomet", "миномет", "mortair"]),
        ("mlrs", ["рсзо", "град", "ураган", "смерч", "mlrs", "himars", "tornado", "торнадо"]),
        ("explosion", ["взрыв", "вибух", "explosion", "детонация", "детонація"]),
        ("landing", ["десант", "высадка", "висадка", "landing"]),
        ("navy", ["корабль", "корабель", "фрегат", "флот", "морской", "морська", "navy", "ship", "submarine", "підводний човен"]),
        ("unknown", ["невідомо", "неизвестно", "unknown", "не встановлено", "не встановлена"])
    ]
    for typ, keys in threat_types:
        for k in keys:
            if k in t:
                return {"type": typ, "confidence": 0.95}
    # 2. ML/LLM классификация (если доступно)
    try:
        # openai>=1.0.0 API
        if hasattr(openai, 'chat') and hasattr(openai.chat, 'completions'):
            prompt = f"Определи тип угрозы (ракета, шахед/дрон, авиация, артиллерия, ПВО, взрыв, десант, корабль, неизвестно) для сообщения: {text}\nОтвет только одним словом на русском или английском."
            resp = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=8, temperature=0.1
            )
            typ = resp.choices[0].message.content.strip().lower()
            if "шахед" in typ or "drone" in typ:
                return {"type": "shahed", "confidence": 0.8}
            if "ракета" in typ or "missile" in typ or "rocket" in typ:
                return {"type": "raketa", "confidence": 0.8}
            if "авиа" in typ or "air" in typ or "plane" in typ:
                return {"type": "avia", "confidence": 0.8}
            if "арт" in typ or "artil" in typ or "shell" in typ:
                return {"type": "artillery", "confidence": 0.8}
            if "пво" in typ or "patriot" in typ or "s-300" in typ or "s-400" in typ:
                return {"type": "pvo", "confidence": 0.8}
            if "взрыв" in typ or "explosion" in typ:
                return {"type": "explosion", "confidence": 0.8}
            if "десант" in typ or "landing" in typ:
                return {"type": "landing", "confidence": 0.8}
            if "кораб" in typ or "navy" in typ or "ship" in typ:
                return {"type": "navy", "confidence": 0.8}
            if "неизвестно" in typ or "unknown" in typ:
                return {"type": "unknown", "confidence": 0.5}
    except Exception as e:
        logger.warning(f"LLM threat_analyzer failed: {e}")
    # 3. Fallback
    return {"type": "unknown", "confidence": 0.3}

def enhanced_ner_parser(text):
    """
    Улучшенный парсер географических объектов с контекстом и fallback-логикой.
    """
    text = re.sub(r'https?://\S+|@\w+|#\w+|[♥♦♣♠♪♫♬☺☻]', '', text)
    locations = {}
    
    # Поиск названий с областью в скобках
    oblast_pattern = r'([А-ЯІЇЄҐ][А-ЯІЇЄҐа-яіїєґ\'\-\s]+)\s*\(([А-ЯІЇЄҐа-яіїєґ\'\-\s]+)\s*(обл|область)\.?\)'
    oblast_matches = re.finditer(oblast_pattern, text, re.UNICODE)
    for match in oblast_matches:
        place = match.group(1).strip()
        oblast = match.group(2).strip()
        if place and oblast:
            full_place = f"{place}, {oblast} область"
            locations[place] = {
                'type': 'city_with_oblast',
                'context': full_place,
                'oblast': oblast
            }
            return locations  # Возвращаем сразу, так как это самое точное совпадение
    
    # Военные термины
    military_terms = {
        "аеродром": "airport",
        "аэропорт": "airport",
        "летовище": "airport",
        "казарм": "military_base",
        "база": "base",
        "в/ч": "military_base",
        "депо": "depot",
        "склад": "warehouse",
        "завод": "factory",
        "електростанц": "power_plant",
        "енерго": "power_plant",
        "пво": "air_defense",
        "зрк": "air_defense"
    }
    
    # Улучшенные паттерны для извлечения локаций
    patterns = [
        r'(?:у |в |біля |поблизу |районі |м\. |с\. |смт )?([А-ЯІЇЄҐ][а-яіїєґ\'-]+)(?:, ([А-ЯІЇЄҐ][а-яіїєґ\'-]+))?(?: області| районі)?',
        r'(північніше|південніше|східніше|західніше|північній|південній|східній|західній)\s+([\w\-\']+)',
        r'на\s+північ\s+від\s+([\w\-\']+)',
        r'на\s+південь\s+від\s+([\w\-\']+)',
        r'на\s+схід\s+від\s+([\w\-\']+)',
        r'на\s+захід\s+від\s+([\w\-\']+)',
        r'(біля|поблизу|околиці|район|поруч\s+з|під)\s*([\w\-\']+)',
        r'у\s+([\w\-\']+)\s+районі'
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            place = match.group(2) if len(match.groups()) > 1 else match.group(1)
            if place:
                # Контекст для уточнения
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end]
                
                # Определение типа локации по контексту
                loc_type = "generic"
                for term, term_type in military_terms.items():
                    if term in context.lower():
                        loc_type = term_type
                        break
                
                locations[place.strip()] = {
                    "type": loc_type,
                    "context": context,
                    "direction": match.group(1) if len(match.groups()) > 1 else None
                }
    
    # Дополнительный поиск по ключевым словам
    keywords = {
        "київ": "Київ",
        "одес": "Одеса",
        "харків": "Харків",
        "львів": "Львів",
        "дніпр": "Дніпро",
        "запоріж": "Запоріжжя",
        "миколаїв": "Миколаїв",
        "херсон": "Херсон",
        "дп": "Дніпро",
        "зп": "Запоріжжя",
        "од": "Одеса"
    }
    
    for pattern, place in keywords.items():
        if re.search(pattern, text, re.IGNORECASE):
            locations[place] = {
                "type": "city",
                "context": "keyword_match",
                "direction": None
            }
    
    # spaCy NER (если доступно)
    if nlp_uk:
        doc = nlp_uk(text)
        for ent in doc.ents:
            if ent.label_ in ("LOC", "GPE", "FAC", "ORG"):
                loc_type = "generic"
                for term, term_type in military_terms.items():
                    if term in ent.text.lower():
                        loc_type = term_type
                        break
                start = max(0, ent.start - 3)
                end = min(len(doc), ent.end + 3)
                context = doc[start:end].text
                if ent.text not in locations:
                    locations[ent.text] = {
                        "type": loc_type,
                        "context": context
                    }
    
    # Фильтрация результатов
    filtered = {}
    skip_words = {"український", "ппошник", "канал", "підтримати", "напрямок", "решта", "the", "new", "times", "cnn", "оае", "сша"}
    for place, meta in locations.items():
        if len(place) < 3:
            continue
        if normalize_place_name(place) in skip_words:
            continue
        filtered[place] = meta
        
    return filtered

def advanced_ner_locations(text):
    """
    Распознаёт локации с помощью регулярных выражений и словарей.
    Возвращает dict: {place: {'type': ..., 'context': ...}}
    """
    locations = {}
    
    # Ищем локации в формате "курсом на Город"
    course_matches = re.finditer(r'курсом на ([А-ЯІЇЄҐ][А-ЯІЇЄҐа-яіїєґ\'\-\s]+)', text)
    for match in course_matches:
        loc = match.group(1).strip()
        if len(loc) > 2:
            locations[loc] = {'type': 'LOC', 'context': 'regex'}
    
    # Ищем названия областей
    region_matches = re.finditer(r'\*\*([А-ЯІЇЄҐ][а-яіїєґ]+(?:щина|ська|ская|область))[:]*\*\*', text)
    for match in region_matches:
        loc = match.group(1).strip()
        if len(loc) > 2:
            locations[loc] = {'type': 'REGION', 'context': 'regex'}
    # DeepPavlov (мультиязычный)
    if dp_ner:
        try:
            dp_results = dp_ner([text])[0]
            for word, tag in zip(dp_results[0], dp_results[1]):
                if tag.startswith('B-LOC') or tag.startswith('B-GPE'):
                    loc = word.strip()
                    if len(loc) > 2 and loc not in locations:
                        locations[loc] = {'type': tag, 'context': 'deeppavlov'}
        except Exception as e:
            logger.warning(f"DeepPavlov NER failed: {e}")
    # Регулярка для 'на <Топоним>' с поддержкой слэшей и сложных форм
    pattern_na = r"на\s+([А-ЯA-ZІЇЄҐ][а-яa-zіїєґ'\-/ ]{2,})"
    for m in re.finditer(pattern_na, text, re.IGNORECASE):
        loc = m.group(1).strip().replace(' /', '/').replace('/ ', '/').replace('  ', ' ')
        for part in re.split(r"[\\/]", loc):
            part = part.strip()
            if len(part) > 2:
                locations[part] = {'type': 'regex_na', 'context': 'regex-na'}
    # Fallback: перевод на укр/рус/en и регулярки
    if not locations:
        try:
            for tgt in ['uk', 'ru', 'en']:
                tr = GoogleTranslator(source='auto', target=tgt).translate(text)
                for m in re.finditer(r'\b[А-ЯA-ZІЇЄҐ][а-яa-zіїєґ\'-]{3,}\b', tr):
                    loc = m.group().strip()
                    if len(loc) > 2:
                        locations[loc] = {'type': 'regex', 'context': f'regex-fallback-{tgt}'}
        except Exception as e:
            logger.warning(f"Fallback translation failed: {e}")
    # LLM fallback (OpenAI)
    if not locations and hasattr(openai, 'chat') and hasattr(openai.chat, 'completions'):
        try:
            prompt = f"Извлеки все топонимы (города, регионы, страны, районы, сёла, акватории, аэропорты) из текста: {text}\nОтвет в формате JSON-словаря: place -> type."
            resp = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=256, temperature=0.1
            )
            import ast
            llm_locs = ast.literal_eval(resp.choices[0].message.content)
            for k, v in llm_locs.items():
                if len(k) > 2:
                    locations[k] = {'type': v, 'context': 'llm'}
        except Exception as e:
            logger.warning(f"LLM fallback failed: {e}")
    # Кэширование (можно расширить)
    # TODO: добавить кэширование результатов NER
    return locations

async def smart_geocode(place_name, context, session, region_hint=None, channel=None):
    # Проверяем, есть ли в контексте информация об области
    oblast_match = None
    if isinstance(context, dict) and 'oblast' in context:
        oblast_match = context['oblast']
    elif isinstance(context, str):
        oblast_pattern = r'\(([А-ЯІЇЄҐа-яіїєґ\'\-\s]+)\s*(обл|область)\.?\)'
        oblast_search = re.search(oblast_pattern, context)
        if oblast_search:
            oblast_match = oblast_search.group(1).strip()
    
    normalized = normalize_place_name(place_name)
    
    # Если есть область в контексте, создаем полное название
    if oblast_match:
        full_name = f"{place_name}, {oblast_match} область"
        coords = geocode_place_opencage(full_name)
        if coords:
            GEOCODING_CACHE[normalized] = coords
            return coords
    
    # 1. Приоритетные локации
    if normalized in PRIORITY_LOCATIONS:
        return PRIORITY_LOCATIONS[normalized]
    # 2. Ручные координаты
    if normalized in MANUAL_COORDS:
        return MANUAL_COORDS[normalized]
    # 3. Кэш
    if normalized in GEOCODING_CACHE:
        return GEOCODING_CACHE[normalized]
    # 4. Контекстные подсказки
    region_override = None
    if re.search(r'дніпр|дп|днепр', context, re.IGNORECASE):
        region_override = "Дніпропетровська область"
    elif re.search(r'запоріж|зп', context, re.IGNORECASE):
        region_override = "Запорізька область"
    elif re.search(r'одес|од', context, re.IGNORECASE):
        region_override = "Одеська область"
    elif re.search(r'харків|харк', context, re.IGNORECASE):
        region_override = "Харківська область"
    elif re.search(r'львів|львов', context, re.IGNORECASE):
        region_override = "Львівська область"
    elif re.search(r'київ|киев', context, re.IGNORECASE):
        region_override = "Київська область"
    # 5. Геокодирование с учетом региона
    query_name = place_name
    if region_override:
        query_name = f"{place_name}, {region_override}"
    elif region_hint:
        query_name = f"{place_name}, {region_hint}"
    elif normalized in DNZP_PRIORITY:
        query_name = f"{place_name}, {DNZP_PRIORITY[normalized]}"
    # 6. OpenCage вместо Google Maps
    coords = geocode_place_googlemaps(query_name)
    if coords and validate_coords(*coords):
        GEOCODING_CACHE[normalized] = coords
        return coords
    # 8. ML fallback
    try:
        result = subprocess.run(
            ['python', 'ml_geo_infer.py', place_name],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and "lat=" in result.stdout:
            latlng = result.stdout.split("lat=")[1].split(", lng=")
            lat = float(latlng[0])
            lng = float(latlng[1])
            if validate_coords(lat, lng):
                GEOCODING_CACHE[normalized] = (lat, lng)
                return (lat, lng)
    except Exception as e:
        logger.error(f"ML fallback error: {e}")
    # 9. Логирование для ручного добавления
    with open('not_found_places.log', 'a', encoding='utf-8') as f:
        f.write(f"{place_name}|{context}\n")
    return None

def geocode_place_opencage(place, api_key=OPENCAGE_API_KEY):
    """
    Геокодирование топонима через OpenCage Geocoding API с кэшированием в opencage_cache.json.
    Возвращает (lat, lng) или None, если не найдено.
    """
    import requests, time, json, os
    CACHE_FILE = 'opencage_cache.json'
    CACHE_TTL = 60 * 60 * 24 * 30  # 30 дней
    now = int(time.time())
    # Загрузка кэша
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except Exception:
            cache = {}
    else:
        cache = {}
    key = place.strip().lower()
    # Проверка кэша
    if key in cache:
        entry = cache[key]
        if entry['coords'] and (now - entry.get('ts', 0) < CACHE_TTL):
            return tuple(entry['coords'])
        # Если coords == null, но запись свежая — не делать повторный запрос
        if entry['coords'] is None and (now - entry.get('ts', 0) < 3600):
            return None
    # Запрос к API
    try:
        url = 'https://api.opencagedata.com/geocode/v1/json'
        params = {
            'q': place,
            'key': api_key,
            'language': 'uk',
            'limit': 1
        }
        resp = requests.get(url, params=params, timeout=7)
        if resp.status_code == 200:
            data = resp.json()
            if data['results']:
                loc = data['results'][0]['geometry']
                lat, lng = loc['lat'], loc['lng']
                cache[key] = {'ts': now, 'coords': [lat, lng]}
                with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(cache, f, ensure_ascii=False)
                return lat, lng
            else:
                cache[key] = {'ts': now, 'coords': None}
                with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(cache, f, ensure_ascii=False)
                return None
    except Exception as e:
        logger.warning(f"OpenCage geocoding error for '{place}': {e}")
    # Сохраняем неудачный результат на 1 час, чтобы не спамить API
    cache[key] = {'ts': now, 'coords': None}
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False)
    return None

# Заменяем функцию geocode_place_googlemaps на OpenCage

def geocode_place_googlemaps(place):
    return geocode_place_opencage(place)

def validate_coords(lat, lng):
    """
    Проверяет, что координаты находятся в допустимых пределах для Украины.
    """
    try:
        lat = float(lat)
        lng = float(lng)
        # Примерные границы Украины
        return 44.0 <= lat <= 53.0 and 22.0 <= lng <= 41.0
    except Exception:
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def data():
    # Получаем параметры фильтрации
    try:
        time_range = int(request.args.get('timeRange', 20))
    except Exception:
        time_range = 20
    try:
        conf_range = float(request.args.get('confRange', 0))
    except Exception:
        conf_range = 0
    source = request.args.get('source', '')

    try:
        with open('messages.json', encoding='utf-8') as f:
            tracks = json.load(f)
    except Exception:
        tracks = []

    # Загружаем скрытые маркеры (по округлённым координатам)
    hidden_set = set()
    try:
        with open('hidden_markers.json', encoding='utf-8') as f:
            hidden = json.load(f)
            for h in hidden:
                lat = round(float(h.get('lat', 0)), 3)
                lng = round(float(h.get('lng', 0)), 3)
                hidden_set.add((lat, lng))
    except Exception:
        hidden_set = set()

    # Используем время Киева для фильтрации
    import pytz
    kyiv_tz = pytz.timezone('Europe/Kyiv')
    now_kyiv = datetime.now(kyiv_tz).replace(tzinfo=None)
    min_time = now_kyiv - timedelta(minutes=time_range)
    filtered_tracks = []
    for t in tracks:
        # Время: t['date'] ожидается в формате 'YYYY-MM-DD HH:MM:SS'
        t_time = None
        if 'date' in t and t['date']:
            try:
                t_time = datetime.strptime(t['date'], '%Y-%m-%d %H:%M:%S')
            except Exception:
                t_time = None
        # Фильтрация
        if t_time and t_time < min_time:
            continue
        if source and t.get('channel') != source:
            continue
        if 'confidence' in t and t['confidence'] is not None:
            try:
                if float(t['confidence']) < conf_range:
                    continue
            except Exception:
                pass
        # Исключаем скрытые маркеры
        lat = round(float(t.get('lat', 0)), 3)
        lng = round(float(t.get('lng', 0)), 3)
        if (lat, lng) in hidden_set:
            continue
        filtered_tracks.append(t)

    # --- Группировка траекторий для шахедов ---
    # Ключ: (канал, threat_type, округлённое время до 10 мин)
    from collections import defaultdict
    trajectories = defaultdict(list)
    for t in filtered_tracks:
        if t.get('threat_type') == 'shahed' and t.get('channel') and t.get('lat') and t.get('lng') and t.get('date'):
            try:
                t_time = datetime.strptime(t['date'], '%Y-%m-%d %H:%M:%S')
                t_time_10 = t_time.replace(minute=(t_time.minute // 10) * 10, second=0)
                key = (t['channel'], t_time_10.strftime('%Y-%m-%d %H:%M'), t.get('place',''))
                trajectories[key].append((float(t['lat']), float(t['lng'])))
            except Exception:
                pass
    # Оставляем только траектории из 2+ точек
    trajectories_out = [pts for pts in trajectories.values() if len(pts) > 1]

    # --- Фильтрация: только с валидными координатами ---
    valid_tracks = []
    for t in filtered_tracks:
        try:
            lat = float(t.get('lat', ''))
            lng = float(t.get('lng', ''))
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                continue
        except Exception:
            continue
        valid_tracks.append(t)

    # --- Удаление дублей по (lat, lng, text, date, place) ---
    seen = set()
    unique_tracks = []
    for t in valid_tracks:
        key = (
            round(float(t.get('lat', 0)), 4),
            round(float(t.get('lng', 0)), 4),
            (t.get('text') or '').strip(),
            (t.get('date') or '').strip(),
            (t.get('place') or '').strip().lower()
        )
        if key in seen:
            continue
        seen.add(key)
        unique_tracks.append(t)

    return jsonify({
        'tracks': unique_tracks,
        'all_sources': channel_usernames,
        'trajectories': trajectories_out
    })

@app.route('/notfound', methods=['GET', 'POST'])
def notfound():
    nf_path = 'not_found_places.log'
    if request.method == 'POST':
        data = request.get_json()
        place = data.get('place')
        coord = data.get('coord')
        with open('manual_coords.json', 'a', encoding='utf-8') as f:
            f.write(json.dumps({'place': place, 'coord': coord}) + '\n')
        return {'ok': True}
    if not os.path.exists(nf_path):
        return jsonify([])
    with open(nf_path, 'r', encoding='utf-8') as f:
        places = list(sorted(set(l.strip() for l in f if l.strip())))
    return jsonify(places)

@app.route('/hide_marker', methods=['POST'])
def hide_marker():
    """
    Сохраняет скрытый маркер (lat, lng, text, source) в hidden_markers.json
    """
    data = request.get_json(force=True)
    lat = data.get('lat')
    lng = data.get('lng')
    text = data.get('text')
    source = data.get('source')
    if lat is None or lng is None:
        return jsonify({'ok': False, 'error': 'lat/lng required'}), 400
    path = 'hidden_markers.json'
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                hidden = json.load(f)
        else:
            hidden = []
    except Exception:
        hidden = []
    # Округляем координаты до 3 знаков для совпадения с фронтом
    lat = round(float(lat), 3)
    lng = round(float(lng), 3)
    # Проверяем, нет ли уже такого маркера
    for h in hidden:
        if h.get('lat') == lat and h.get('lng') == lng:
            return jsonify({'ok': True, 'already': True})
    hidden.append({'lat': lat, 'lng': lng, 'text': text, 'source': source})
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(hidden, f, ensure_ascii=False, indent=2)
    return jsonify({'ok': True})

def should_ignore_message(text):
    """Проверяет, нужно ли игнорировать сообщение"""
    # Слова, указывающие на общие направления или регионы без конкретного места
    vague_location_words = [
        r'схід\w*', r'захід\w*', r'північ\w*', r'південь\w*', r'восток\w*', r'запад\w*', r'север\w*', r'юг\w*',
        r'схід\s+та\s+південь', r'восток\s+и\s+юг',
        r'регіон\w*', r'район\w*', r'област\w*', r'зон\w*',
        r'східн\w*', r'західн\w*', r'північн\w*', r'південн\w*',
        r'восточн\w*', r'западн\w*', r'северн\w*', r'южн\w*',
        'сумщин', 'харківщин', 'київщин', 'дніпропетровщин'
    ]
    
    # Проверка на наличие только общих указаний местоположения без конкретного населенного пункта
    has_only_vague_location = False
    for word in vague_location_words:
        if re.search(word, text.lower()):
            has_only_vague_location = True
            break
    
    # Ищем конкретные населенные пункты (города, села и т.д.)
    has_specific_location = re.search(r'[А-ЯІЇЄҐ][а-яіїєґ\'\-]+(?:\s+(?:міст|город|село|смт|селище|пгт))?', text)
    
    # Если есть только общие указания без конкретного места - игнорируем
    if has_only_vague_location and not has_specific_location:
        return True
    
    # Слова, указывающие на предупреждение или возможную угрозу
    warning_words = [
        'імовірн', 'можлив', 'вероятн', 'возможн',
        'загроза', 'угроза', 'threat',
        'готов', 'готує', 'готовит', 'preparing',
        'активн', 'active',
        'очікує', 'ожидае', 'waiting',
        'зафіксован', 'фиксируем', 'observed',
        'може', 'может', 'may', 'might',
        'ситуація', 'ситуация', 'situation',
        'залишаємось', 'остаемся', 'staying',
        'перебува', 'находит', 'located',
        'спостерігає', 'наблюдае', 'monitoring'
    ]
    
    # Если текст содержит указание на актуальное время - это может быть отчет о ситуации
    if re.search(r'станом на|по состоянию на|as of', text, re.IGNORECASE):
        return True
        
    # Проверяем наличие слов-маркеров предупреждений
    for word in warning_words:
        if re.search(fr'\b{word}', text, re.IGNORECASE):
            # Ищем в том же предложении слова о фактической атаке
            sentence = re.split(r'[.!?]\s+', text)
            for s in sentence:
                if word in s.lower():
                    # Если в том же предложении нет слов о фактической атаке - игнорируем
                    attack_words = ['влучи', 'попада', 'hit', 'strike', 'атак', 'attack', 'пуск', 'launch']
                    if not any(w in s.lower() for w in attack_words):
                        return True
    
    return False

def round_coords(coords, precision=3):
    """Округляет координаты до заданной точности"""
    if isinstance(coords, (list, tuple)):
        return tuple(round(x, precision) for x in coords)
    return round(coords, precision)

def process_message(message_text, message_id, date, channel):
    """
    Обрабатывает текст сообщения: извлекает топонимы, геокодирует, формирует трек для карты.
    Возвращает dict с результатом или None, если не удалось распознать локацию.
    """
    # Удаляем любые подписи/ссылки/упоминания "Український | ППОшник" и его вариаций
    # 1. Markdown-ссылки на канал (с любым текстом, ведущие на t.me/ukrainsiypposhnik)
    message_text = re.sub(r'\[.*?\]\(https?://t\.me/ukrainsiypposhnik[^)]*\)', '', message_text, flags=re.IGNORECASE)
    # 2. Любые прямые ссылки на t.me/ukrainsiypposhnik
    message_text = re.sub(r'https?://t\.me/ukrainsiypposhnik\S*', '', message_text, flags=re.IGNORECASE)
    # 3. Любые текстовые упоминания "Український | ППОшник", "ukrainsiypposhnik", "ппошник", "pposhnik" (с пробелами/без, в любом регистре)
    message_text = re.sub(r'(український\s*\|\s*ппошник|ukrainskiy\s*\|\s*pposhnik|ukrainsiypposhnik|ппошник|pposhnik)', '', message_text, flags=re.IGNORECASE)
    # 4. Удаляем все подписи вида ✙[ ... ](...)✙ (любые ссылки и любые подписи, даже если подряд)
    message_text = re.sub(r'(✙\[.*?\]\([^\)]+\)✙\s*)+', '', message_text, flags=re.IGNORECASE)
    # 5. Удаляем любые одиночные ✙
    message_text = re.sub(r'✙', '', message_text)
    # 6. Удаляем лишние пробелы и пустые строки
    message_text = re.sub(r'\n+', '\n', message_text)
    message_text = re.sub(r'\s{2,}', ' ', message_text).strip()

    # Проверяем, нужно ли игнорировать сообщение
    if should_ignore_message(message_text):
        return None

    # Проверка на наличие конкретного места
    has_specific_location = False
    # Поиск конкретных населенных пунктов
    location_match = re.search(r'[А-ЯІЇЄҐ][а-яіїєґ\'\-]+(?:\s+(?:міст|город|село|смт|селище|пгт))?', message_text)
    # Поиск места с указанием области в скобках
    oblast_location_match = re.search(r'([А-ЯІЇЄҐ][А-ЯІЇЄҐа-яіїєґ\'\-\s]+)\s*\(([А-ЯІЇЄҐа-яіїєґ\'\-\s]+)\s*(обл|область)\.?\)', message_text)
    
    if location_match or oblast_location_match:
        has_specific_location = True

    if not has_specific_location:
        return None

    # --- МОРСКОЙ ПРИОРИТЕТ ---
    lower_text = message_text.lower()
    sea_keys = [
        "чорне море", "черное море", "black sea",
        "акваторія чорного моря", "акватория черного моря", "акватория black sea"
    ]
    sea_bios_keys = [
        "чорноморський біосферний заповідник", "черноморский биосферный заповедник"
    ]
    tracks = []
    unique_places = set()  # Для фильтрации дублей
    unique_cities = set()
    city_keywords = [
        'місто', 'город', 'city', 'sumy', 'суми', 'київ', 'kiev', 'lviv', 'львів', 'харків', 'kharkiv', 'одеса', 'odesa', 'дніпро', 'dnipro', 'запоріжжя', 'zaporizhzhia', 'чернігів', 'chernihiv', 'полтава', 'poltava', 'черкаси', 'cherkasy', 'житомир', 'zhytomyr', 'хмельницький', 'khmelnytskyi', 'вінниця', 'vinnytsia', 'луцьк', 'lutsk', 'рівне', 'rivne', 'тернопіль', 'ternopil', 'ужгород', 'uzhhorod', 'івано-франківськ', 'ivano-frankivsk', 'суми', 'sumy', 'мелітополь', 'melitopol', 'маріуполь', 'mariupol', 'краматорськ', 'kramatorsk', 'кропивницький', 'kropyvnytskyi', 'миколаїв', 'mykolaiv', 'херсон', 'kherson', 'сімферополь', 'simferopol', 'севастополь', 'sevastopol'
    ]
    if any(k in lower_text for k in sea_keys) or (
        any(k in lower_text for k in sea_bios_keys) and ("акватор" in lower_text or "біосферн" in lower_text or "biosphere" in lower_text)
    ):
        pass
    # Определяем тип угрозы по тексту (очень простая эвристика)
    # ML/LLM определение типа угрозы


    def get_threat_type(text):
        result = threat_analyzer(text)
        typ = result.get('type', '').lower()
        # Кастомная логика для разведывательных БПЛА
        if re.search(r'розвід|развед|recon|розвідувальн', text, re.IGNORECASE):
            return 'recon_uav'
        if typ in ['shahed', 'raketa', 'avia', 'artillery', 'mlrs', 'explosion', 'landing', 'pvo', 'navy']:
            return typ
        return 'shahed'  # fallback

    # Ensure locations is defined before use
    locations = advanced_ner_locations(message_text)
    threat_type = get_threat_type(message_text)
    tracks = []
    
    # Process all locations
    loc_items = list(locations.items())
    for i, (place, meta) in enumerate(loc_items):
        place_norm = normalize_place_name(place)
        # Получаем координаты
        if re.search(r'(ська|ская|область|region)$', place_norm, re.IGNORECASE):
            oblast_key = place_norm.replace(' область', '').replace('ская', 'ская').replace('ська', 'ська').strip()
            coords = OBLAST_CENTERS.get(oblast_key) or geocode_place_opencage(place)
        elif place_norm in PRIORITY_LOCATIONS:
            coords = PRIORITY_LOCATIONS[place_norm]
        else:
            coords = geocode_place_opencage(place)
        if not coords:
            continue
        lat, lng = round_coords(coords)
        # Ключ для уникальности: нормализованное название + округленные координаты
        key = (place_norm, round(lat, 4), round(lng, 4))
        if key in unique_places:
            continue  # Уже добавляли такой маркер
        unique_places.add(key)
        # Далее стандартная логика
        if threat_type in ['shahed', 'raketa'] and i + 1 < len(loc_items):
            next_place, next_meta = loc_items[i + 1]
            next_place_norm = normalize_place_name(next_place)
            if re.search(r'(ська|ская|область|region)$', next_place_norm, re.IGNORECASE):
                oblast_key2 = next_place_norm.replace(' область', '').replace('ская', 'ская').replace('ська', 'ська').strip()
                coords2 = OBLAST_CENTERS.get(oblast_key2) or geocode_place_opencage(next_place)
            elif next_place_norm in PRIORITY_LOCATIONS:
                coords2 = PRIORITY_LOCATIONS[next_place_norm]
            else:
                coords2 = geocode_place_opencage(next_place)
            if coords2:
                lat2, lng2 = round_coords(coords2)
                if 44.0 <= lat <= 53.0 and 22.0 <= lng <= 41.0:
                    track = {
                        'id': f"{message_id}_{i}",
                        'place': place,
                        'lat': round(lat, 3),
                        'lng': round(lng, 3),
                        'lat2': round(lat2, 3),
                        'lng2': round(lng2, 3),
                        'threat_type': threat_type,
                        'text': message_text,
                        'date': date,
                        'channel': channel,
                        'marker_icon': f"{threat_type}.png"
                    }
                    tracks.append(track)
        else:
            track = {
                'id': f"{message_id}_{i}",
                'place': place,
                'lat': lat,
                'lng': lng,
                'threat_type': threat_type,
                'text': message_text,
                'date': date,
                'channel': channel,
                'marker_icon': f"{threat_type}.png"
            }
            tracks.append(track)
    
    return tracks if tracks else None



async def fetch_and_process_posts():
    """
    Периодически получает новые сообщения из Telegram-каналов, обрабатывает их и сохраняет в messages.json
    Только сообщения за последние 30 минут по Киевскому времени.
    """
    processed_ids = set()
    if os.path.exists('messages.json'):
        try:
            with open('messages.json', encoding='utf-8') as f:
                data = json.load(f)
                for msg in data:
                    processed_ids.add(msg.get('id'))
        except Exception as e:
            logger.warning(f"Ошибка чтения messages.json: {e}")
    all_tracks = []
    kyiv_tz = pytz.timezone('Europe/Kyiv')
    while True:
        min_time = datetime.now(kyiv_tz) - timedelta(minutes=30)
        new_tracks = []
        for channel in channel_usernames:
            try:
                logger.info(f"Проверка канала: {channel}")
                async for message in client.iter_messages(channel, limit=50):
                    logger.debug(f"Сообщение {message.id} ({message.date})")
                    if message.id in processed_ids:
                        continue
                    if not message.text:
                        continue
                    msg_time = message.date.astimezone(kyiv_tz)
                    if msg_time < min_time:
                        continue  # пропускаем старые сообщения
                    date_str = msg_time.strftime('%Y-%m-%d %H:%M:%S')
                    tracks = process_message(message.text, message.id, date_str, channel)
                    if tracks:
                        for tr in tracks:
                            new_tracks.append(tr)
                            logger.info(f"Добавлен track: {tr.get('place')} ({tr.get('lat')}, {tr.get('lng')}) из {channel}")
                            processed_ids.add(message.id)
            except Exception as e:
                logger.warning(f"Ошибка получения сообщений из {channel}: {e}")
        if new_tracks:
            try:
                if os.path.exists('messages.json'):
                    with open('messages.json', encoding='utf-8') as f:
                        all_tracks = json.load(f)
                else:
                    all_tracks = []
            except Exception as e:
                logger.warning(f"Ошибка чтения messages.json при записи: {e}")
                all_tracks = []
            all_tracks.extend(new_tracks)
            try:
                with open('messages.json', 'w', encoding='utf-8') as f:
                    json.dump(all_tracks, f, ensure_ascii=False, indent=2)
                logger.info(f"Добавлено {len(new_tracks)} новых треков. Всего: {len(all_tracks)}")
            except Exception as e:
                logger.error(f"Ошибка записи messages.json: {e}")
        else:
            logger.info("Нет новых сообщений для записи в messages.json")
        await asyncio.sleep(60)  # Проверять раз в минуту

def start_background_fetch(loop):
    """
    Фоновая задача для сбора сообщений из Telegram.
    """
    asyncio.set_event_loop(loop)
    with client:
        loop.run_until_complete(fetch_and_process_posts())

if __name__ == '__main__':
    # Запуск фоновой задачи для сбора сообщений из Telegram
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=start_background_fetch, args=(loop,), daemon=True)
    t.start()
    # Запуск Flask
    logger.info("Starting Flask server...")
    app.run(host='0.0.0.0', port=8080, debug=False)

# --- Улучшение: Healthcheck endpoint для мониторинга ---
@app.route('/health')
def health():
    """
    Healthcheck endpoint для мониторинга состояния сервера и основных файлов.
    """
    status = {'status': 'ok', 'time': datetime.utcnow().isoformat() + 'Z'}
    # Проверка наличия ключевых файлов
    for fname in ['messages.json', 'geocoding_cache.json', 'hidden_markers.json']:
        status[fname] = os.path.exists(fname)
    # Проверка количества треков
    try:
        with open('messages.json', encoding='utf-8') as f:
            tracks = json.load(f)
            status['tracks_count'] = len(tracks)
    except Exception:
        status['tracks_count'] = 0
    return jsonify(status)

# --- Улучшение: endpoint для динамического добавления Telegram-каналов ---
@app.route('/add_channel', methods=['POST'])
def add_channel():
    """
    Позволяет добавить новый Telegram-канал для мониторинга без перезапуска сервера.
    Пример запроса: {"channel": "new_channel_name"}
    """
    data = request.get_json(force=True)
    channel = data.get('channel')
    if not channel or not isinstance(channel, str):
        return jsonify({'ok': False, 'error': 'channel required'}), 400
    if channel in channel_usernames:
        return jsonify({'ok': True, 'already': True})
    channel_usernames.append(channel)
    logger.info(f"Добавлен новый канал для мониторинга: {channel}")
    return jsonify({'ok': True, 'channels': channel_usernames})

# --- Улучшение: endpoint для удаления Telegram-канала из мониторинга ---
@app.route('/remove_channel', methods=['POST'])
def remove_channel():
    """
    Позволяет удалить Telegram-канал из мониторинга без перезапуска сервера.
    Пример запроса: {"channel": "channel_name"}
    """
    data = request.get_json(force=True)
    channel = data.get('channel')
    if not channel or not isinstance(channel, str):
        return jsonify({'ok': False, 'error': 'channel required'}), 400
    if channel not in channel_usernames:
        return jsonify({'ok': False, 'error': 'not found'})
    channel_usernames.remove(channel)
    logger.info(f"Канал удалён из мониторинга: {channel}")
    return jsonify({'ok': True, 'channels': channel_usernames})

# --- Улучшение: endpoint для просмотра текущих Telegram-каналов ---
@app.route('/channels', methods=['GET'])
def list_channels():
    """
    Возвращает список всех Telegram-каналов, которые мониторятся.
    """
    return jsonify({'channels': channel_usernames})

# --- Улучшение: endpoint для экспорта всех треков в CSV ---
@app.route('/export_tracks', methods=['GET'])
def export_tracks():
    """
    Экспортирует все треки (messages.json) в формате CSV.
    """
    import csv
    from io import StringIO
    try:
        with open('messages.json', encoding='utf-8') as f:
            tracks = json.load(f)
    except Exception:
        tracks = []
    if not tracks:
        return ('No data', 204)
    # Определяем все возможные ключи
    all_keys = set()
    for t in tracks:
        all_keys.update(t.keys())
    all_keys = sorted(all_keys)
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=all_keys, extrasaction='ignore')
    writer.writeheader()
    for t in tracks:
        writer.writerow(t)
    csv_data = output.getvalue()
    return (csv_data, 200, {'Content-Type': 'text/csv; charset=utf-8', 'Content-Disposition': 'attachment; filename=tracks.csv'})