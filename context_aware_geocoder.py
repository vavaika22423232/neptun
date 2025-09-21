#!/usr/bin/env python3
"""
Context-Aware Geocoding Plugin
Intelligent text analysis to determine primary targets vs regional context
"""

import re
import spacy
from typing import List, Dict, Tuple, Optional

class ContextAwareGeocoder:
    """
    Intelligent geocoder that understands context and determines primary targets
    """
    
    def __init__(self):
        # Load SpaCy model if available
        try:
            self.nlp = spacy.load('uk_core_news_sm')
            self.spacy_available = True
        except (ImportError, OSError):
            self.spacy_available = False
            self.nlp = None
        
        # Target prepositions that indicate primary location
        self.target_prepositions = [
            'над', 'на', 'у', 'в', 'до', 'під', 'біля', 'поблизу', 'курсом на'
        ]
        
        # Regional context indicators (less priority)
        self.region_indicators = [
            'щина', 'область', 'обл', 'регіон', 'район'
        ]
        
        # Action words that indicate threats/movement towards targets
        self.action_words = [
            'шахеди', 'бпла', 'ракети', 'курсом', 'летять', 'рухаються', 'направляються'
        ]
    
    def analyze_message_context(self, text: str) -> Dict:
        """
        Analyze message to determine primary targets vs regional context
        
        Returns:
            Dict with 'primary_targets', 'regional_context', and 'confidence'
        """
        result = {
            'primary_targets': [],
            'regional_context': [],
            'confidence': 0.0,
            'analysis': []
        }
        
        # Normalize text
        text_lower = text.lower()
        
        # Pattern 1: "над/на [target]" - high priority
        target_pattern = r'(?:над|на|у|в|до|під|біля|поблизу|курсом\s+на)\s+([a-zа-яіїєґ\'ʼ\'`\-]+(?:ою|кою|ою|ею|ю)?)'
        target_matches = re.findall(target_pattern, text_lower)
        
        for match in target_matches:
            city = self._normalize_city_form(match)
            result['primary_targets'].append({
                'name': city,
                'confidence': 0.9,
                'reason': 'target_preposition',
                'original': match
            })
            result['analysis'].append(f"Found target preposition: '{match}' → '{city}'")
        
        # Pattern 2: Regional context (lower priority)
        region_pattern = r'([a-zа-яіїєґ\'ʼ\'`\-]+(?:щин[аи]|област[ьі]|обл\.?))'
        region_matches = re.findall(region_pattern, text_lower)
        
        for match in region_matches:
            region_clean = match.replace('щина', '').replace('область', '').replace('обл.', '').replace('обл', '').strip()
            result['regional_context'].append({
                'name': region_clean,
                'confidence': 0.3,
                'reason': 'regional_indicator',
                'original': match
            })
            result['analysis'].append(f"Found regional context: '{match}' → '{region_clean}'")
        
        # Pattern 3: Action words + city context
        if any(action in text_lower for action in self.action_words):
            # Look for cities mentioned after action words
            action_city_pattern = r'(?:шахеди|бпла|ракети|атакували|обстріляли).*?([a-zа-яіїєґ\'ʼ\'`\-]+(?:ою|кою|ою|ею|ю|ко|ці|у|ськ|чук|ка|на|во|ів|ськ))\b'
            action_matches = re.findall(action_city_pattern, text_lower)
            
            for match in action_matches:
                # Skip action words themselves and region indicators
                if (match not in self.action_words and 
                    not any(indicator in match for indicator in self.region_indicators) and
                    len(match) > 3):  # Skip short words
                    city = self._normalize_city_form(match)
                    result['primary_targets'].append({
                        'name': city,
                        'confidence': 0.7,
                        'reason': 'action_context',
                        'original': match
                    })
                    result['analysis'].append(f"Found action context: '{match}' → '{city}'")
        
        # Calculate overall confidence
        if result['primary_targets']:
            result['confidence'] = max(target['confidence'] for target in result['primary_targets'])
        
        # Remove duplicates and sort by confidence
        result['primary_targets'] = self._deduplicate_targets(result['primary_targets'])
        result['regional_context'] = self._deduplicate_targets(result['regional_context'])
        
        return result
    
    def _normalize_city_form(self, city_form: str) -> str:
        """
        Normalize declined city forms to nominative case
        """
        city = city_form.strip().lower()
        
        # Special cases first
        special_cases = {
            'кременчуці': 'кременчук',
            'києві': 'київ',
            'львові': 'львів',
            'харкові': 'харків',
            'дніпрі': 'дніпро',
            'одесі': 'одеса',
            'полтаві': 'полтава'
        }
        
        if city in special_cases:
            return special_cases[city]
        
        # General morphological patterns
        endings_map = {
            'ою': 'а',
            'кою': 'ка', 
            'ею': 'я',
            'ю': 'а',
            'ко': 'ки',
            'ці': '',    # Just remove -ці 
            'у': 'а',
            'і': '',     # Remove -і for locative
        }
        
        for ending, replacement in endings_map.items():
            if city.endswith(ending):
                return city[:-len(ending)] + replacement
        
        return city
    
    def _deduplicate_targets(self, targets: List[Dict]) -> List[Dict]:
        """
        Remove duplicate targets and keep highest confidence
        """
        unique_targets = {}
        
        for target in targets:
            name = target['name']
            if name not in unique_targets or target['confidence'] > unique_targets[name]['confidence']:
                unique_targets[name] = target
        
        return sorted(unique_targets.values(), key=lambda x: x['confidence'], reverse=True)
    
    def get_priority_geocoding_candidates(self, text: str) -> List[Tuple[str, str, float]]:
        """
        Get prioritized list of geocoding candidates
        
        Returns:
            List of (city_name, region_context, confidence) tuples
        """
        analysis = self.analyze_message_context(text)
        candidates = []
        
        # Primary targets get highest priority
        for target in analysis['primary_targets']:
            region = None
            if analysis['regional_context']:
                region = analysis['regional_context'][0]['name']  # Use most confident region
            
            candidates.append((target['name'], region, target['confidence']))
        
        # If no primary targets found, fall back to regional context
        if not candidates and analysis['regional_context']:
            for region in analysis['regional_context']:
                candidates.append((region['name'], None, region['confidence'] * 0.5))  # Lower confidence
        
        return candidates

# Global instance
context_geocoder = ContextAwareGeocoder()

def get_context_aware_geocoding(text: str) -> List[Tuple[str, str, float]]:
    """
    Public function to get context-aware geocoding candidates
    """
    return context_geocoder.get_priority_geocoding_candidates(text)

if __name__ == "__main__":
    # Test the context analyzer
    test_messages = [
        "чернігівщина - нові шахеди над семенівкою",
        "шахеди над семенівкою чернігівської області",
        "БпЛА курсом на семенівку",
        "новини з харківщини - бпла у балаклії",
        "донецька область - ракети на покровськ"
    ]
    
    geocoder = ContextAwareGeocoder()
    
    for msg in test_messages:
        print(f"\n🔍 Testing: '{msg}'")
        analysis = geocoder.analyze_message_context(msg)
        print(f"Primary targets: {analysis['primary_targets']}")
        print(f"Regional context: {analysis['regional_context']}")
        print(f"Confidence: {analysis['confidence']}")
        
        candidates = geocoder.get_priority_geocoding_candidates(msg)
        print(f"Geocoding candidates: {candidates}")
        print("---")
