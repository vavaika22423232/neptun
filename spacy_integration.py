#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SpaCy integration module for enhanced Ukrainian city recognition
"""

import spacy
import re
from typing import List, Tuple, Dict, Optional

# Load Ukrainian model
try:
    nlp = spacy.load('uk_core_news_sm')
    SPACY_AVAILABLE = True
except OSError:
    nlp = None
    SPACY_AVAILABLE = False
    print("Ukrainian SpaCy model not available. Using fallback methods.")

class SpacyCityExtractor:
    """Enhanced city extraction using SpaCy NLP"""
    
    def __init__(self):
        self.nlp = nlp
        self.available = SPACY_AVAILABLE
        
        # Known Ukrainian regions patterns  
        self.region_patterns = {
            'сумщина': ['сумщин', 'сумська область', 'сумська обл'],
            'чернігівщина': ['чернігівщин', 'чернігівська область', 'чернігівська обл'],
            'харківщина': ['харківщин', 'харківська область', 'харківська обл'],
            'полтавщина': ['полтавщин', 'полтавська область', 'полтавська обл'],
            'херсонщина': ['херсонщин', 'херсонська область', 'херсонська обл'],
            'миколаївщина': ['миколаївщин', 'миколаївська область', 'миколаївська обл'],
        }
    
    def extract_cities_and_regions(self, text: str) -> Tuple[List[Dict], List[str]]:
        """
        Extract cities and regions from text using SpaCy NLP
        
        Returns:
            Tuple of (cities_info, regions)
            cities_info: List of dicts with keys: name, case, lemma, confidence
            regions: List of detected region names
        """
        if not self.available:
            return self._fallback_extraction(text)
        
        doc = self.nlp(text)
        cities_info = []
        regions = []
        
        # Extract geographic entities via NER
        for ent in doc.ents:
            if ent.label_ in ['LOC', 'GPE']:  # Location, Geopolitical entity
                entity_text = ent.text.lower()
                
                # Check if it's a region
                is_region = False
                for region_name, patterns in self.region_patterns.items():
                    if any(pattern in entity_text for pattern in patterns):
                        regions.append(region_name)
                        is_region = True
                        break
                
                if not is_region:
                    # Get morphological info
                    token = doc[ent.start]
                    case_info = self._extract_case_info(token)
                    
                    cities_info.append({
                        'name': ent.text,
                        'lemma': token.lemma_ if token.lemma_ != ent.text.lower() else None,
                        'case': case_info,
                        'confidence': 0.9,  # High confidence for NER
                        'source': 'spacy_ner'
                    })
        
        # Additional pattern-based extraction for missed entities
        pattern_cities = self._extract_pattern_cities(doc)
        cities_info.extend(pattern_cities)
        
        # Remove duplicates while preserving order
        unique_cities = []
        seen_names = set()
        for city in cities_info:
            city_key = city['lemma'] or city['name'].lower()
            if city_key not in seen_names:
                seen_names.add(city_key)
                unique_cities.append(city)
        
        return unique_cities, regions
    
    def _extract_case_info(self, token) -> Optional[str]:
        """Extract case information from token morphology"""
        if hasattr(token, 'morph') and token.morph:
            morph_dict = token.morph.to_dict()
            return morph_dict.get('Case', None)
        return None
    
    def _extract_pattern_cities(self, doc) -> List[Dict]:
        """Extract cities using linguistic patterns"""
        cities = []
        
        # Look for cities after prepositions "на", "повз", "через", "у напрямку"
        preposition_patterns = ['на', 'повз', 'через']
        direction_patterns = ['у напрямку', 'в напрямку'] 
        
        for i, token in enumerate(doc):
            # Simple prepositions
            if token.text.lower() in preposition_patterns:
                city_info = self._extract_city_after_preposition(doc, i)
                if city_info:
                    cities.append(city_info)
            
            # Direction patterns
            elif token.text.lower() == 'у' and i + 1 < len(doc) and doc[i + 1].text.lower() == 'напрямку':
                city_info = self._extract_city_after_preposition(doc, i + 1)
                if city_info:
                    cities.append(city_info)
        
        return cities
    
    def _extract_city_after_preposition(self, doc, prep_index: int) -> Optional[Dict]:
        """Extract city name after preposition"""
        if prep_index + 1 >= len(doc):
            return None
        
        # Collect potential city tokens (proper nouns, nouns, adjectives)
        city_tokens = []
        start_idx = prep_index + 1
        
        for i in range(start_idx, min(start_idx + 3, len(doc))):  # Max 3 words
            token = doc[i]
            if token.pos_ in ['PROPN', 'NOUN', 'ADJ'] or token.text == '-':
                city_tokens.append(token)
            else:
                break
        
        if not city_tokens:
            return None
        
        # Build city name
        city_name = ' '.join(token.text for token in city_tokens)
        
        # Get morphological info from the main token (usually the first one)
        main_token = city_tokens[0] 
        case_info = self._extract_case_info(main_token)
        
        return {
            'name': city_name,
            'lemma': main_token.lemma_ if main_token.lemma_ != city_name.lower() else None,
            'case': case_info,
            'confidence': 0.7,  # Medium confidence for pattern-based
            'source': 'spacy_pattern'
        }
    
    def normalize_city_name(self, city_info: Dict) -> str:
        """
        Normalize city name to canonical form (nominative case)
        
        Args:
            city_info: Dict with city information from extract_cities_and_regions
            
        Returns:
            Normalized city name in nominative case
        """
        if not self.available:
            return city_info['name'].lower()
        
        # If we have lemma information, use it
        if city_info.get('lemma'):
            return city_info['lemma']
        
        # Try to convert accusative/genitive to nominative using patterns
        name = city_info['name'].lower()
        case = city_info.get('case')
        
        if case == 'Acc':  # Accusative case
            # Common Ukrainian accusative -> nominative transformations
            if name.endswith('ку'):
                return name[:-2] + 'ка'  # миколаївку -> миколаївка
            elif name.endswith('ву'):
                return name[:-2] + 'ва'  # полтаву -> полтава
            elif name.endswith('ів'):
                return name[:-2] + 'ів'  # харків -> харків (no change)
                
        elif case == 'Gen':  # Genitive case  
            if name.endswith('а'):
                return name[:-1] + ''   # харкова -> харків
            elif name.endswith('ки'):
                return name[:-2] + 'ка'  # миколаївки -> миколаївка
        
        return name
    
    def _fallback_extraction(self, text: str) -> Tuple[List[Dict], List[str]]:
        """Fallback extraction when SpaCy is not available"""
        cities = []
        regions = []
        
        # Simple regex patterns for fallback
        city_patterns = [
            r'(?:на|повз|через)\s+([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,30})',
            r'у\s+напрямку\s+([А-ЯІЇЄа-яіїєґ][А-Яа-яІіЇїЄєґ\-\'ʼ\s]{2,30})'
        ]
        
        for pattern in city_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                cities.append({
                    'name': match.strip(),
                    'lemma': None,
                    'case': None,
                    'confidence': 0.5,
                    'source': 'regex_fallback'
                })
        
        # Extract regions
        for region_name, patterns in self.region_patterns.items():
            if any(pattern in text.lower() for pattern in patterns):
                regions.append(region_name)
        
        return cities, regions

def integrate_spacy_with_existing_geocoder(message_text: str, existing_city_coords: dict, 
                                         existing_normalizer: dict) -> List[Tuple[str, float, float]]:
    """
    Integration function to enhance existing geocoder with SpaCy
    
    Args:
        message_text: Original message text
        existing_city_coords: Your existing CITY_COORDS dict
        existing_normalizer: Your existing UA_CITY_NORMALIZE dict
        
    Returns:
        List of tuples (city_name, lat, lng) for found cities
    """
    extractor = SpacyCityExtractor()
    cities_info, regions = extractor.extract_cities_and_regions(message_text)
    
    found_coordinates = []
    
    for city_info in cities_info:
        # Try SpaCy normalization first
        normalized_name = extractor.normalize_city_name(city_info)
        
        # Fallback to existing normalization
        if normalized_name in existing_normalizer:
            normalized_name = existing_normalizer[normalized_name]
        
        # Look up coordinates
        coords = existing_city_coords.get(normalized_name)
        
        if coords:
            found_coordinates.append((city_info['name'], coords[0], coords[1]))
        else:
            # Try with region context if detected
            for region in regions:
                region_key = f"{normalized_name} {region}"
                coords = existing_city_coords.get(region_key) 
                if coords:
                    found_coordinates.append((city_info['name'], coords[0], coords[1]))
                    break
    
    return found_coordinates

# Test the integration
if __name__ == "__main__":
    # Test with your problematic message
    test_message = "1 шахед на Миколаївку на Сумщині"
    
    extractor = SpacyCityExtractor()
    cities, regions = extractor.extract_cities_and_regions(test_message)
    
    print(f"Повідомлення: {test_message}")
    print(f"Міста: {cities}")
    print(f"Регіони: {regions}")
    
    for city in cities:
        normalized = extractor.normalize_city_name(city)
        print(f"  {city['name']} -> {normalized} (case: {city.get('case', 'unknown')})")
