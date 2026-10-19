import time
from app.cache import ResponseCache


def test_cache_set_and_get():
    cache = ResponseCache(ttl_seconds=60)
    data = {"answer": "USD 4.21 billion", "confidence": 0.95, "citations": []}
    
    cache.set("C-01", "What was the market size?", {"R-101", "R-103"}, data)
    retrieved = cache.get("C-01", "What was the market size?", {"R-101", "R-103"})
    
    assert retrieved is not None
    assert retrieved["answer"] == "USD 4.21 billion"


def test_cache_normalizes_casing_and_whitespace():
    cache = ResponseCache(ttl_seconds=60)
    data = {"answer": "USD 4.21 billion", "confidence": 0.95}
    
    cache.set("C-01", "  What was the MARKET size?  ", {"R-101"}, data)
    retrieved = cache.get("C-01", "what was the market size?", {"R-101"})
    
    assert retrieved is not None
    assert retrieved["answer"] == "USD 4.21 billion"


def test_cache_multi_tenant_isolation_prevents_leakage():
    cache = ResponseCache(ttl_seconds=60)
    c01_data = {"answer": "Proprietary R-101 data: USD 4.21 billion", "confidence": 0.95}
    
    # C-01 asks about water market
    cache.set("C-01", "smart water market size", {"R-101", "R-103"}, c01_data)
    
    # C-02 asks identical question with C-02 client_id and entitlements
    c02_result = cache.get("C-02", "smart water market size", {"R-103"})
    
    assert c02_result is None, "Client C-02 must never retrieve cached data from C-01"


def test_cache_invalidates_on_entitlement_change():
    cache = ResponseCache(ttl_seconds=60)
    data = {"answer": "Initial view", "confidence": 0.9}
    
    cache.set("C-01", "market summary", {"R-101"}, data)
    
    # Client is granted R-102
    result = cache.get("C-01", "market summary", {"R-101", "R-102"})
    assert result is None, "Cache must invalidate when entitlement set changes"


def test_cache_never_caches_escalations_or_empty_answers():
    cache = ResponseCache(ttl_seconds=60)
    
    # Escalated response
    escalated_data = {"answer": "I don't know", "escalation_reason": "low_confidence"}
    cache.set("C-01", "uncertain question", {"R-101"}, escalated_data)
    assert cache.get("C-01", "uncertain question", {"R-101"}) is None
    
    # Empty answer
    empty_data = {"answer": ""}
    cache.set("C-01", "empty question", {"R-101"}, empty_data)
    assert cache.get("C-01", "empty question", {"R-101"}) is None


def test_cache_ttl_expiration():
    cache = ResponseCache(ttl_seconds=1)
    data = {"answer": "Fast answer"}
    
    cache.set("C-01", "quick question", {"R-101"}, data)
    assert cache.get("C-01", "quick question", {"R-101"}) is not None
    
    time.sleep(1.1)
    assert cache.get("C-01", "quick question", {"R-101"}) is None
