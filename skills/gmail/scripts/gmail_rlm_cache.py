"""
Gmail RLM Caching Layer

This module provides a disk-based caching layer for RLM LLM queries.
Caching reduces costs by avoiding redundant API calls for identical prompts.

Features:
- SHA256-based cache keys from prompt+context+model
- TTL-based expiration (default: 24 hours)
- Cache stats (hits, misses, tokens saved)
- JSON file storage in temp directory
"""

import hashlib
import json
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class CacheEntry:
    """Represents a cached LLM query result."""
    result: str
    created_at: str
    tokens_saved: int
    model: str
    prompt_hash: str  # For debugging/verification


class QueryCache:
    """
    Disk-based cache for LLM query results.

    Uses SHA256 hashing of prompt+context+model to create cache keys.
    Entries expire after ttl_hours (default: 24).

    Usage:
        cache = QueryCache()
        key = cache.get_key(prompt, context, model)

        # Check cache
        if result := cache.get(key):
            return result

        # ... make API call ...

        # Store result
        cache.set(key, result, tokens_used, model)
    """

    def __init__(self, cache_dir: str = None, ttl_hours: int = 24):
        """
        Initialize the cache.

        Args:
            cache_dir: Directory for cache files (default: temp dir)
            ttl_hours: Time-to-live in hours (default: 24)
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / "rlm_cache"

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
        self.hits = 0
        self.misses = 0
        self.tokens_saved = 0

    def get_key(self, prompt: str, context: str, model: str) -> str:
        """
        Generate a cache key from prompt, context, and model.

        Args:
            prompt: The LLM prompt
            context: The context data
            model: The model name

        Returns:
            SHA256 hash string
        """
        content = f"{prompt}|{context}|{model}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"{key}.json"

    def get(self, key: str) -> Optional[str]:
        """
        Retrieve a cached result if exists and not expired.

        Args:
            key: Cache key from get_key()

        Returns:
            Cached result string, or None if not found/expired
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            data = json.loads(cache_path.read_text())
            entry = CacheEntry(**data)

            # Check expiration
            created = datetime.fromisoformat(entry.created_at)
            if datetime.now() - created > timedelta(hours=self.ttl_hours):
                # Expired - remove and return None
                cache_path.unlink(missing_ok=True)
                return None

            # Valid cache hit
            self.hits += 1
            self.tokens_saved += entry.tokens_saved
            return entry.result

        except (json.JSONDecodeError, TypeError, KeyError):
            # Corrupted cache file
            cache_path.unlink(missing_ok=True)
            return None

    def set(self, key: str, result: str, tokens: int, model: str) -> None:
        """
        Store a result in the cache.

        Args:
            key: Cache key from get_key()
            result: LLM response to cache
            tokens: Total tokens used (for stats)
            model: Model name (for verification)
        """
        entry = CacheEntry(
            result=result,
            created_at=datetime.now().isoformat(),
            tokens_saved=tokens,
            model=model,
            prompt_hash=key[:16]  # Store partial hash for debugging
        )

        cache_path = self._get_cache_path(key)
        cache_path.write_text(json.dumps(asdict(entry), indent=2))

    def stats(self) -> dict:
        """
        Return cache statistics.

        Returns:
            Dict with hits, misses, hit_rate, tokens_saved
        """
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 3),
            "tokens_saved": self.tokens_saved
        }

    def clear(self) -> int:
        """
        Clear all cached entries.

        Returns:
            Number of entries cleared
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1
        return count

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(cache_file.read_text())
                created = datetime.fromisoformat(data.get("created_at", ""))
                if datetime.now() - created > timedelta(hours=self.ttl_hours):
                    cache_file.unlink()
                    count += 1
            except (json.JSONDecodeError, ValueError):
                cache_file.unlink()
                count += 1
        return count


# Global cache instance
_cache: Optional[QueryCache] = None


def get_cache() -> Optional[QueryCache]:
    """Get the global cache instance."""
    return _cache


def init_cache(cache_dir: str = None, ttl_hours: int = 24) -> QueryCache:
    """Initialize or reset the global cache."""
    global _cache
    _cache = QueryCache(cache_dir=cache_dir, ttl_hours=ttl_hours)
    return _cache


def disable_cache() -> None:
    """Disable caching by setting global cache to None."""
    global _cache
    _cache = None


# =============================================================================
# Security Pattern Caching
# =============================================================================

@dataclass
class SecurityCacheEntry:
    """Cached security pattern analysis result."""
    result: dict
    created_at: str
    ioc: str
    ioc_type: str


class SecurityPatternCache:
    """
    Specialized cache for security patterns (separate from general LLM cache).

    Use cases:
    - Cache IOC extractions (same malware hash seen 100 times)
    - Cache severity classifications (same alert type from same tool)
    - Cache MITRE mappings (same attack technique)

    Longer TTL than general cache (7 days vs 24 hours) since security
    patterns are more stable over time.

    Usage:
        sec_cache = SecurityPatternCache()

        # Check cache
        if cached := sec_cache.get_ioc_analysis("192.168.1.1", "ip"):
            return cached

        # ... perform analysis ...

        # Store result
        sec_cache.cache_ioc_analysis("192.168.1.1", "ip", analysis_result)
    """

    def __init__(self, cache_dir: str = None, ttl_hours: int = 168):
        """
        Initialize security pattern cache.

        Args:
            cache_dir: Directory for cache files (default: temp/security_cache)
            ttl_hours: Time-to-live in hours (default: 168 = 7 days)
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / "security_cache"

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
        self.hits = 0
        self.misses = 0

    def _get_key(self, ioc: str, ioc_type: str, analysis_type: str = "general") -> str:
        """Generate cache key for IOC analysis."""
        content = f"{ioc_type}:{ioc}:{analysis_type}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        return self.cache_dir / f"sec_{key}.json"

    def get_ioc_analysis(self, ioc: str, ioc_type: str) -> Optional[dict]:
        """
        Retrieve cached IOC analysis.

        Args:
            ioc: The IOC value (IP, domain, hash, etc.)
            ioc_type: Type of IOC ("ip", "domain", "hash", "email", "url")

        Returns:
            Cached analysis dict or None
        """
        key = self._get_key(ioc, ioc_type)
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            self.misses += 1
            return None

        try:
            data = json.loads(cache_path.read_text())
            entry = SecurityCacheEntry(**data)

            # Check expiration
            created = datetime.fromisoformat(entry.created_at)
            if datetime.now() - created > timedelta(hours=self.ttl_hours):
                cache_path.unlink(missing_ok=True)
                self.misses += 1
                return None

            self.hits += 1
            return entry.result

        except (json.JSONDecodeError, TypeError, KeyError):
            cache_path.unlink(missing_ok=True)
            self.misses += 1
            return None

    def cache_ioc_analysis(self, ioc: str, ioc_type: str, analysis: dict) -> None:
        """
        Store IOC analysis result.

        Args:
            ioc: The IOC value
            ioc_type: Type of IOC
            analysis: Analysis result dict
        """
        key = self._get_key(ioc, ioc_type)
        entry = SecurityCacheEntry(
            result=analysis,
            created_at=datetime.now().isoformat(),
            ioc=ioc,
            ioc_type=ioc_type
        )

        cache_path = self._get_cache_path(key)
        cache_path.write_text(json.dumps(asdict(entry), indent=2))

    def get_mitre_mapping(self, alert_signature: str) -> Optional[list[str]]:
        """
        Retrieve cached MITRE technique mapping.

        Args:
            alert_signature: Unique signature of alert (e.g., hash of subject+snippet)

        Returns:
            List of MITRE technique IDs or None
        """
        key = self._get_key(alert_signature, "mitre", "mapping")
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            self.misses += 1
            return None

        try:
            data = json.loads(cache_path.read_text())
            created = datetime.fromisoformat(data.get("created_at", ""))
            if datetime.now() - created > timedelta(hours=self.ttl_hours):
                cache_path.unlink(missing_ok=True)
                self.misses += 1
                return None

            self.hits += 1
            return data.get("result", [])

        except (json.JSONDecodeError, ValueError):
            cache_path.unlink(missing_ok=True)
            self.misses += 1
            return None

    def cache_mitre_mapping(self, alert_signature: str, techniques: list[str]) -> None:
        """
        Store MITRE technique mapping.

        Args:
            alert_signature: Unique signature of alert
            techniques: List of MITRE technique IDs
        """
        key = self._get_key(alert_signature, "mitre", "mapping")
        cache_path = self._get_cache_path(key)

        data = {
            "result": techniques,
            "created_at": datetime.now().isoformat(),
            "ioc": alert_signature,
            "ioc_type": "mitre"
        }

        cache_path.write_text(json.dumps(data, indent=2))

    def stats(self) -> dict:
        """Return cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0

        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 3)
        }

    def clear(self) -> int:
        """Clear all security cache entries."""
        count = 0
        for cache_file in self.cache_dir.glob("sec_*.json"):
            cache_file.unlink()
            count += 1
        return count


@dataclass
class ThreatObservation:
    """Single observation of a threat pattern."""
    timestamp: str
    ioc: str
    ioc_type: str
    context: dict
    severity: str


class ThreatPatternStore:
    """
    Persistent storage for observed threat patterns across sessions.

    Enables:
    - Historical IOC tracking
    - Recurring attack pattern detection
    - Baseline for anomaly detection

    Data is stored as JSON files with 30-day default retention.

    Usage:
        store = ThreatPatternStore()

        # Record IOC observation
        store.add_observed_ioc(
            "192.168.1.100",
            "ip",
            {"alert_type": "brute_force", "count": 5}
        )

        # Get history
        history = store.get_ioc_history("192.168.1.100")
        if len(history) >= 3:
            print("Recurring threat detected!")
    """

    def __init__(self, store_dir: str = None, retention_days: int = 30):
        """
        Initialize threat pattern store.

        Args:
            store_dir: Directory for threat data (default: temp/threat_store)
            retention_days: How long to keep observations (default: 30 days)
        """
        if store_dir:
            self.store_dir = Path(store_dir)
        else:
            self.store_dir = Path(tempfile.gettempdir()) / "threat_store"

        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days

    def _get_ioc_file(self, ioc: str, ioc_type: str) -> Path:
        """Get file path for IOC observations."""
        # Hash IOC to create filename (handles special chars)
        ioc_hash = hashlib.sha256(f"{ioc_type}:{ioc}".encode()).hexdigest()[:16]
        return self.store_dir / f"ioc_{ioc_hash}.json"

    def add_observed_ioc(self, ioc: str, ioc_type: str, context: dict) -> None:
        """
        Record IOC observation with timestamp and context.

        Args:
            ioc: The IOC value
            ioc_type: Type of IOC ("ip", "domain", "hash", etc.)
            context: Additional context (alert details, severity, etc.)
        """
        ioc_file = self._get_ioc_file(ioc, ioc_type)

        # Load existing observations
        observations = []
        if ioc_file.exists():
            try:
                data = json.loads(ioc_file.read_text())
                observations = data.get("observations", [])
            except (json.JSONDecodeError, KeyError):
                observations = []

        # Add new observation
        observation = ThreatObservation(
            timestamp=datetime.now().isoformat(),
            ioc=ioc,
            ioc_type=ioc_type,
            context=context,
            severity=context.get("severity", "unknown")
        )
        observations.append(asdict(observation))

        # Cleanup old observations (retention policy)
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        observations = [
            obs for obs in observations
            if datetime.fromisoformat(obs["timestamp"]) > cutoff
        ]

        # Save
        data = {
            "ioc": ioc,
            "ioc_type": ioc_type,
            "observations": observations,
            "first_seen": observations[0]["timestamp"] if observations else None,
            "last_seen": observations[-1]["timestamp"] if observations else None,
            "observation_count": len(observations)
        }

        ioc_file.write_text(json.dumps(data, indent=2))

    def get_ioc_history(self, ioc: str, ioc_type: str = None) -> list[dict]:
        """
        Retrieve all observations of an IOC.

        Args:
            ioc: The IOC value
            ioc_type: Type of IOC (if known)

        Returns:
            List of observation dicts with timestamp, context, severity
        """
        # If type not specified, try common types
        if ioc_type:
            types_to_check = [ioc_type]
        else:
            types_to_check = ["ip", "domain", "hash", "email", "url"]

        all_observations = []
        for ioc_t in types_to_check:
            ioc_file = self._get_ioc_file(ioc, ioc_t)
            if ioc_file.exists():
                try:
                    data = json.loads(ioc_file.read_text())
                    all_observations.extend(data.get("observations", []))
                except (json.JSONDecodeError, KeyError):
                    continue

        return all_observations

    def add_attack_pattern(self, pattern: dict) -> None:
        """
        Store detected attack pattern for future reference.

        Args:
            pattern: Attack pattern dict with:
                - pattern_type: Type of attack (e.g., "kill_chain", "brute_force")
                - description: Human-readable description
                - mitre_techniques: List of technique IDs
                - severity: P1-P5
                - indicators: List of IOCs involved
        """
        pattern_file = self.store_dir / "attack_patterns.json"

        # Load existing patterns
        patterns = []
        if pattern_file.exists():
            try:
                patterns = json.loads(pattern_file.read_text())
            except json.JSONDecodeError:
                patterns = []

        # Add timestamp
        pattern["timestamp"] = datetime.now().isoformat()

        patterns.append(pattern)

        # Cleanup old patterns
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        patterns = [
            p for p in patterns
            if datetime.fromisoformat(p["timestamp"]) > cutoff
        ]

        pattern_file.write_text(json.dumps(patterns, indent=2))

    def search_similar_patterns(
        self,
        current_pattern: dict,
        min_similarity: float = 0.7
    ) -> list[dict]:
        """
        Find historically similar attack patterns.

        Args:
            current_pattern: Pattern to compare
            min_similarity: Minimum similarity score (0-1)

        Returns:
            List of similar patterns from history
        """
        pattern_file = self.store_dir / "attack_patterns.json"

        if not pattern_file.exists():
            return []

        try:
            historical_patterns = json.loads(pattern_file.read_text())
        except json.JSONDecodeError:
            return []

        similar = []
        current_techniques = set(current_pattern.get("mitre_techniques", []))
        current_type = current_pattern.get("pattern_type", "")

        for hist_pattern in historical_patterns:
            # Calculate similarity based on MITRE techniques overlap
            hist_techniques = set(hist_pattern.get("mitre_techniques", []))

            if current_techniques and hist_techniques:
                intersection = len(current_techniques & hist_techniques)
                union = len(current_techniques | hist_techniques)
                similarity = intersection / union if union > 0 else 0.0
            else:
                similarity = 0.0

            # Boost similarity if same pattern type
            if hist_pattern.get("pattern_type") == current_type:
                similarity = min(1.0, similarity + 0.2)

            if similarity >= min_similarity:
                hist_pattern["similarity_score"] = round(similarity, 3)
                similar.append(hist_pattern)

        # Sort by similarity
        similar.sort(key=lambda x: -x["similarity_score"])

        return similar

    def stats(self) -> dict:
        """Return threat store statistics."""
        ioc_files = list(self.store_dir.glob("ioc_*.json"))
        pattern_file = self.store_dir / "attack_patterns.json"

        total_observations = 0
        for ioc_file in ioc_files:
            try:
                data = json.loads(ioc_file.read_text())
                total_observations += data.get("observation_count", 0)
            except (json.JSONDecodeError, KeyError):
                continue

        pattern_count = 0
        if pattern_file.exists():
            try:
                patterns = json.loads(pattern_file.read_text())
                pattern_count = len(patterns)
            except json.JSONDecodeError:
                pass

        return {
            "unique_iocs": len(ioc_files),
            "total_observations": total_observations,
            "attack_patterns": pattern_count,
            "retention_days": self.retention_days
        }

    def clear(self) -> int:
        """Clear all stored threat data."""
        count = 0
        for file in self.store_dir.glob("*.json"):
            file.unlink()
            count += 1
        return count


# Global security cache and threat store instances
_security_cache: Optional[SecurityPatternCache] = None
_threat_store: Optional[ThreatPatternStore] = None


def get_security_cache() -> Optional[SecurityPatternCache]:
    """Get the global security pattern cache instance."""
    return _security_cache


def init_security_cache(cache_dir: str = None, ttl_hours: int = 168) -> SecurityPatternCache:
    """Initialize or reset the global security cache."""
    global _security_cache
    _security_cache = SecurityPatternCache(cache_dir=cache_dir, ttl_hours=ttl_hours)
    return _security_cache


def get_threat_store() -> Optional[ThreatPatternStore]:
    """Get the global threat pattern store instance."""
    return _threat_store


def init_threat_store(store_dir: str = None, retention_days: int = 30) -> ThreatPatternStore:
    """Initialize or reset the global threat pattern store."""
    global _threat_store
    _threat_store = ThreatPatternStore(store_dir=store_dir, retention_days=retention_days)
    return _threat_store
