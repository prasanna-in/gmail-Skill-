"""
Gmail Security JSON Schemas

This module defines JSON schemas for structured security data output.
These schemas are used with llm_query_json() for validated, structured responses.

Schemas:
- SECURITY_ALERT_SCHEMA: Full security alert structure
- IOC_SCHEMA: Indicator of Compromise data
- KILL_CHAIN_SCHEMA: Attack chain/kill chain detection
- MITRE_MAPPING_SCHEMA: MITRE ATT&CK technique mapping
- PHISHING_ANALYSIS_SCHEMA: Phishing detection results
- THREAT_ASSESSMENT_SCHEMA: Threat level assessment
- IP_REPUTATION_SCHEMA: IP reputation data
- DOMAIN_REPUTATION_SCHEMA: Domain reputation data

Usage:
    from gmail_security_schemas import SECURITY_ALERT_SCHEMA

    result = llm_query_json(
        "Extract security alert details",
        context=email_text,
        schema=SECURITY_ALERT_SCHEMA
    )
"""


# =============================================================================
# Core Security Data Schemas
# =============================================================================

SECURITY_ALERT_SCHEMA = {
    "type": "object",
    "properties": {
        "alert_id": {
            "type": "string",
            "description": "Unique alert identifier"
        },
        "severity": {
            "enum": ["P1", "P2", "P3", "P4", "P5"],
            "description": "Alert priority level"
        },
        "source_tool": {
            "type": "string",
            "description": "Security tool that generated the alert (e.g., CrowdStrike, Splunk)"
        },
        "timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "When the alert was generated"
        },
        "alert_type": {
            "type": "string",
            "description": "Type of security event (e.g., Malware, Phishing, Brute Force)"
        },
        "affected_assets": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Systems, users, or resources affected"
        },
        "iocs": {
            "type": "object",
            "properties": {
                "ips": {
                    "type": "array",
                    "items": {"type": "string", "pattern": "^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$"}
                },
                "domains": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "file_hashes": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "urls": {
                    "type": "array",
                    "items": {"type": "string", "format": "uri"}
                }
            }
        },
        "mitre_techniques": {
            "type": "array",
            "items": {
                "type": "string",
                "pattern": "^T\\d{4}(\\.\\d{3})?$"
            },
            "description": "MITRE ATT&CK technique IDs"
        },
        "description": {
            "type": "string",
            "description": "Human-readable alert description"
        },
        "recommended_actions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Suggested response actions"
        }
    },
    "required": ["alert_id", "severity", "timestamp"]
}


IOC_SCHEMA = {
    "type": "object",
    "properties": {
        "ips": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ip": {"type": "string", "pattern": "^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$"},
                    "reputation": {"enum": ["malicious", "suspicious", "unknown", "benign"]},
                    "first_seen": {"type": "string", "format": "date-time"},
                    "last_seen": {"type": "string", "format": "date-time"},
                    "threat_type": {"type": "string"}
                },
                "required": ["ip"]
            }
        },
        "domains": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "reputation": {"enum": ["malicious", "suspicious", "unknown", "benign"]},
                    "category": {"type": "string"},
                    "registrar": {"type": "string"}
                },
                "required": ["domain"]
            }
        },
        "file_hashes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "hash": {"type": "string"},
                    "hash_type": {"enum": ["md5", "sha1", "sha256"]},
                    "malware_family": {"type": "string"},
                    "detection_count": {"type": "integer"}
                },
                "required": ["hash", "hash_type"]
            }
        },
        "email_addresses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "reputation": {"enum": ["malicious", "suspicious", "unknown", "benign"]},
                    "associated_campaigns": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["email"]
            }
        },
        "urls": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "format": "uri"},
                    "category": {"type": "string"},
                    "reputation": {"enum": ["malicious", "suspicious", "unknown", "benign"]}
                },
                "required": ["url"]
            }
        }
    },
    "required": ["ips", "domains", "file_hashes"]
}


KILL_CHAIN_SCHEMA = {
    "type": "object",
    "properties": {
        "chain_id": {
            "type": "string",
            "description": "Unique identifier for this kill chain"
        },
        "chain_detected": {
            "type": "boolean",
            "description": "Whether a kill chain pattern was detected"
        },
        "pattern": {
            "type": "string",
            "description": "Description of the attack pattern (e.g., 'Phishing → Execution → C2')"
        },
        "stages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "stage_name": {
                        "type": "string",
                        "description": "Kill chain stage (e.g., Initial Access, Execution)"
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time"
                    },
                    "alert_id": {"type": "string"},
                    "mitre_technique": {
                        "type": "string",
                        "pattern": "^T\\d{4}(\\.\\d{3})?$"
                    }
                },
                "required": ["stage_name"]
            },
            "minItems": 2,
            "description": "Sequence of attack stages in temporal order"
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence score for kill chain detection (0-1)"
        },
        "severity": {
            "enum": ["P1", "P2", "P3", "P4", "P5"],
            "description": "Overall severity of the attack chain"
        },
        "affected_systems": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Systems or users involved in the attack"
        },
        "start_time": {
            "type": "string",
            "format": "date-time",
            "description": "When the attack chain started"
        },
        "end_time": {
            "type": "string",
            "format": "date-time",
            "description": "When the attack chain ended"
        },
        "duration_minutes": {
            "type": "integer",
            "minimum": 0,
            "description": "Duration of the attack in minutes"
        }
    },
    "required": ["chain_detected", "pattern", "confidence", "severity"]
}


MITRE_MAPPING_SCHEMA = {
    "type": "object",
    "properties": {
        "techniques": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "technique_id": {
                        "type": "string",
                        "pattern": "^T\\d{4}(\\.\\d{3})?$",
                        "description": "MITRE ATT&CK technique ID"
                    },
                    "technique_name": {
                        "type": "string",
                        "description": "Human-readable technique name"
                    },
                    "tactic": {
                        "type": "string",
                        "description": "MITRE tactic (e.g., Initial Access, Execution)"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Confidence in this mapping (0-1)"
                    },
                    "evidence": {
                        "type": "string",
                        "description": "Evidence from alert supporting this technique"
                    }
                },
                "required": ["technique_id", "technique_name"]
            }
        },
        "primary_tactic": {
            "type": "string",
            "description": "Primary MITRE tactic for this alert"
        }
    },
    "required": ["techniques"]
}


PHISHING_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "is_phishing": {
            "type": "boolean",
            "description": "Whether this email is phishing"
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence score (0-1)"
        },
        "phishing_type": {
            "enum": [
                "credential_harvesting",
                "bec",
                "brand_impersonation",
                "malware_delivery",
                "link_based",
                "attachment_based",
                "none"
            ],
            "description": "Type of phishing attack"
        },
        "indicators": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "indicator_type": {
                        "enum": [
                            "suspicious_sender",
                            "auth_failure",
                            "lookalike_domain",
                            "malicious_url",
                            "malicious_attachment",
                            "social_engineering",
                            "urgency_language"
                        ]
                    },
                    "description": {"type": "string"},
                    "severity": {"enum": ["high", "medium", "low"]}
                },
                "required": ["indicator_type", "description"]
            },
            "description": "List of phishing indicators found"
        },
        "target_brand": {
            "type": "string",
            "description": "Brand being impersonated (if applicable)"
        },
        "recommended_action": {
            "enum": [
                "quarantine",
                "delete",
                "warn_user",
                "monitor",
                "allow"
            ],
            "description": "Recommended action for this email"
        }
    },
    "required": ["is_phishing", "confidence", "phishing_type"]
}


THREAT_ASSESSMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "threat_level": {
            "enum": ["critical", "high", "medium", "low", "info"],
            "description": "Overall threat level"
        },
        "threat_actor": {
            "type": "object",
            "properties": {
                "sophistication": {
                    "enum": ["nation_state", "organized_crime", "hacktivist", "script_kiddie", "unknown"]
                },
                "motivation": {
                    "enum": ["financial", "espionage", "disruption", "vandalism", "unknown"]
                },
                "attribution": {
                    "type": "string",
                    "description": "Known threat actor group (if identified)"
                }
            }
        },
        "attack_vector": {
            "enum": [
                "email",
                "web",
                "network",
                "endpoint",
                "cloud",
                "physical",
                "social_engineering",
                "supply_chain",
                "unknown"
            ],
            "description": "Primary attack vector"
        },
        "targeted": {
            "type": "boolean",
            "description": "Whether this appears to be a targeted attack"
        },
        "impact_assessment": {
            "type": "object",
            "properties": {
                "confidentiality": {"enum": ["high", "medium", "low", "none"]},
                "integrity": {"enum": ["high", "medium", "low", "none"]},
                "availability": {"enum": ["high", "medium", "low", "none"]}
            },
            "description": "CIA triad impact"
        },
        "immediate_actions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Immediate actions to take"
        },
        "long_term_actions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Long-term remediation actions"
        }
    },
    "required": ["threat_level", "attack_vector"]
}


IP_REPUTATION_SCHEMA = {
    "type": "object",
    "properties": {
        "ip": {
            "type": "string",
            "pattern": "^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$"
        },
        "reputation": {
            "enum": ["malicious", "suspicious", "neutral", "trusted"],
            "description": "Overall reputation score"
        },
        "reputation_score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": "Numeric reputation (0=malicious, 100=trusted)"
        },
        "threat_types": {
            "type": "array",
            "items": {
                "enum": [
                    "malware",
                    "botnet",
                    "scanner",
                    "brute_force",
                    "spam",
                    "proxy",
                    "tor_exit",
                    "phishing"
                ]
            },
            "description": "Known malicious activities"
        },
        "geolocation": {
            "type": "object",
            "properties": {
                "country": {"type": "string"},
                "country_code": {"type": "string", "pattern": "^[A-Z]{2}$"},
                "city": {"type": "string"},
                "asn": {"type": "integer"},
                "as_name": {"type": "string"}
            }
        },
        "first_seen": {
            "type": "string",
            "format": "date-time",
            "description": "When this IP was first observed in threat intelligence"
        },
        "last_seen": {
            "type": "string",
            "format": "date-time",
            "description": "Most recent observation"
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence in reputation assessment"
        }
    },
    "required": ["ip", "reputation"]
}


DOMAIN_REPUTATION_SCHEMA = {
    "type": "object",
    "properties": {
        "domain": {
            "type": "string",
            "description": "Domain name"
        },
        "reputation": {
            "enum": ["malicious", "suspicious", "neutral", "trusted"],
            "description": "Overall reputation"
        },
        "category": {
            "type": "array",
            "items": {
                "enum": [
                    "malware",
                    "phishing",
                    "spam",
                    "c2",
                    "cryptomining",
                    "typosquatting",
                    "parked",
                    "benign"
                ]
            },
            "description": "Domain categories"
        },
        "registration": {
            "type": "object",
            "properties": {
                "registrar": {"type": "string"},
                "creation_date": {"type": "string", "format": "date"},
                "expiration_date": {"type": "string", "format": "date"},
                "recently_created": {
                    "type": "boolean",
                    "description": "Created within last 30 days"
                }
            }
        },
        "dns_records": {
            "type": "object",
            "properties": {
                "a_records": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "mx_records": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "nameservers": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "lookalike_of": {
            "type": "string",
            "description": "Legitimate domain this may be impersonating"
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
        }
    },
    "required": ["domain", "reputation"]
}


# =============================================================================
# Workflow Output Schemas
# =============================================================================

SECURITY_TRIAGE_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "object",
            "properties": {
                "total_alerts": {"type": "integer"},
                "unique_alerts": {"type": "integer"},
                "critical_count": {"type": "integer"},
                "kill_chains_detected": {"type": "integer"}
            },
            "required": ["total_alerts", "unique_alerts", "critical_count"]
        },
        "classifications": {
            "type": "object",
            "properties": {
                "P1": {"type": "array", "items": {"type": "object"}},
                "P2": {"type": "array", "items": {"type": "object"}},
                "P3": {"type": "array", "items": {"type": "object"}},
                "P4": {"type": "array", "items": {"type": "object"}},
                "P5": {"type": "array", "items": {"type": "object"}}
            }
        },
        "executive_summary": {
            "type": "string",
            "description": "LLM-generated executive brief for CISO"
        }
    },
    "required": ["summary", "classifications"]
}


# =============================================================================
# Helper Schemas for Common Patterns
# =============================================================================

EMAIL_AUTHENTICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "spf": {
            "enum": ["pass", "fail", "neutral", "softfail", "none"],
            "description": "SPF (Sender Policy Framework) result"
        },
        "dkim": {
            "enum": ["pass", "fail", "neutral", "none"],
            "description": "DKIM (DomainKeys Identified Mail) result"
        },
        "dmarc": {
            "enum": ["pass", "fail", "none"],
            "description": "DMARC (Domain-based Message Authentication) result"
        },
        "suspicious": {
            "type": "boolean",
            "description": "Overall authentication failure flag"
        },
        "spoof_detected": {
            "type": "boolean",
            "description": "Whether email spoofing was detected"
        }
    },
    "required": ["spf", "dkim", "dmarc", "suspicious"]
}


SEVERITY_CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "severity": {
            "enum": ["P1", "P2", "P3", "P4", "P5"]
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
        },
        "reasoning": {
            "type": "string",
            "description": "Explanation for severity classification"
        },
        "factors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "factor": {"type": "string"},
                    "weight": {"enum": ["high", "medium", "low"]}
                }
            },
            "description": "Factors contributing to severity assessment"
        }
    },
    "required": ["severity", "confidence"]
}
