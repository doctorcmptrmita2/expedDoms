"""
Domain Quality Score Calculator.
Calculates a quality score (0-100) for dropped domains based on various factors.
"""
from typing import Optional, Set
import re

# Common English words for dictionary check (top brandable words)
COMMON_WORDS: Set[str] = {
    # Short words (2-4 letters)
    "app", "web", "net", "dev", "api", "hub", "lab", "box", "bot", "pro",
    "max", "top", "new", "hot", "big", "one", "all", "get", "buy", "pay",
    "run", "fly", "go", "do", "be", "my", "we", "up", "on", "in", "to",
    "ai", "io", "co", "tv", "me", "us", "uk", "eu", "la", "ny",
    
    # Tech words (5-6 letters)
    "cloud", "cyber", "pixel", "smart", "swift", "rapid", "ultra", "micro",
    "super", "hyper", "alpha", "beta", "delta", "gamma", "omega", "prime",
    "elite", "boost", "spark", "flash", "blaze", "storm", "force", "power",
    "logic", "nexus", "pulse", "vibe", "flux", "core", "edge", "sync",
    "tech", "data", "code", "hack", "byte", "link", "node", "mesh",
    
    # Business words
    "trade", "market", "store", "shop", "deal", "sale", "stock", "fund",
    "money", "cash", "gold", "bank", "trust", "legal", "audit", "brand",
    "media", "press", "news", "blog", "wiki", "forum", "group", "team",
    
    # Creative words
    "design", "style", "trend", "craft", "create", "build", "make", "form",
    "art", "music", "video", "photo", "game", "play", "fun", "cool",
    
    # Action words
    "find", "search", "track", "watch", "learn", "teach", "guide", "help",
    "start", "launch", "grow", "scale", "level", "boost", "drive", "move",
    
    # Descriptive words
    "fast", "quick", "easy", "simple", "clean", "clear", "fresh", "pure",
    "safe", "secure", "free", "open", "direct", "instant", "global", "local",
    
    # Domain-specific
    "hosting", "domain", "server", "email", "mail", "inbox", "send", "chat",
    "call", "meet", "zoom", "live", "stream", "cast", "feed", "post",
}

# Premium TLD weights (higher = more valuable)
TLD_WEIGHTS = {
    "com": 15,
    "net": 10,
    "org": 10,
    "io": 12,
    "co": 10,
    "dev": 14,
    "app": 14,
    "ai": 15,
    "tech": 8,
    "pro": 8,
    "me": 7,
    "tv": 7,
    "info": 5,
    "biz": 5,
    "name": 4,
    "blog": 6,
    "shop": 7,
    "store": 7,
    "site": 5,
    "online": 5,
    "cloud": 8,
    "digital": 6,
    "media": 6,
    "news": 6,
    "live": 6,
}


def is_dictionary_word(word: str) -> bool:
    """
    Check if a word is in our dictionary of common/brandable words.
    
    Args:
        word: The word to check (lowercase)
        
    Returns:
        True if word is in dictionary
    """
    return word.lower() in COMMON_WORDS


def is_pronounceable(domain: str) -> bool:
    """
    Check if a domain is pronounceable (has vowels and consonants in reasonable pattern).
    
    Args:
        domain: Domain name without TLD
        
    Returns:
        True if domain appears pronounceable
    """
    vowels = set('aeiou')
    consonants = set('bcdfghjklmnpqrstvwxyz')
    
    domain_lower = domain.lower()
    
    # Must have at least one vowel
    has_vowel = any(c in vowels for c in domain_lower)
    
    # Check for too many consecutive consonants (>4)
    consonant_count = 0
    max_consonants = 0
    for c in domain_lower:
        if c in consonants:
            consonant_count += 1
            max_consonants = max(max_consonants, consonant_count)
        else:
            consonant_count = 0
    
    return has_vowel and max_consonants <= 4


def calculate_length_score(length: int) -> int:
    """
    Calculate score based on domain length.
    Shorter domains are more valuable.
    
    Args:
        length: Length of domain (without TLD)
        
    Returns:
        Score component (0-30)
    """
    if length <= 2:
        return 30  # 2-letter domains are extremely rare/valuable
    elif length <= 3:
        return 28  # 3-letter domains are very valuable
    elif length <= 4:
        return 25  # 4-letter domains are valuable
    elif length <= 5:
        return 20
    elif length <= 6:
        return 15
    elif length <= 8:
        return 10
    elif length <= 10:
        return 5
    elif length <= 15:
        return 2
    else:
        return 0


def calculate_charset_score(domain: str) -> int:
    """
    Calculate score based on character composition.
    
    Args:
        domain: Domain name without TLD
        
    Returns:
        Score component (0-20)
    """
    # Only letters is best
    if domain.isalpha():
        return 20
    
    # Only numbers (numeric domains)
    if domain.isdigit():
        # Short numeric domains are valuable
        if len(domain) <= 4:
            return 15
        return 8
    
    # Alphanumeric without hyphens
    if domain.isalnum():
        # Numbers at end (e.g., app2, web3) is acceptable
        if domain[-1].isdigit() and domain[:-1].isalpha():
            return 15
        # Numbers at start is less valuable
        if domain[0].isdigit():
            return 8
        return 10
    
    # Contains hyphens
    if '-' in domain:
        # Single hyphen in middle is acceptable
        if domain.count('-') == 1 and not domain.startswith('-') and not domain.endswith('-'):
            return 5
        return 0
    
    return 5


def calculate_pattern_score(domain: str) -> int:
    """
    Calculate score based on domain patterns (CVCV, repeating, etc.).
    
    Args:
        domain: Domain name without TLD
        
    Returns:
        Score component (0-15)
    """
    score = 0
    domain_lower = domain.lower()
    
    # Check for pronounceable pattern
    if is_pronounceable(domain_lower):
        score += 8
    
    # Bonus for common suffixes
    common_suffixes = ['ly', 'ify', 'fy', 'er', 'io', 'ia', 'eo', 'it', 'ix', 'ex', 'ox']
    for suffix in common_suffixes:
        if domain_lower.endswith(suffix) and len(domain_lower) > len(suffix) + 1:
            score += 3
            break
    
    # Bonus for common prefixes
    common_prefixes = ['get', 'my', 'the', 'go', 'try', 'use', 'be', 'we', 'i']
    for prefix in common_prefixes:
        if domain_lower.startswith(prefix) and len(domain_lower) > len(prefix) + 1:
            score += 3
            break
    
    # Penalty for repeated characters (e.g., "aaa")
    if re.search(r'(.)\1{2,}', domain_lower):
        score -= 5
    
    return max(0, min(15, score))


def calculate_tld_score(tld: str) -> int:
    """
    Calculate score based on TLD value.
    
    Args:
        tld: Top-level domain (without dot)
        
    Returns:
        Score component (0-15)
    """
    return TLD_WEIGHTS.get(tld.lower(), 3)


def calculate_word_score(domain: str) -> int:
    """
    Calculate score based on dictionary word presence.
    
    Args:
        domain: Domain name without TLD
        
    Returns:
        Score component (0-20)
    """
    domain_lower = domain.lower()
    
    # Exact dictionary word match
    if is_dictionary_word(domain_lower):
        return 20
    
    # Check if domain contains a dictionary word
    for word in COMMON_WORDS:
        if len(word) >= 3 and word in domain_lower:
            # Word at start or end is better
            if domain_lower.startswith(word) or domain_lower.endswith(word):
                return 12
            return 8
    
    # Check for compound words (two dictionary words)
    for word1 in COMMON_WORDS:
        if len(word1) >= 2 and domain_lower.startswith(word1):
            remainder = domain_lower[len(word1):]
            if is_dictionary_word(remainder):
                return 15  # Compound word bonus
    
    return 0


def calculate_quality_score(
    domain: str,
    tld: str,
    include_breakdown: bool = False
) -> int | dict:
    """
    Calculate comprehensive quality score for a domain.
    
    Args:
        domain: Domain name (SLD part only, without TLD)
        tld: Top-level domain (without dot)
        include_breakdown: If True, return dict with score breakdown
        
    Returns:
        Quality score (0-100) or dict with breakdown if include_breakdown=True
    """
    # Clean inputs
    domain = domain.lower().strip()
    tld = tld.lower().strip().lstrip('.')
    
    # Calculate individual scores
    length_score = calculate_length_score(len(domain))
    charset_score = calculate_charset_score(domain)
    pattern_score = calculate_pattern_score(domain)
    tld_score = calculate_tld_score(tld)
    word_score = calculate_word_score(domain)
    
    # Calculate total (max 100)
    total = length_score + charset_score + pattern_score + tld_score + word_score
    final_score = min(100, max(0, total))
    
    if include_breakdown:
        return {
            "total": final_score,
            "breakdown": {
                "length": length_score,
                "charset": charset_score,
                "pattern": pattern_score,
                "tld": tld_score,
                "word": word_score
            },
            "domain": domain,
            "tld": tld,
            "full_domain": f"{domain}.{tld}"
        }
    
    return final_score


def get_quality_tier(score: int) -> str:
    """
    Get quality tier label based on score.
    
    Args:
        score: Quality score (0-100)
        
    Returns:
        Tier label
    """
    if score >= 85:
        return "Premium"
    elif score >= 70:
        return "Excellent"
    elif score >= 55:
        return "Good"
    elif score >= 40:
        return "Average"
    elif score >= 25:
        return "Below Average"
    else:
        return "Low"


def batch_calculate_scores(domains: list[tuple[str, str]]) -> list[dict]:
    """
    Calculate quality scores for multiple domains.
    
    Args:
        domains: List of (domain, tld) tuples
        
    Returns:
        List of score results with breakdowns
    """
    results = []
    for domain, tld in domains:
        result = calculate_quality_score(domain, tld, include_breakdown=True)
        result["tier"] = get_quality_tier(result["total"])
        results.append(result)
    
    return sorted(results, key=lambda x: x["total"], reverse=True)






