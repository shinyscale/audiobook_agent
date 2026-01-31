"""Smoke test for Wolfsheim spelling variant merge fix."""

import sys
sys.path.insert(0, "../src")

from utils.similarity import names_similar

# Test the fuzzy matching function
name1 = "Meyer Wolfsheim"
name2 = "Meyer Wolfshiem"

similarity_passes = names_similar(name1, name2)

print(f"Testing fuzzy matching for Wolfsheim variants:")
print(f"  Name 1: '{name1}'")
print(f"  Name 2: '{name2}'")
print(f"  Fuzzy match (85% threshold): {similarity_passes}")
print()

if similarity_passes:
    print("✓ PASS: names_similar() returns True for Wolfsheim/Wolfshiem")
    print("  The fix should work - these names will be merged")
    sys.exit(0)
else:
    print("✗ FAIL: names_similar() returns False")
    print("  The fix may not work - threshold may be too high")
    sys.exit(1)
