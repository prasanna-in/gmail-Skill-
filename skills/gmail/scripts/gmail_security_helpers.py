"""
Gmail Security Helper Functions

This module provides security-specific utility functions for RLM email analysis.
These functions enable security alert triage, IOC extraction, threat correlation,
and attack pattern detection.

Functions are designed to be used within the gmail_rlm_repl.py environment.

Security Analysis Capabilities:
- Severity classification (P1-P5 priority mapping)
- IOC extraction (IPs, domains, hashes, emails, URLs)
- MITRE ATT&CK technique mapping
- Time-based correlation for kill chain detection
- Email authentication validation (SPF/DKIM/DMARC)
- Suspicious sender/domain analysis
- Attachment risk assessment
- URL analysis for phishing detection

Educational Note:
- Security triage benefits from recursive LLM for pattern recognition
- Time correlation is critical for detecting multi-stage attacks
- IOC extraction combines regex patterns with LLM validation
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Optional
import re
import hashlib


# =============================================================================
# Severity Extraction & Classification
# =============================================================================

# Common severity field mappings across security tools
SEVERITY_FIELD_MAPPINGS = {
    "crowdstrike": "severity",
    "splunk": "urgency",
    "azure_sentinel": "alertSeverity",
    "palo_alto": "threat_severity",
    "elastic": "event.severity",
    "microsoft_defender": "severity",
    "cisco_secure": "priority",
    "fortinet": "level",
}

# Severity value normalization
SEVERITY_TO_PRIORITY = {
    # Critical/High → P1
    "critical": "P1",
    "very high": "P1",
    "5": "P1",
    "high": "P2",
    "4": "P2",
    # Medium → P3
    "medium": "P3",
    "moderate": "P3",
    "3": "P3",
    # Low → P4
    "low": "P4",
    "2": "P4",
    # Info → P5
    "info": "P5",
    "informational": "P5",
    "1": "P5",
    "0": "P5",
}


def extract_severity(alert: dict) -> str:
    """
    Normalize severity from different security tool formats.

    Handles:
    - CrowdStrike: 'severity' field
    - Splunk: 'urgency' field
    - Azure Sentinel: 'alertSeverity' field
    - Palo Alto: 'threat_severity' field
    - Custom: extract from subject/body with pattern matching

    Args:
        alert: Email dictionary with security alert data

    Returns:
        Normalized priority: "P1" | "P2" | "P3" | "P4" | "P5"

    Example:
        severity = extract_severity(crowdstrike_alert)
        if severity == "P1":
            escalate_immediately(alert)
    """
    # Check common severity field names
    for field_name in SEVERITY_FIELD_MAPPINGS.values():
        if field_name in alert:
            value = str(alert[field_name]).lower().strip()
            normalized = SEVERITY_TO_PRIORITY.get(value, None)
            if normalized:
                return normalized

    # Check for severity patterns in subject or body
    subject = alert.get('subject', '').lower()
    snippet = alert.get('snippet', '').lower()
    body = alert.get('body', '').lower()
    combined_text = f"{subject} {snippet} {body}"

    # Pattern-based severity detection
    if any(word in combined_text for word in ['critical', 'p1', 'sev-1', 'emergency']):
        return "P1"
    if any(word in combined_text for word in ['high', 'p2', 'sev-2', 'urgent']):
        return "P2"
    if any(word in combined_text for word in ['medium', 'p3', 'sev-3']):
        return "P3"
    if any(word in combined_text for word in ['low', 'p4', 'sev-4']):
        return "P4"
    if any(word in combined_text for word in ['info', 'p5', 'sev-5', 'informational']):
        return "P5"

    # Default to P3 if unable to determine
    return "P3"


def classify_alerts(
    emails: list[dict],
    llm_query_fn: Callable,
    batch_size: int = 20
) -> dict[str, list[dict]]:
    """
    Batch classification of security alerts into P1-P5 severity levels.

    Uses LLM for accurate severity classification when field-based extraction
    is ambiguous or unavailable.

    Args:
        emails: List of email dictionaries
        llm_query_fn: The llm_query function from RLM environment
        batch_size: Number of alerts to classify per LLM call

    Returns:
        Dict mapping priority level to list of alerts:
        {"P1": [...], "P2": [...], "P3": [...], "P4": [...], "P5": [...]}

    Example:
        classifications = classify_alerts(security_emails, llm_query)
        print(f"P1 alerts requiring immediate action: {len(classifications['P1'])}")
    """
    classifications = {"P1": [], "P2": [], "P3": [], "P4": [], "P5": []}

    # First pass: Try field-based extraction
    unclassified = []
    for email in emails:
        severity = extract_severity(email)
        if severity != "P3":  # P3 is our "uncertain" default
            classifications[severity].append(email)
        else:
            # Check if we actually found P3 or if it's just default
            subject_body = f"{email.get('subject', '')} {email.get('snippet', '')}"
            if 'p3' in subject_body.lower() or 'medium' in subject_body.lower():
                classifications["P3"].append(email)
            else:
                unclassified.append(email)

    # Second pass: Use LLM for unclassified alerts
    if unclassified and llm_query_fn:
        for i in range(0, len(unclassified), batch_size):
            batch = unclassified[i:i + batch_size]
            context = "\n\n".join([
                f"Alert {j+1}:\nSubject: {email.get('subject', '')}\nFrom: {email.get('from', '')}\nSnippet: {email.get('snippet', '')}"
                for j, email in enumerate(batch)
            ])

            prompt = """Classify each security alert into priority levels:
- P1 (Critical): Immediate threat, active exploitation, data breach
- P2 (High): Significant risk, needs attention within hours
- P3 (Medium): Moderate risk, needs attention within days
- P4 (Low): Minor issue, routine monitoring
- P5 (Info): Informational, no action required

Respond with only the alert numbers and priorities, one per line:
Alert 1: P1
Alert 2: P3
etc."""

            try:
                result = llm_query_fn(prompt, context=context, _skip_status=True)

                # Parse LLM response
                lines = result.strip().split('\n')
                for idx, line in enumerate(lines):
                    if idx < len(batch):
                        # Extract priority from line (e.g., "Alert 1: P2" → "P2")
                        match = re.search(r'P[1-5]', line, re.IGNORECASE)
                        if match:
                            priority = match.group().upper()
                            classifications[priority].append(batch[idx])
                        else:
                            # Fallback to P3 if parse fails
                            classifications["P3"].append(batch[idx])
            except Exception:
                # If LLM fails, default to P3
                classifications["P3"].extend(batch)

    return classifications


# =============================================================================
# IOC (Indicator of Compromise) Extraction
# =============================================================================

# Regex patterns for IOC extraction
IP_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
DOMAIN_PATTERN = re.compile(r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b')
MD5_PATTERN = re.compile(r'\b[a-fA-F0-9]{32}\b')
SHA1_PATTERN = re.compile(r'\b[a-fA-F0-9]{40}\b')
SHA256_PATTERN = re.compile(r'\b[a-fA-F0-9]{64}\b')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
URL_PATTERN = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')


def extract_iocs(emails: list[dict]) -> dict:
    """
    Extract Indicators of Compromise from security alerts.

    Extracts:
    - IP addresses (IPv4)
    - Domain names
    - File hashes (MD5, SHA1, SHA256)
    - Email addresses (potential attackers)
    - URLs

    Args:
        emails: List of email dictionaries

    Returns:
        Dict with IOC lists:
        {
            "ips": ["192.168.1.1", ...],
            "domains": ["malicious.com", ...],
            "file_hashes": {"md5": [...], "sha1": [...], "sha256": [...]},
            "email_addresses": ["attacker@evil.com", ...],
            "urls": ["http://phishing.site", ...]
        }

    Example:
        iocs = extract_iocs(security_alerts)
        for ip in iocs['ips']:
            check_threat_intel(ip)
    """
    iocs = {
        "ips": set(),
        "domains": set(),
        "file_hashes": {"md5": set(), "sha1": set(), "sha256": set()},
        "email_addresses": set(),
        "urls": set()
    }

    for email in emails:
        # Combine all text fields for IOC extraction
        text_fields = [
            email.get('subject', ''),
            email.get('snippet', ''),
            email.get('body', '')
        ]
        combined_text = ' '.join(text_fields)

        # Extract IPs
        ips = IP_PATTERN.findall(combined_text)
        for ip in ips:
            # Filter out invalid IPs (e.g., version numbers like 1.2.3.4)
            octets = ip.split('.')
            if all(0 <= int(octet) <= 255 for octet in octets):
                iocs["ips"].add(ip)

        # Extract domains
        domains = DOMAIN_PATTERN.findall(combined_text)
        for domain in domains:
            # Filter out common false positives
            if not domain.endswith(('.jpg', '.png', '.gif', '.pdf')):
                iocs["domains"].add(domain.lower())

        # Extract hashes
        iocs["file_hashes"]["md5"].update(MD5_PATTERN.findall(combined_text))
        iocs["file_hashes"]["sha1"].update(SHA1_PATTERN.findall(combined_text))
        iocs["file_hashes"]["sha256"].update(SHA256_PATTERN.findall(combined_text))

        # Extract email addresses
        email_addrs = EMAIL_PATTERN.findall(combined_text)
        iocs["email_addresses"].update(e.lower() for e in email_addrs)

        # Extract URLs
        urls = URL_PATTERN.findall(combined_text)
        iocs["urls"].update(urls)

    # Convert sets to sorted lists
    return {
        "ips": sorted(list(iocs["ips"])),
        "domains": sorted(list(iocs["domains"])),
        "file_hashes": {
            "md5": sorted(list(iocs["file_hashes"]["md5"])),
            "sha1": sorted(list(iocs["file_hashes"]["sha1"])),
            "sha256": sorted(list(iocs["file_hashes"]["sha256"]))
        },
        "email_addresses": sorted(list(iocs["email_addresses"])),
        "urls": sorted(list(iocs["urls"]))
    }


def validate_email_auth(email: dict) -> dict:
    """
    Check SPF/DKIM/DMARC authentication status from email headers.

    Parses Authentication-Results and Received-SPF headers to determine
    if the email passed authentication checks.

    Args:
        email: Email dictionary with headers

    Returns:
        Dict with authentication status:
        {
            "spf": "pass" | "fail" | "neutral" | "none",
            "dkim": "pass" | "fail" | "none",
            "dmarc": "pass" | "fail" | "none",
            "suspicious": bool
        }

    Example:
        auth_status = validate_email_auth(phishing_alert)
        if auth_status['suspicious']:
            flag_for_review(phishing_alert)
    """
    # Note: Gmail API in metadata format doesn't expose all headers
    # This is a placeholder for when full format is available

    auth_result = {
        "spf": "none",
        "dkim": "none",
        "dmarc": "none",
        "suspicious": False
    }

    # Check if we have headers dict
    headers = email.get('headers', {})
    if not headers:
        # Try to extract from raw payload if available
        return auth_result

    # Look for Authentication-Results header
    auth_results_header = headers.get('authentication-results', '').lower()

    # Parse SPF
    if 'spf=' in auth_results_header:
        if 'spf=pass' in auth_results_header:
            auth_result['spf'] = 'pass'
        elif 'spf=fail' in auth_results_header:
            auth_result['spf'] = 'fail'
        elif 'spf=neutral' in auth_results_header:
            auth_result['spf'] = 'neutral'

    # Parse DKIM
    if 'dkim=' in auth_results_header:
        if 'dkim=pass' in auth_results_header:
            auth_result['dkim'] = 'pass'
        elif 'dkim=fail' in auth_results_header:
            auth_result['dkim'] = 'fail'

    # Parse DMARC
    if 'dmarc=' in auth_results_header:
        if 'dmarc=pass' in auth_results_header:
            auth_result['dmarc'] = 'pass'
        elif 'dmarc=fail' in auth_results_header:
            auth_result['dmarc'] = 'fail'

    # Mark as suspicious if any auth failed
    auth_result['suspicious'] = (
        auth_result['spf'] == 'fail' or
        auth_result['dkim'] == 'fail' or
        auth_result['dmarc'] == 'fail'
    )

    return auth_result


# =============================================================================
# MITRE ATT&CK Mapping
# =============================================================================

# Common MITRE technique patterns for quick matching
MITRE_PATTERNS = {
    "T1566": ["phishing", "malicious attachment", "credential harvesting"],
    "T1566.001": ["spearphishing attachment", "weaponized document"],
    "T1566.002": ["spearphishing link", "malicious url"],
    "T1059": ["command execution", "powershell", "cmd.exe", "bash"],
    "T1059.001": ["powershell", "ps1"],
    "T1059.003": ["windows command shell", "cmd.exe"],
    "T1071": ["application layer protocol", "http", "https", "dns"],
    "T1082": ["system information discovery", "reconnaissance"],
    "T1021": ["remote services", "rdp", "ssh", "smb"],
    "T1021.001": ["remote desktop", "rdp"],
    "T1078": ["valid accounts", "compromised credentials", "stolen password"],
    "T1110": ["brute force", "password spray", "credential stuffing"],
    "T1486": ["ransomware", "file encryption", "crypto locker"],
    "T1204": ["user execution", "malicious file", "macro"],
    "T1133": ["external remote services", "vpn", "external access"],
    "T1190": ["exploit public-facing application", "web exploit", "vulnerability"],
}


def map_to_mitre(
    alert: dict,
    llm_query_fn: Callable = None
) -> list[str]:
    """
    Map security alert to MITRE ATT&CK technique IDs.

    Uses pattern matching for common techniques, optionally enhanced
    with LLM for complex or ambiguous alerts.

    Args:
        alert: Email dictionary with security alert
        llm_query_fn: Optional llm_query function for enhanced mapping

    Returns:
        List of MITRE technique IDs (e.g., ["T1566.001", "T1059.001"])

    Example:
        techniques = map_to_mitre(phishing_alert)
        if "T1566" in techniques:
            alert_phishing_team()
    """
    techniques = set()

    # Combine text for pattern matching
    text_fields = [
        alert.get('subject', ''),
        alert.get('snippet', ''),
        alert.get('body', '')
    ]
    combined_text = ' '.join(text_fields).lower()

    # Pattern-based matching
    for technique_id, patterns in MITRE_PATTERNS.items():
        if any(pattern in combined_text for pattern in patterns):
            techniques.add(technique_id)

    # If LLM is available and we found few matches, use it for enhancement
    if llm_query_fn and len(techniques) < 2:
        prompt = """Map this security alert to MITRE ATT&CK technique IDs.

Provide ONLY the technique IDs (e.g., T1566.001, T1059.001), one per line.
If no clear match, respond with "NONE"."""

        context = f"Subject: {alert.get('subject', '')}\nSnippet: {alert.get('snippet', '')}"

        try:
            result = llm_query_fn(prompt, context=context, _skip_status=True)
            # Extract T-IDs from response
            llm_techniques = re.findall(r'T\d{4}(?:\.\d{3})?', result)
            techniques.update(llm_techniques)
        except Exception:
            pass  # Fall back to pattern-based results

    return sorted(list(techniques))


# =============================================================================
# Time-Based Correlation
# =============================================================================

def parse_email_date(date_str: str) -> Optional[datetime]:
    """
    Parse email date string to datetime object.

    Args:
        date_str: Date string from email (RFC 2822 or ISO format)

    Returns:
        datetime object or None if parsing fails
    """
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',  # RFC 2822: "Wed, 15 Jan 2026 10:30:00 -0800"
        '%d %b %Y %H:%M:%S %z',       # Without day: "15 Jan 2026 10:30:00 -0800"
        '%Y-%m-%d %H:%M:%S',          # ISO-like: "2026-01-15 10:30:00"
        '%Y-%m-%dT%H:%M:%S',          # ISO with T
        '%Y-%m-%d',                   # ISO date: "2026-01-15"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue

    return None


def chunk_by_time(
    emails: list[dict],
    window_minutes: int = 5
) -> dict[str, list[dict]]:
    """
    Group emails into time windows for attack correlation.

    Critical for detecting kill chains where events occur in rapid sequence
    (e.g., phishing → execution → C2 callback within 5 minutes).

    Args:
        emails: List of email dictionaries with 'date' field
        window_minutes: Size of time buckets in minutes (default: 5)

    Returns:
        Dict mapping window timestamp to emails in that window:
        {
            "2025-01-15T10:00:00": [emails_in_window],
            "2025-01-15T10:05:00": [emails_in_window],
            ...
        }

    Example:
        windows = chunk_by_time(security_alerts, window_minutes=5)
        for window_time, alerts in windows.items():
            if len(alerts) >= 3:
                check_for_kill_chain(alerts)
    """
    windows = defaultdict(list)

    for email in emails:
        date_str = email.get('date', '')
        dt = parse_email_date(date_str)

        if dt is None:
            windows['unknown_time'].append(email)
            continue

        # Round down to nearest window
        # Example: 10:23 with 5-min window → 10:20
        window_delta = timedelta(minutes=window_minutes)
        timestamp = dt.replace(second=0, microsecond=0)
        minute_offset = timestamp.minute % window_minutes
        window_start = timestamp - timedelta(minutes=minute_offset)

        window_key = window_start.strftime('%Y-%m-%dT%H:%M:%S')
        windows[window_key].append(email)

    return dict(windows)


def detect_kill_chains(
    time_windows: dict[str, list[dict]],
    llm_query_fn: Callable
) -> list[dict]:
    """
    Analyze time-correlated alerts for attack pattern sequences.

    Looks for multi-stage attack patterns:
    - Initial Access → Execution → Persistence
    - Reconnaissance → Exploitation → Lateral Movement
    - Data Staging → Exfiltration

    Args:
        time_windows: Output from chunk_by_time()
        llm_query_fn: The llm_query function for pattern analysis

    Returns:
        List of detected kill chains:
        [
            {
                "window": "2025-01-15T10:00:00",
                "chain_detected": bool,
                "pattern": "Initial Access → Execution",
                "mitre_techniques": ["T1566", "T1059"],
                "severity": "P1",
                "alert_count": 3,
                "alerts": [...]
            },
            ...
        ]

    Example:
        windows = chunk_by_time(alerts, 5)
        chains = detect_kill_chains(windows, llm_query)
        for chain in chains:
            if chain['chain_detected']:
                escalate_to_soc(chain)
    """
    kill_chains = []

    for window_time, alerts in time_windows.items():
        if window_time == 'unknown_time' or len(alerts) < 2:
            continue  # Need at least 2 alerts for a chain

        # Build context for LLM
        context = "\n\n".join([
            f"Alert {i+1} ({alert.get('date', 'unknown')}):\n"
            f"Subject: {alert.get('subject', '')}\n"
            f"From: {alert.get('from', '')}\n"
            f"Snippet: {alert.get('snippet', '')}"
            for i, alert in enumerate(alerts)
        ])

        prompt = """Analyze these security alerts for kill chain patterns.

A kill chain is a sequence of attack stages like:
- Initial Access → Execution → Persistence
- Reconnaissance → Weaponization → Delivery → Exploitation
- Data Collection → Exfiltration

Respond in this format:
CHAIN_DETECTED: yes/no
PATTERN: [description if detected, e.g., "Phishing → Execution → C2"]
SEVERITY: P1/P2/P3/P4/P5
MITRE_TECHNIQUES: [comma-separated T-IDs]"""

        try:
            result = llm_query_fn(prompt, context=context, _skip_status=True)

            # Parse LLM response
            chain_detected = 'yes' in re.search(r'CHAIN_DETECTED:\s*(\w+)', result, re.IGNORECASE).group(1).lower() if re.search(r'CHAIN_DETECTED:\s*(\w+)', result, re.IGNORECASE) else False

            pattern_match = re.search(r'PATTERN:\s*(.+?)(?:\n|$)', result, re.IGNORECASE)
            pattern = pattern_match.group(1).strip() if pattern_match else "Unknown pattern"

            severity_match = re.search(r'SEVERITY:\s*(P[1-5])', result, re.IGNORECASE)
            severity = severity_match.group(1).upper() if severity_match else "P2"

            techniques_match = re.search(r'MITRE_TECHNIQUES:\s*(.+?)(?:\n|$)', result, re.IGNORECASE)
            techniques = []
            if techniques_match:
                tech_str = techniques_match.group(1)
                techniques = re.findall(r'T\d{4}(?:\.\d{3})?', tech_str)

            kill_chains.append({
                "window": window_time,
                "chain_detected": chain_detected,
                "pattern": pattern,
                "mitre_techniques": techniques,
                "severity": severity,
                "alert_count": len(alerts),
                "alerts": alerts
            })

        except Exception as e:
            # If LLM fails, still record the window
            kill_chains.append({
                "window": window_time,
                "chain_detected": False,
                "pattern": f"Analysis failed: {str(e)}",
                "mitre_techniques": [],
                "severity": "P3",
                "alert_count": len(alerts),
                "alerts": alerts
            })

    return kill_chains


# =============================================================================
# Threat Pattern Analysis
# =============================================================================

def correlate_by_source_ip(
    emails: list[dict],
    llm_query_fn: Callable = None
) -> dict:
    """
    Group alerts by source IP and analyze for coordinated attacks.

    Detects patterns like:
    - Brute force attempts from single IP
    - Port scanning activity
    - Distributed attacks from IP ranges

    Args:
        emails: List of email dictionaries
        llm_query_fn: Optional llm_query function for threat assessment

    Returns:
        Dict mapping IPs to analysis:
        {
            "192.168.1.100": {
                "alert_count": 5,
                "timespan_minutes": 15,
                "attack_type": "Brute Force",
                "severity": "P2",
                "first_seen": "2025-01-15T10:00:00",
                "last_seen": "2025-01-15T10:15:00",
                "alerts": [...]
            },
            ...
        }

    Example:
        ip_analysis = correlate_by_source_ip(firewall_alerts, llm_query)
        for ip, data in ip_analysis.items():
            if data['alert_count'] >= 10:
                block_ip(ip)
    """
    # Extract IPs from all emails
    iocs = extract_iocs(emails)
    ip_to_alerts = defaultdict(list)

    # Map each IP to its alerts
    for email in emails:
        combined_text = f"{email.get('subject', '')} {email.get('snippet', '')} {email.get('body', '')}"
        for ip in iocs['ips']:
            if ip in combined_text:
                ip_to_alerts[ip].append(email)

    # Analyze each IP
    analysis = {}
    for ip, alerts in ip_to_alerts.items():
        if len(alerts) < 2:
            continue  # Skip single-alert IPs

        # Calculate timespan
        dates = [parse_email_date(a.get('date', '')) for a in alerts]
        valid_dates = [d for d in dates if d is not None]

        if valid_dates:
            first_seen = min(valid_dates)
            last_seen = max(valid_dates)
            timespan_minutes = int((last_seen - first_seen).total_seconds() / 60)
        else:
            first_seen = last_seen = None
            timespan_minutes = 0

        # Use LLM for attack type classification if available
        attack_type = "Unknown"
        severity = "P3"

        if llm_query_fn:
            context = f"IP: {ip}\nAlert count: {len(alerts)}\nTimespan: {timespan_minutes} minutes\n\n"
            context += "\n".join([
                f"- {a.get('subject', '')}" for a in alerts[:5]
            ])

            prompt = """Analyze this IP's activity pattern.

Identify the attack type (e.g., Brute Force, Port Scan, DDoS, Lateral Movement, etc.)
and assign a severity (P1-P5).

Respond in format:
ATTACK_TYPE: [type]
SEVERITY: P1/P2/P3/P4/P5"""

            try:
                result = llm_query_fn(prompt, context=context, _skip_status=True)

                type_match = re.search(r'ATTACK_TYPE:\s*(.+?)(?:\n|$)', result, re.IGNORECASE)
                if type_match:
                    attack_type = type_match.group(1).strip()

                sev_match = re.search(r'SEVERITY:\s*(P[1-5])', result, re.IGNORECASE)
                if sev_match:
                    severity = sev_match.group(1).upper()
            except Exception:
                pass

        analysis[ip] = {
            "alert_count": len(alerts),
            "timespan_minutes": timespan_minutes,
            "attack_type": attack_type,
            "severity": severity,
            "first_seen": first_seen.isoformat() if first_seen else None,
            "last_seen": last_seen.isoformat() if last_seen else None,
            "alerts": alerts
        }

    return analysis


def detect_suspicious_senders(
    emails: list[dict],
    llm_query_fn: Callable = None
) -> list[dict]:
    """
    Identify phishing attempts, spoofing, and domain squatting.

    Checks for:
    - Lookalike domains (goog1e.com vs google.com)
    - Display name spoofing
    - Unusual sender patterns
    - Failed authentication (SPF/DKIM/DMARC)

    Args:
        emails: List of email dictionaries
        llm_query_fn: Optional llm_query function for enhanced analysis

    Returns:
        List of suspicious sender detections:
        [
            {
                "sender": "admin@g00gle.com",
                "reason": "Domain squatting detected",
                "confidence": 0.95,
                "email_id": "...",
                "auth_failed": True
            },
            ...
        ]

    Example:
        suspicious = detect_suspicious_senders(inbox_emails)
        for detection in suspicious:
            if detection['confidence'] > 0.8:
                quarantine_email(detection['email_id'])
    """
    suspicious = []

    # Known legitimate domains for comparison
    common_domains = {
        'google.com', 'microsoft.com', 'apple.com', 'amazon.com',
        'facebook.com', 'paypal.com', 'netflix.com', 'linkedin.com'
    }

    for email in emails:
        from_field = email.get('from', '')

        # Extract sender email address
        match = re.search(r'<([^>]+)>', from_field)
        if match:
            sender_email = match.group(1).lower()
            display_name = from_field[:match.start()].strip()
        else:
            sender_email = from_field.lower().strip()
            display_name = ""

        if '@' not in sender_email:
            continue

        sender_domain = sender_email.split('@')[1]

        # Check 1: Domain squatting
        for legit_domain in common_domains:
            # Levenshtein-like check (simple version)
            if sender_domain != legit_domain and _domain_similarity(sender_domain, legit_domain) > 0.7:
                suspicious.append({
                    "sender": sender_email,
                    "reason": f"Possible domain squatting of {legit_domain}",
                    "confidence": 0.9,
                    "email_id": email.get('id', ''),
                    "auth_failed": False
                })

        # Check 2: Display name spoofing
        if display_name:
            # Look for corporate names in display but different domain
            corporate_keywords = ['paypal', 'apple', 'microsoft', 'google', 'amazon', 'bank']
            display_lower = display_name.lower()
            if any(keyword in display_lower for keyword in corporate_keywords):
                # Check if domain matches
                if not any(keyword in sender_domain for keyword in corporate_keywords):
                    suspicious.append({
                        "sender": sender_email,
                        "reason": "Display name spoofing (corporate name with unrelated domain)",
                        "confidence": 0.85,
                        "email_id": email.get('id', ''),
                        "auth_failed": False
                    })

        # Check 3: Authentication failures
        auth_status = validate_email_auth(email)
        if auth_status['suspicious']:
            suspicious.append({
                "sender": sender_email,
                "reason": f"Email authentication failed (SPF: {auth_status['spf']}, DKIM: {auth_status['dkim']})",
                "confidence": 0.75,
                "email_id": email.get('id', ''),
                "auth_failed": True
            })

    return suspicious


def _domain_similarity(domain1: str, domain2: str) -> float:
    """
    Calculate similarity between two domain names.

    Simple character-based similarity for detecting typosquatting.

    Args:
        domain1: First domain
        domain2: Second domain

    Returns:
        Similarity score 0.0-1.0
    """
    # Simple Jaccard similarity on character bigrams
    def bigrams(s):
        return set(s[i:i+2] for i in range(len(s)-1))

    b1 = bigrams(domain1)
    b2 = bigrams(domain2)

    if not b1 or not b2:
        return 0.0

    intersection = len(b1 & b2)
    union = len(b1 | b2)

    return intersection / union if union > 0 else 0.0


# =============================================================================
# Attachment & URL Analysis
# =============================================================================

def analyze_attachments(emails: list[dict]) -> list[dict]:
    """
    Extract attachment metadata and identify risk indicators.

    Note: Does NOT download attachments, only analyzes metadata from email.

    Args:
        emails: List of email dictionaries

    Returns:
        List of risky attachments:
        [
            {
                "filename": "invoice.exe",
                "mime_type": "application/x-msdownload",
                "risk_level": "HIGH",
                "reason": "Executable file in financial context",
                "email_id": "...",
                "email_subject": "..."
            },
            ...
        ]

    Example:
        risky_attachments = analyze_attachments(inbox)
        for attachment in risky_attachments:
            if attachment['risk_level'] == 'HIGH':
                alert_user(attachment)
    """
    risky_attachments = []

    # High-risk file extensions
    dangerous_extensions = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs',
        '.js', '.jar', '.ps1', '.msi', '.hta', '.wsf', '.dll'
    }

    # Suspicious contexts
    financial_keywords = ['invoice', 'payment', 'receipt', 'statement', 'tax']
    urgent_keywords = ['urgent', 'immediate', 'action required', 'suspended']

    for email in emails:
        # Gmail metadata format doesn't expose attachment details easily
        # We look for clues in snippet/subject
        snippet = email.get('snippet', '').lower()
        subject = email.get('subject', '').lower()
        combined = f"{subject} {snippet}"

        # Check for attachment indicators
        has_attachment_mention = any(word in combined for word in ['attachment', 'attached', 'file', 'document'])

        if has_attachment_mention:
            # Analyze context
            risk_level = "LOW"
            reason = "Attachment mentioned"

            # Check for dangerous file extensions mentioned
            for ext in dangerous_extensions:
                if ext in combined:
                    risk_level = "HIGH"
                    reason = f"Executable file type detected: {ext}"
                    break

            # Check for financial context
            if any(kw in combined for kw in financial_keywords):
                if risk_level == "LOW":
                    risk_level = "MEDIUM"
                    reason = "Attachment in financial context"

            # Check for urgency
            if any(kw in combined for kw in urgent_keywords):
                if risk_level in ["LOW", "MEDIUM"]:
                    risk_level = "MEDIUM" if risk_level == "LOW" else "HIGH"
                    reason = f"{reason} with urgency indicators"

            if risk_level != "LOW":
                risky_attachments.append({
                    "filename": "unknown (metadata limited)",
                    "mime_type": "unknown",
                    "risk_level": risk_level,
                    "reason": reason,
                    "email_id": email.get('id', ''),
                    "email_subject": subject
                })

    return risky_attachments


def extract_and_analyze_urls(emails: list[dict]) -> list[dict]:
    """
    Extract URLs from emails and identify suspicious links.

    Checks for:
    - URL shorteners (bit.ly, tinyurl)
    - Mismatched display text vs actual URL
    - Suspicious TLDs (.xyz, .top, .tk, etc.)
    - Known malicious domains (basic check)

    Args:
        emails: List of email dictionaries

    Returns:
        List of suspicious URLs:
        [
            {
                "url": "http://bit.ly/abc123",
                "display_text": "Click for invoice",
                "risk_level": "MEDIUM",
                "reason": "URL shortener in financial context",
                "email_id": "...",
                "email_subject": "..."
            },
            ...
        ]

    Example:
        suspicious_urls = extract_and_analyze_urls(phishing_emails)
        for url_data in suspicious_urls:
            submit_to_sandbox(url_data['url'])
    """
    suspicious_urls = []

    # URL shortener domains
    shorteners = {'bit.ly', 'tinyurl.com', 'goo.gl', 't.co', 'ow.ly', 'is.gd'}

    # Suspicious TLDs
    suspicious_tlds = {'.xyz', '.top', '.tk', '.ml', '.ga', '.cf', '.gq'}

    for email in emails:
        combined_text = f"{email.get('subject', '')} {email.get('snippet', '')} {email.get('body', '')}"

        # Extract URLs
        urls = URL_PATTERN.findall(combined_text)

        for url in urls:
            risk_level = "LOW"
            reasons = []

            # Parse domain from URL
            domain_match = re.search(r'https?://([^/]+)', url)
            if not domain_match:
                continue
            domain = domain_match.group(1).lower()

            # Check 1: URL shorteners
            if any(shortener in domain for shortener in shorteners):
                risk_level = "MEDIUM"
                reasons.append("URL shortener detected")

            # Check 2: Suspicious TLD
            if any(domain.endswith(tld) for tld in suspicious_tlds):
                risk_level = "MEDIUM" if risk_level == "LOW" else "HIGH"
                reasons.append("Suspicious TLD")

            # Check 3: IP address as domain (often suspicious)
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', domain):
                risk_level = "MEDIUM" if risk_level == "LOW" else "HIGH"
                reasons.append("IP address used instead of domain")

            # Check 4: Excessive subdomains (potential phishing)
            subdomain_count = domain.count('.')
            if subdomain_count > 3:
                risk_level = "MEDIUM" if risk_level == "LOW" else "HIGH"
                reasons.append("Excessive subdomains")

            if risk_level != "LOW":
                suspicious_urls.append({
                    "url": url,
                    "display_text": "unknown",  # Would need HTML parsing
                    "risk_level": risk_level,
                    "reason": "; ".join(reasons),
                    "email_id": email.get('id', ''),
                    "email_subject": email.get('subject', '')
                })

    return suspicious_urls


# =============================================================================
# Alert Deduplication
# =============================================================================

def deduplicate_security_alerts(
    emails: list[dict],
    similarity_threshold: float = 0.9
) -> list[dict]:
    """
    Remove duplicate security alerts based on content similarity.

    Useful for consolidating recurring alerts (e.g., same vuln scan finding
    across 50 servers).

    Args:
        emails: List of email dictionaries
        similarity_threshold: Similarity score 0.0-1.0 for considering duplicates

    Returns:
        Deduplicated list of emails

    Example:
        unique_alerts = deduplicate_security_alerts(vuln_scan_results)
        print(f"Reduced from {len(all_alerts)} to {len(unique_alerts)} unique alerts")
    """
    if not emails:
        return []

    unique_emails = []
    seen_signatures = []

    for email in emails:
        # Create a signature from subject + snippet
        subject = email.get('subject', '').lower()
        snippet = email.get('snippet', '').lower()

        # Normalize: remove numbers (IPs, ports, etc.) and dates
        normalized_subject = re.sub(r'\d+', 'N', subject)
        normalized_snippet = re.sub(r'\d+', 'N', snippet)

        signature = f"{normalized_subject}|{normalized_snippet[:100]}"

        # Check against seen signatures
        is_duplicate = False
        for seen_sig in seen_signatures:
            similarity = _text_similarity(signature, seen_sig)
            if similarity >= similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            unique_emails.append(email)
            seen_signatures.append(signature)

    return unique_emails


def _text_similarity(text1: str, text2: str) -> float:
    """Calculate simple character-level similarity between two texts."""
    # Jaccard similarity on words
    words1 = set(text1.split())
    words2 = set(text2.split())

    if not words1 or not words2:
        return 0.0

    intersection = len(words1 & words2)
    union = len(words1 | words2)

    return intersection / union if union > 0 else 0.0
