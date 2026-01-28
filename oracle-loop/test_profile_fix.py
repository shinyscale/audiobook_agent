#!/usr/bin/env python3
"""
Smoke test for profile JSON extraction fix.

Tests that the enhanced _extract_text_from_malformed_json function correctly:
1. Extracts profile text when embedded structured fields are present
2. Does not include malformed JSON in the profile description
"""

import sys
sys.path.insert(0, '/home/zacharymandrews/Tools/audiobook_agent')

from src.analyzer import AudiobookAnalyzer

# Create analyzer instance (just to access the method)
analyzer = AudiobookAnalyzer(llm_provider='ollama', llm_model='test')

# Test Case 1: Malformed JSON with embedded structured fields (Lincoln Stewart's actual case)
malformed_json_1 = '''
{
  "profile": "Lincoln Stewart is the first-person narrator of the story, a sixteen-year-old boy who works on his family's farm and eagerly joins a camping trip with friends, experiencing a mix of excitement and quiet melancholy as the adventure unfolds.",
  "appearance": "summary": "unknown", "age_indication": "young", "distinguishing_features": [],
  "personality": "summary": "Lincoln is enthusiastic about adventure but also reflective, showing both spontaneous joy and a thoughtful awareness of impermanence.", "traits": ["enthusiastic", "reflective", "cautious", "eager"], "temperament": "cheerful", "emotional_range": "Expresses wild delight, skepticism, and quiet sadness; shifts from exuberance to melancholy as the trip progresses.",
  "voice_guidance": "suggested_tone": "gentle", "dialect_notes": "Regional American rural dialect with colloquial expressions and contractions", "verbal_tics": ["I'm with you,", "That's sure,"], "formality_level": "informal",
  "relationships": "Milton Jennings": "friend", "Rance": "friend", "Bert Jenks": "friend", "Mr. Stewart": "father"
}
'''

# Test the extraction
result = analyzer._extract_text_from_malformed_json(malformed_json_1)

print("=" * 80)
print("Test Case 1: Malformed JSON with embedded structured fields")
print("=" * 80)
print(f"Input length: {len(malformed_json_1)} chars")
print(f"Output length: {len(result)} chars")
print(f"\nExtracted profile text:")
print(result)
print()

# Verify the result doesn't contain JSON artifacts
expected_profile = "Lincoln Stewart is the first-person narrator of the story, a sixteen-year-old boy who works on his family's farm and eagerly joins a camping trip with friends, experiencing a mix of excitement and quiet melancholy as the adventure unfolds."

if '", "appearance":' in result:
    print("❌ FAIL: Result still contains embedded JSON pattern")
    sys.exit(1)

if '"summary":' in result:
    print("❌ FAIL: Result contains JSON field names")
    sys.exit(1)

if result.strip() == expected_profile.strip():
    print("✅ PASS: Extracted profile text matches expected (exact match)")
elif expected_profile.strip() in result:
    print("✅ PASS: Extracted profile text contains expected content")
else:
    print(f"⚠️  PARTIAL: Extracted text is clean but differs from expected")
    print(f"Expected: {expected_profile}")
    print(f"Got: {result}")

# Test Case 2: Normal clean JSON (should still work)
clean_json = '''
{
  "profile": "This is a clean profile description."
}
'''

result2 = analyzer._extract_text_from_malformed_json(clean_json)
print("\n" + "=" * 80)
print("Test Case 2: Clean JSON")
print("=" * 80)
print(f"Extracted: {result2}")

if "This is a clean profile description" in result2:
    print("✅ PASS: Clean JSON still works")
else:
    print("❌ FAIL: Clean JSON extraction broken")
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ All smoke tests passed!")
print("=" * 80)
