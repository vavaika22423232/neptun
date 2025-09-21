#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import spacy
from spacy import displacy
import re

# Загружаем украинскую модель
nlp = spacy.load('uk_core_news_sm')

def test_spacy_ner():
    """Тест Named Entity Recognition для украинских географических названий"""
    
    test_messages = [
        "1 шахед на Миколаївку на Сумщині",
        "БпЛА курсом на Харків через Полтаву", 
        "2х БпЛА повз Конотоп у напрямку Глухова",
        "Чернігівщина: 3 шахеди на Новгород-Сіверський",
        "Обстріл Херсона та Миколаєва",
        "Ракетний удар по Кременчуку Полтавської області",
        "💥 Синельникове — 1х БпЛА довкола міста"
    ]
    
    print("=== SpaCy Named Entity Recognition Test ===\n")
    
    for i, message in enumerate(test_messages, 1):
        print(f"Тест {i}: {message}")
        doc = nlp(message)
        
        print("Токени та їх характеристики:")
        for token in doc:
            print(f"  {token.text:15} | POS: {token.pos_:10} | Tag: {token.tag_:10} | Dep: {token.dep_:10}")
        
        print("Названі сутності (Named Entities):")
        for ent in doc.ents:
            print(f"  {ent.text:20} | Label: {ent.label_:10} | Start: {ent.start} | End: {ent.end}")
        
        print("Іменникові групи (Noun Chunks):")
        try:
            for chunk in doc.noun_chunks:
                print(f"  {chunk.text:20} | Root: {chunk.root.text:10} | Dep: {chunk.root.dep_}")
        except NotImplementedError:
            print("  (Не підтримується для української мови)")
        
        print("-" * 60)

def extract_cities_with_spacy(text):
    """Витягування міст з тексту за допомогою SpaCy"""
    doc = nlp(text)
    
    cities = []
    regions = []
    
    # Витягуємо географічні об'єкти через NER
    for ent in doc.ents:
        if ent.label_ in ['LOC', 'GPE']:  # Location, Geopolitical entity
            if any(region_marker in ent.text.lower() for region_marker in ['щина', 'область', 'обл']):
                regions.append(ent.text)
            else:
                cities.append(ent.text)
    
    # Додатковий пошук через паттерни
    for token in doc:
        # Шукаємо міста після прийменників "на", "повз", "через"
        if token.text.lower() in ['на', 'повз', 'через'] and token.i + 1 < len(doc):
            next_token = doc[token.i + 1]
            if next_token.pos_ == 'NOUN' or next_token.pos_ == 'PROPN':
                # Збираємо можливу назву міста (може бути багатословною)
                city_tokens = []
                for j in range(token.i + 1, min(token.i + 4, len(doc))):  # До 3 слів
                    if doc[j].pos_ in ['NOUN', 'PROPN', 'ADJ'] or doc[j].text == '-':
                        city_tokens.append(doc[j].text)
                    else:
                        break
                
                if city_tokens:
                    potential_city = ' '.join(city_tokens)
                    if potential_city not in cities:
                        cities.append(potential_city)
    
    return cities, regions

def test_city_extraction():
    """Тест витягування міст"""
    
    test_messages = [
        "1 шахед на Миколаївку на Сумщині",
        "БпЛА курсом на Харків через Полтаву", 
        "2х БпЛА повз Конотоп у напрямку Глухова",
        "Чернігівщина: 3 шахеди на Новгород-Сіверський",
        "Обстріл Херсона та Миколаєва"
    ]
    
    print("\n=== SpaCy City Extraction Test ===\n")
    
    for i, message in enumerate(test_messages, 1):
        print(f"Тест {i}: {message}")
        cities, regions = extract_cities_with_spacy(message)
        
        print(f"  Міста: {cities}")
        print(f"  Регіони: {regions}")
        print("-" * 60)

def test_morphology():
    """Тест морфологічного аналізу для правильного визначення відмінків"""
    
    test_words = [
        "Миколаївку",  # Знахідний відмінок
        "Миколаївка",  # Називний відмінок  
        "Харків",
        "Харкова",
        "Полтаву",
        "Полтава"
    ]
    
    print("\n=== SpaCy Morphology Test ===\n")
    
    for word in test_words:
        doc = nlp(word)
        token = doc[0]
        
        print(f"Слово: {word}")
        print(f"  Лема: {token.lemma_}")
        print(f"  POS: {token.pos_}")
        print(f"  Морфологія: {token.morph}")
        print("-" * 30)

if __name__ == "__main__":
    test_spacy_ner()
    test_city_extraction() 
    test_morphology()
