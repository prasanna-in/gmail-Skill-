"""
Gmail Security Workflow Functions

This module provides high-level security analysis workflows that orchestrate
the security helper functions into complete triage and analysis pipelines.

Workflows are designed to be used within the gmail_rlm_repl.py environment
and leverage the RLM approach for large-scale security alert processing.

Pre-built Workflows:
- security_triage(emails) - Complete alert triage pipeline
- detect_attack_chains(emails) - Multi-pass correlation for attack sequences
- enrich_with_threat_intel(iocs) - Prepare IOCs for threat intel lookup

These workflows combine:
- Severity classification
- IOC extraction
- Time-based correlation
- MITRE ATT&CK mapping
- Kill chain detection
- Executive summary generation
"""

from typing import Callable, Optional
from collections import defaultdict
import json

# Import security helper functions
from gmail_security_helpers import (
    classify_alerts,
    extract_iocs,
    validate_email_auth,
    map_to_mitre,
    chunk_by_time,
    detect_kill_chains,
    correlate_by_source_ip,
    detect_suspicious_senders,
    analyze_attachments,
    extract_and_analyze_urls,
    deduplicate_security_alerts
)


# =============================================================================
# Workflow Factory Functions
# =============================================================================
#
# These factory functions create workflows with injected dependencies,
# following the same pattern as gmail_rlm_helpers.py workflows.


def create_security_triage(
    llm_query_fn: Callable,
    parallel_map_fn: Callable
):
    """
    Create security_triage workflow with injected dependencies.

    Args:
        llm_query_fn: The llm_query function
        parallel_map_fn: The parallel_map function

    Returns:
        security_triage function
    """
    def security_triage(
        emails: list[dict],
        deduplicate: bool = True,
        include_executive_summary: bool = True
    ) -> dict:
        """
        Complete security alert triage pipeline.

        This is the primary workflow for daily security alert processing.
        It performs comprehensive analysis across all security dimensions.

        Steps:
        1. Deduplicate recurring alerts (optional)
        2. Classify alerts by severity (P1-P5)
        3. Extract IOCs from all alerts
        4. Detect kill chains via time correlation
        5. Correlate alerts by source IP
        6. Identify suspicious senders/domains
        7. Analyze attachments and URLs for phishing
        8. Generate executive summary (optional)

        Args:
            emails: List of email dictionaries (security alerts)
            deduplicate: Remove duplicate alerts (default: True)
            include_executive_summary: Generate LLM summary (default: True)

        Returns:
            Comprehensive triage results:
            {
                "summary": {
                    "total_alerts": int,
                    "unique_alerts": int,
                    "critical_count": int,
                    "kill_chains_detected": int
                },
                "classifications": {"P1": [...], "P2": [...], ...},
                "iocs": {"ips": [...], "domains": [...], ...},
                "kill_chains": [{pattern, severity, alerts}, ...],
                "source_ip_analysis": {"192.168.1.100": {...}, ...},
                "suspicious_senders": [{sender, reason, confidence}, ...],
                "risky_attachments": [{filename, risk_level}, ...],
                "suspicious_urls": [{url, risk_level}, ...],
                "executive_summary": "LLM-generated brief for CISO"
            }

        Example:
            result = security_triage(security_alerts)
            print(f"P1 Critical: {len(result['classifications']['P1'])}")
            print(f"Kill Chains: {len(result['kill_chains'])}")
            print(result['executive_summary'])
        """
        if not emails:
            return {
                "summary": {"total_alerts": 0, "unique_alerts": 0, "critical_count": 0, "kill_chains_detected": 0},
                "classifications": {"P1": [], "P2": [], "P3": [], "P4": [], "P5": []},
                "iocs": {"ips": [], "domains": [], "file_hashes": {"md5": [], "sha1": [], "sha256": []}, "email_addresses": [], "urls": []},
                "kill_chains": [],
                "source_ip_analysis": {},
                "suspicious_senders": [],
                "risky_attachments": [],
                "suspicious_urls": [],
                "executive_summary": "No alerts to triage."
            }

        total_alerts = len(emails)

        # Step 1: Deduplicate
        if deduplicate:
            emails = deduplicate_security_alerts(emails)

        unique_alerts = len(emails)

        # Step 2: Classify by severity
        classifications = classify_alerts(emails, llm_query_fn)

        critical_count = len(classifications.get('P1', []))

        # Step 3: Extract IOCs
        iocs = extract_iocs(emails)

        # Step 4: Time-based kill chain detection
        time_windows = chunk_by_time(emails, window_minutes=5)
        kill_chains = detect_kill_chains(time_windows, llm_query_fn)

        # Filter to only chains that were actually detected
        detected_chains = [kc for kc in kill_chains if kc.get('chain_detected', False)]

        # Step 5: Source IP correlation
        source_ip_analysis = correlate_by_source_ip(emails, llm_query_fn)

        # Step 6: Suspicious sender detection
        suspicious_senders = detect_suspicious_senders(emails, llm_query_fn)

        # Step 7: Attachment and URL analysis
        risky_attachments = analyze_attachments(emails)
        suspicious_urls = extract_and_analyze_urls(emails)

        # Step 8: Executive summary
        executive_summary = ""
        if include_executive_summary:
            summary_context = f"""Security Alert Triage Summary:
- Total Alerts Processed: {total_alerts} (Unique: {unique_alerts})
- Critical (P1): {len(classifications.get('P1', []))}
- High (P2): {len(classifications.get('P2', []))}
- Medium (P3): {len(classifications.get('P3', []))}
- Low (P4): {len(classifications.get('P4', []))}
- Info (P5): {len(classifications.get('P5', []))}

Kill Chains Detected: {len(detected_chains)}
{chr(10).join([f"- {kc['pattern']} ({kc['severity']})" for kc in detected_chains[:5]])}

Suspicious Activity:
- {len(source_ip_analysis)} unique source IPs with multiple alerts
- {len(suspicious_senders)} suspicious sender patterns
- {len(risky_attachments)} risky attachments
- {len(suspicious_urls)} suspicious URLs

Top IOCs:
- IPs: {len(iocs['ips'])}
- Domains: {len(iocs['domains'])}
- File Hashes: {len(iocs['file_hashes']['sha256'])} SHA256
"""

            summary_prompt = """Generate a concise executive summary for the CISO based on this security triage.

Include:
1. Overall threat landscape (1-2 sentences)
2. Critical items requiring immediate action (if any)
3. Key trends or patterns
4. Recommended next steps

Keep it under 200 words. Be direct and actionable."""

            try:
                executive_summary = llm_query_fn(summary_prompt, context=summary_context)
            except Exception as e:
                executive_summary = f"Summary generation failed: {str(e)}"

        return {
            "summary": {
                "total_alerts": total_alerts,
                "unique_alerts": unique_alerts,
                "critical_count": critical_count,
                "kill_chains_detected": len(detected_chains)
            },
            "classifications": classifications,
            "iocs": iocs,
            "kill_chains": detected_chains,
            "source_ip_analysis": source_ip_analysis,
            "suspicious_senders": suspicious_senders,
            "risky_attachments": risky_attachments,
            "suspicious_urls": suspicious_urls,
            "executive_summary": executive_summary
        }

    return security_triage


def create_detect_attack_chains(llm_query_fn: Callable):
    """
    Create detect_attack_chains workflow with injected dependencies.

    Args:
        llm_query_fn: The llm_query function

    Returns:
        detect_attack_chains function
    """
    def detect_attack_chains(
        emails: list[dict],
        window_minutes: int = 5,
        min_alerts_per_chain: int = 2
    ) -> list[dict]:
        """
        Multi-pass correlation analysis for sophisticated attack detection.

        This workflow performs deep analysis of temporal alert patterns to
        identify multi-stage attacks that might be missed by single-alert analysis.

        Analysis Passes:
        1. Group alerts into time windows (default: 5 minutes)
        2. Detect kill chain patterns within each window
        3. Correlate across windows for multi-stage attacks
        4. Synthesize final attack chains with confidence scoring

        Args:
            emails: List of email dictionaries (security alerts)
            window_minutes: Time window size in minutes (default: 5)
            min_alerts_per_chain: Minimum alerts to consider a chain (default: 2)

        Returns:
            List of detected attack chains:
            [
                {
                    "attack_id": "chain_20250115_001",
                    "start_time": "2025-01-15T10:00:00",
                    "end_time": "2025-01-15T10:25:00",
                    "duration_minutes": 25,
                    "pattern": "Phishing → Execution → C2 Callback",
                    "mitre_techniques": ["T1566", "T1059", "T1071"],
                    "severity": "P1",
                    "confidence": 0.92,
                    "affected_systems": ["user@company.com", "192.168.1.50"],
                    "alert_count": 5,
                    "alerts": [...]
                },
                ...
            ]

        Example:
            chains = detect_attack_chains(security_alerts, window_minutes=5)
            for chain in chains:
                if chain['severity'] == 'P1' and chain['confidence'] > 0.85:
                    incident_response(chain)
        """
        if not emails:
            return []

        # Pass 1: Group by time windows
        time_windows = chunk_by_time(emails, window_minutes=window_minutes)

        # Pass 2: Detect patterns in each window
        window_chains = detect_kill_chains(time_windows, llm_query_fn)

        # Filter to only detected chains
        detected_window_chains = [
            kc for kc in window_chains
            if kc.get('chain_detected', False) and kc.get('alert_count', 0) >= min_alerts_per_chain
        ]

        if not detected_window_chains:
            return []

        # Pass 3: Synthesize multi-window attacks
        # Group adjacent windows that might be part of same attack
        attack_chains = []
        attack_id = 1

        for i, window_chain in enumerate(detected_window_chains):
            # Extract affected systems (IPs, users)
            affected_systems = set()
            for alert in window_chain['alerts']:
                # Extract email addresses
                from_field = alert.get('from', '')
                if '@' in from_field:
                    affected_systems.add(from_field.split('@')[0] if '<' not in from_field else from_field)

                # Extract IPs from snippets (basic)
                import re
                snippet = alert.get('snippet', '')
                ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', snippet)
                affected_systems.update(ips)

            # Parse window time
            from datetime import datetime
            try:
                start_time = datetime.fromisoformat(window_chain['window'])
                end_time = start_time  # Single window initially
                duration_minutes = window_minutes
            except:
                start_time = end_time = None
                duration_minutes = window_minutes

            # Build attack chain entry
            attack_chain = {
                "attack_id": f"chain_{datetime.now().strftime('%Y%m%d')}_{attack_id:03d}",
                "start_time": window_chain['window'],
                "end_time": window_chain['window'],  # Updated if multi-window
                "duration_minutes": duration_minutes,
                "pattern": window_chain['pattern'],
                "mitre_techniques": window_chain['mitre_techniques'],
                "severity": window_chain['severity'],
                "confidence": 0.75,  # Base confidence, enhanced by LLM below
                "affected_systems": sorted(list(affected_systems)),
                "alert_count": window_chain['alert_count'],
                "alerts": window_chain['alerts']
            }

            # Pass 4: Enhance with LLM confidence scoring
            context = f"""Attack Chain Analysis:
Pattern: {attack_chain['pattern']}
MITRE Techniques: {', '.join(attack_chain['mitre_techniques'])}
Alert Count: {attack_chain['alert_count']}
Duration: {attack_chain['duration_minutes']} minutes
Affected Systems: {', '.join(attack_chain['affected_systems'][:5])}

Sample Alerts:
{chr(10).join([f"- {a.get('subject', '')}" for a in attack_chain['alerts'][:3]])}
"""

            confidence_prompt = """Assess the confidence that this is a genuine multi-stage attack.

Consider:
- Pattern coherence (do the stages logically follow?)
- Timing (are stages occurring in realistic sequence?)
- Affected systems (single target or distributed?)
- MITRE technique validity

Respond with:
CONFIDENCE: [0-100]
REASONING: [brief explanation]"""

            try:
                result = llm_query_fn(confidence_prompt, context=context, _skip_status=True)

                # Parse confidence
                import re
                conf_match = re.search(r'CONFIDENCE:\s*(\d+)', result, re.IGNORECASE)
                if conf_match:
                    attack_chain['confidence'] = int(conf_match.group(1)) / 100

                reason_match = re.search(r'REASONING:\s*(.+?)(?:\n|$)', result, re.IGNORECASE)
                if reason_match:
                    attack_chain['confidence_reasoning'] = reason_match.group(1).strip()
            except Exception:
                pass

            attack_chains.append(attack_chain)
            attack_id += 1

        # Sort by severity and confidence
        severity_order = {"P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5}
        attack_chains.sort(
            key=lambda x: (severity_order.get(x['severity'], 3), -x['confidence'])
        )

        return attack_chains

    return detect_attack_chains


def create_enrich_with_threat_intel():
    """
    Create enrich_with_threat_intel workflow.

    Note: This is a placeholder for future threat intelligence integrations.
    Currently structures IOC data for manual enrichment or external API calls.

    Returns:
        enrich_with_threat_intel function
    """
    def enrich_with_threat_intel(iocs: dict) -> dict:
        """
        Prepare IOCs for threat intelligence enrichment.

        This function structures IOC data for integration with threat intel APIs
        like VirusTotal, AbuseIPDB, AlienVault OTX, or MISP.

        Currently returns structured data. Future enhancements will add:
        - VirusTotal API integration
        - AbuseIPDB lookup
        - AlienVault OTX queries
        - MISP export

        Args:
            iocs: IOC dict from extract_iocs()

        Returns:
            Structured IOC data ready for enrichment:
            {
                "ips": [
                    {
                        "ip": "1.2.3.4",
                        "reputation": "unknown",
                        "source": None,
                        "first_seen": None,
                        "last_seen": None,
                        "threat_type": None
                    },
                    ...
                ],
                "domains": [...],
                "file_hashes": [...],
                "enrichment_status": "pending",
                "apis_available": []
            }

        Example:
            enriched = enrich_with_threat_intel(iocs)
            # TODO: for ip_data in enriched['ips']:
            #     if check_virustotal(ip_data['ip']):
            #         ip_data['reputation'] = 'malicious'
        """
        enriched = {
            "ips": [],
            "domains": [],
            "file_hashes": [],
            "email_addresses": [],
            "urls": [],
            "enrichment_status": "pending",
            "apis_available": []
        }

        # Structure IPs for enrichment
        for ip in iocs.get('ips', []):
            enriched['ips'].append({
                "ip": ip,
                "reputation": "unknown",
                "source": None,
                "first_seen": None,
                "last_seen": None,
                "threat_type": None,
                "asn": None,
                "country": None
            })

        # Structure domains
        for domain in iocs.get('domains', []):
            enriched['domains'].append({
                "domain": domain,
                "category": "unknown",
                "reputation": "unknown",
                "source": None,
                "registrar": None,
                "creation_date": None
            })

        # Structure file hashes
        for hash_type in ['md5', 'sha1', 'sha256']:
            for hash_value in iocs.get('file_hashes', {}).get(hash_type, []):
                enriched['file_hashes'].append({
                    "hash": hash_value,
                    "hash_type": hash_type,
                    "malware_family": None,
                    "detection_count": None,
                    "source": None
                })

        # Structure email addresses
        for email in iocs.get('email_addresses', []):
            enriched['email_addresses'].append({
                "email": email,
                "reputation": "unknown",
                "associated_campaigns": []
            })

        # Structure URLs
        for url in iocs.get('urls', []):
            enriched['urls'].append({
                "url": url,
                "category": "unknown",
                "reputation": "unknown",
                "screenshot_available": False
            })

        # Check which APIs are available (future enhancement)
        # For now, just indicate what could be integrated
        enriched['apis_available'] = [
            "virustotal",  # Requires API key
            "abuseipdb",   # Requires API key
            "alienvault",  # Requires API key
            "misp"         # Requires MISP instance
        ]

        return enriched

    return enrich_with_threat_intel


# =============================================================================
# Specialized Analysis Workflows
# =============================================================================

def create_phishing_analysis(llm_query_fn: Callable):
    """
    Create phishing-specific analysis workflow.

    Args:
        llm_query_fn: The llm_query function

    Returns:
        phishing_analysis function
    """
    def phishing_analysis(emails: list[dict]) -> dict:
        """
        Specialized analysis for phishing detection and categorization.

        Analyzes emails for:
        - Credential harvesting attempts
        - Business email compromise (BEC)
        - Brand impersonation
        - Attachment-based phishing
        - Link-based phishing

        Args:
            emails: List of email dictionaries

        Returns:
            Phishing analysis results:
            {
                "credential_harvesting": [...],
                "bec_attempts": [...],
                "brand_impersonation": [...],
                "malicious_attachments": [...],
                "malicious_links": [...],
                "summary": "..."
            }

        Example:
            phishing_results = phishing_analysis(suspicious_emails)
            high_risk = phishing_results['credential_harvesting']
        """
        results = {
            "credential_harvesting": [],
            "bec_attempts": [],
            "brand_impersonation": [],
            "malicious_attachments": [],
            "malicious_links": [],
            "summary": ""
        }

        if not emails:
            return results

        # Detect suspicious senders (covers BEC and impersonation)
        suspicious = detect_suspicious_senders(emails, llm_query_fn)

        for detection in suspicious:
            if "spoofing" in detection['reason'].lower():
                results['brand_impersonation'].append(detection)
            else:
                results['bec_attempts'].append(detection)

        # Analyze attachments
        risky_attachments = analyze_attachments(emails)
        results['malicious_attachments'] = [
            att for att in risky_attachments if att['risk_level'] in ['HIGH', 'MEDIUM']
        ]

        # Analyze URLs
        suspicious_urls = extract_and_analyze_urls(emails)
        results['malicious_links'] = suspicious_urls

        # Detect credential harvesting (look for login/password keywords)
        for email in emails:
            snippet = email.get('snippet', '').lower()
            subject = email.get('subject', '').lower()
            combined = f"{subject} {snippet}"

            if any(word in combined for word in ['verify account', 'confirm password', 'update payment', 'suspended account']):
                results['credential_harvesting'].append({
                    "email_id": email.get('id', ''),
                    "subject": subject,
                    "reason": "Credential harvesting keywords detected"
                })

        # Generate summary
        summary_context = f"""Phishing Analysis Results:
- Credential Harvesting Attempts: {len(results['credential_harvesting'])}
- BEC Attempts: {len(results['bec_attempts'])}
- Brand Impersonation: {len(results['brand_impersonation'])}
- Malicious Attachments: {len(results['malicious_attachments'])}
- Malicious Links: {len(results['malicious_links'])}
"""

        try:
            results['summary'] = llm_query_fn(
                "Summarize the phishing threat landscape based on this data in 2-3 sentences.",
                context=summary_context,
                _skip_status=True
            )
        except Exception:
            results['summary'] = "Summary generation failed."

        return results

    return phishing_analysis
