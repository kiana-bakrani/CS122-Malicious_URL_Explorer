"""Estimate hosting countries using DNS and a local DB-IP database."""

from concurrent.futures import ThreadPoolExecutor, wait
from contextlib import closing
from ipaddress import ip_address
import logging
from pathlib import Path
import sqlite3
import time
try:
    import dns.exception
    import dns.resolver
    import maxminddb
except ImportError:
    maxminddb = None


UNKNOWN = "Unknown"
CACHE_SECONDS = 24 * 60 * 60
DNS_BUDGET_SECONDS = 8
logger = logging.getLogger(__name__)


def resolve_country(host, database_path):
    try:
        addresses = [ip_address(host)]
    except ValueError:
        resolver = dns.resolver.Resolver()
        addresses = []
        for record_type in ("A", "AAAA"):
            try:
                answers = resolver.resolve(host, record_type, lifetime=1.5, search=False)
                addresses.extend(ip_address(answer.address) for answer in answers)
            except (dns.exception.DNSException, ValueError):
                continue

    countries = set()
    with maxminddb.open_database(str(database_path)) as database:
        for address in addresses:
            if not address.is_global or address.is_multicast:
                continue
            entry = database.get(str(address)) or {}
            code = entry.get("country", {}).get("iso_code")
            if code:
                countries.add(code)
    if len(countries) == 1:
        return countries.pop()
    return UNKNOWN


def add_countries(records, cache_dir):
    """Add ISO alpha-2 country codes to the filtered records."""
    records = records.copy()
    if "country" not in records:
        records["country"] = UNKNOWN
    records["country"] = records["country"].fillna(UNKNOWN).replace("", UNKNOWN)
    if records.empty or "hostname" not in records:
        return records

    unresolved = records["country"].eq(UNKNOWN)
    hosts = records.loc[unresolved, "hostname"].astype("string").str.strip().str.lower().str.rstrip(".")
    unique_hosts = hosts.dropna().unique().tolist()
    unique_hosts = [host for host in unique_hosts if host]
    if not unique_hosts:
        return records

    if maxminddb is None:
        logger.warning("Install dnspython and maxminddb to enable country lookup")
        return records

    cache_dir = Path(cache_dir)
    database_path = cache_dir / "dbip-country-lite.mmdb"
    if not database_path.is_file():
        logger.warning("Country database missing at %s", database_path)
        return records

    now = time.time()
    version = database_path.stat().st_mtime_ns
    cache_dir.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(cache_dir / "country_cache.sqlite3")) as cache, cache:
        cache.execute(
            """CREATE TABLE IF NOT EXISTS countries (
                host TEXT PRIMARY KEY, country TEXT NOT NULL,
                checked_at REAL NOT NULL, database_version INTEGER NOT NULL
            )"""
        )
        known = dict(cache.execute(
            "SELECT host, country FROM countries WHERE checked_at > ? AND database_version = ?",
            (now - CACHE_SECONDS, version),
        ))

    missing = [host for host in unique_hosts if host not in known]
    resolved = {}
    if missing:
        executor = ThreadPoolExecutor(max_workers=32)
        try:
            lookups = {executor.submit(resolve_country, host, database_path): host for host in missing}
            finished, _ = wait(lookups, timeout=DNS_BUDGET_SECONDS)
            for result in finished:
                try:
                    country = result.result()
                except (ImportError, OSError, ValueError):
                    logger.warning("Country lookup failed", exc_info=True)
                    continue
                if country != UNKNOWN:
                    resolved[lookups[result]] = country
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    if resolved:
        with closing(sqlite3.connect(cache_dir / "country_cache.sqlite3")) as cache, cache:
            cache.executemany(
                "INSERT OR REPLACE INTO countries VALUES (?, ?, ?, ?)",
                [(host, country, now, version) for host, country in resolved.items()],
            )
        known.update(resolved)

    records.loc[unresolved, "country"] = hosts.map(known).fillna(UNKNOWN)
    return records
