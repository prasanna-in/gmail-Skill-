# Agent Conversation Examples

Comprehensive examples showing how Claude Code's Agent should orchestrate RLM email analysis operations.

---

## Example 1: Basic Inbox Triage

**User:** "Triage my inbox"

**Agent (Internal Reasoning):**
- Intent: Categorize emails by urgency
- Scope: inbox, last 7 days, ~100 emails
- Workflow: inbox_triage(emails)
- Cost estimate: ~$0.20

**Agent Response:**
```
I'll triage your inbox to categorize emails by priority. Let me analyze your recent emails.

[Executes: .venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py --query "is:inbox newer_than:7d" --max-results 100 --max-budget 1.00 --code "result = inbox_triage(emails); print(f'Urgent: {len(result[\"urgent\"])}'); print(f'Action Required: {len(result[\"action_required\"])}'); print(f'FYI: {len(result[\"fyi\"])}'); print(f'Newsletters: {len(result[\"newsletter\"])}'); FINAL(f'Found {len(result[\"urgent\"])} urgent emails requiring immediate attention')"]

Inbox Triage Complete:

**📌 Urgent (5 emails):** Require immediate attention
**✅ Action Required (12 emails):** Need response or action
**📄 FYI (48 emails):** Informational, no action needed
**📰 Newsletters (23 emails):** Automated/marketing emails

Would you like me to show you the urgent emails or help with specific actions?
```

**User:** "Show me the urgent emails"

**Agent (uses cached result from previous RLM execution):**
```
Here are your 5 urgent emails:

1. **From:** boss@company.com
   **Subject:** Q1 Budget Review - Need Input by EOD
   **Date:** Today, 9:15 AM

2. **From:** client@bigcorp.com
   **Subject:** Project delivery timeline - Urgent clarification needed
   **Date:** Today, 11:30 AM

3. **From:** security@company.com
   **Subject:** [P1] Critical Security Alert - Account Access Attempt
   **Date:** Today, 2:45 PM

... (continues with remaining 2)

Would you like me to help you draft responses or create action items from these?
```

---

## Example 2: Security Alert Triage

**User:** "Triage security alerts from last week"

**Agent (Internal Reasoning):**
- Intent: Security-specific analysis with P1-P5 classification
- Scope: label:security-alerts, 7 days, ~500 emails
- Workflow: security_triage(emails)
- Cost estimate: ~$2.00 (high volume)
- Action: Warn user about cost, ask confirmation

**Agent Response:**
```
I'll analyze your security alerts from the last week. Based on the volume (~500 alerts), this will cost approximately $2.00. Should I proceed?
```

**User:** "Yes, go ahead"

**Agent:**
```
Analyzing security alerts...

[Executes: .venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py --query "label:security-alerts newer_than:7d" --max-results 500 --max-budget 2.00 --code "result = security_triage(emails); print(f'Total: {result[\"summary\"][\"total_alerts\"]}'); print(f'P1: {len(result[\"classifications\"][\"P1\"])}'); print(f'P2: {len(result[\"classifications\"][\"P2\"])}'); print(f'Kill Chains: {len(result[\"kill_chains\"])}'); FINAL(result['executive_summary'])"]

## Security Alert Triage - Last 7 Days

**Summary:**
- Total Alerts: 487 (347 unique after deduplication)
- P1 Critical: 5
- P2 High: 12
- P3 Medium: 85
- P4 Low: 180
- P5 Info: 65

**Kill Chains Detected:** 2
- Initial Access → Execution → C2 (P1, 92% confidence)
- Reconnaissance → Exploitation (P2, 78% confidence)

**Indicators of Compromise:**
- 23 unique IP addresses
- 15 suspicious domains
- 8 file hashes (malware)

**Executive Summary:**
The threat landscape shows moderate activity with two critical concerns requiring immediate action. A sophisticated attack chain was detected involving phishing, PowerShell execution, and C2 callbacks targeting the finance department. Additionally, persistent brute-force attempts from three IP ranges suggest coordinated reconnaissance. The remaining alerts are primarily routine vulnerability scan findings and informational advisories. Immediate actions: investigate P1 attack chain, block identified IOCs, and review finance department access logs.

Cost: $1.87 | Tokens: 45,200 | Analysis time: 28s

Would you like details on the P1 critical alerts or the detected attack chains?
```

**User:** "Show me the P1 details"

**Agent (accesses cached result):**
```
## P1 Critical Alerts (5 alerts)

### 1. Multi-Stage Attack - Finance Department
**Time:** Jan 15, 2026, 10:23 AM - 10:35 AM
**Pattern:** Phishing → PowerShell Execution → C2 Callback
**Affected:** sarah.chen@company.com, 192.168.10.45
**MITRE:** T1566.001, T1059.001, T1071.001
**Confidence:** 92%

Details: Employee clicked phishing link, triggered weaponized document executing PowerShell script. Script established connection to known C2 server (185.220.102.8). Finance database access attempted from compromised workstation.

**Immediate Actions:**
1. Isolate workstation 192.168.10.45
2. Reset credentials for sarah.chen@company.com
3. Block C2 IP: 185.220.102.8
4. Audit finance database access logs

### 2. Ransomware Indicators - File Server
... (continues with remaining 4)

Should I generate an incident response ticket for the P1 attack chain?
```

---

## Example 3: Find Action Items

**User:** "What do I need to do? Find action items from my emails"

**Agent:**
```
I'll extract action items from your recent emails.

[Executes: .venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py --query "newer_than:7d" --max-results 150 --code "items = find_action_items(emails); FINAL_VAR('items')"]

Found 14 action items from your emails:

## High Priority (3)
1. **Complete Q1 budget proposal**
   - Deadline: This Friday (Jan 19)
   - Requested by: boss@company.com
   - Context: Email from Jan 15

2. **Review and approve marketing campaign**
   - Deadline: Tomorrow (Jan 18)
   - Requested by: marketing@company.com
   - Context: Needs sign-off before launch

3. **Schedule team sync for project retrospective**
   - Deadline: End of week
   - Requested by: pm@company.com
   - Context: Email thread from Jan 16

## Medium Priority (7)
4. **Respond to client feedback on deliverable**
   - Deadline: Next Monday
   - Requested by: client@partner.com
   ...

## Low Priority (4)
...

Would you like me to help you prioritize these or draft responses?

Cost: $0.22 | 11 action items extracted
```

---

## Example 4: Weekly Summary

**User:** "Summarize my week"

**Agent:**
```
I'll generate a summary of your emails from the past week.

[Executes: .venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py --query "newer_than:7d" --max-results 500 --code "summary = weekly_summary(emails); FINAL(summary)"]

## Your Week in Email (Jan 12-19, 2026)

**Key Themes:**
- Project Alpha launch preparation dominated communications (45 emails)
- Q1 budget review cycle initiated with multiple stakeholder meetings
- Customer feedback on new feature rollout generally positive
- Team transition planning for Sarah's departure

**Important Developments:**
- New enterprise client (Acme Corp) signed contract on Jan 15
- Product release date shifted from Jan 25 to Feb 8 due to QA findings
- Board meeting scheduled for Feb 1 - presentation prep starting
- Security incident in finance department resolved (see separate alerts)

**Action Items Summary:**
- 14 pending tasks identified, 3 with deadlines this week
- Budget proposal needs completion by Friday
- Client deliverable review needed by Monday

**Communication Patterns:**
- Most active: boss@company.com (52 emails), team@company.com (38 emails)
- Tone shift: Increased urgency around budget timeline
- New stakeholders: Finance team more engaged in project discussions

**Notable Decisions:**
- Approved marketing campaign for Q1
- Postponed feature launch to address customer feedback
- Greenlit hiring for two additional engineering positions

Cost: $0.48 | 487 emails analyzed

What would you like to explore further?
```

---

## Example 5: Sender Analysis

**User:** "Analyze emails from my top 5 senders and tell me what each person is emailing about"

**Agent:**
```
I'll analyze communication patterns from your top senders.

[Executes: .venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py --query "newer_than:14d" --max-results 300 --code "analysis = sender_analysis(emails, top_n=5); for sender, info in analysis.items(): print(f'{sender}: {info[\"count\"]} emails'); FINAL_VAR('analysis')"]

## Top 5 Sender Analysis (Last 2 Weeks)

### 1. boss@company.com (52 emails)
**Communication Tone:** Formal, directive
**Main Topics:**
- Q1 budget planning and resource allocation discussions
- Project Alpha status updates and milestone tracking
- Strategic planning for Q2 initiatives
- Performance review cycle coordination

**Pattern:** Primarily sends early morning (7-9 AM) and late afternoon (4-6 PM). Increased frequency this week around budget deadline.

### 2. team@company.com (38 emails)
**Communication Tone:** Informal, collaborative
**Main Topics:**
- Daily standup summaries and sprint planning
- Technical design discussions for new features
- Code review requests and merge notifications
- Team event coordination

**Pattern:** Distributed throughout day. Heavy use of GitHub integration for PR notifications.

### 3. client@partner.com (24 emails)
**Communication Tone:** Professional, detail-oriented
**Main Topics:**
- Project deliverable reviews and feedback
- Timeline adjustments and scope discussions
- Technical questions about implementation details
- Contract amendment negotiations

**Pattern:** Responds within 2-4 hours typically. Prefers detailed written communication over calls.

### 4. marketing@company.com (19 emails)
**Communication Tone:** Enthusiastic, creative
**Main Topics:**
- Q1 campaign planning and creative reviews
- Product launch messaging and positioning
- Customer case study development
- Event sponsorship opportunities

**Pattern:** Sends in bursts, often with multiple follow-ups. Prefers visual mockups attached.

### 5. security@company.com (15 emails)
**Communication Tone:** Urgent, technical
**Main Topics:**
- Security alert notifications and incident reports
- Compliance audit preparation
- Access review requests
- Security training reminders

**Pattern:** Irregular timing, often off-hours when incidents occur. Recent spike due to finance department incident.

Cost: $0.42 | 5 senders analyzed

Would you like deeper analysis on any particular sender or time period?
```

---

## Example 6: Custom Analysis Request

**User:** "Find all emails mentioning 'Project Alpha' and tell me if we're on track"

**Agent:**
```
I'll search for Project Alpha mentions and analyze the project status.

[Executes: .venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py --query "newer_than:30d" --max-results 200 --code "project_emails = filter_by_keyword(emails, 'project alpha'); status = llm_query('Based on these emails, is Project Alpha on track? Summarize: 1) Current status, 2) Key risks, 3) Next milestones, 4) Overall assessment', context=batch_extract_summaries(project_emails, max_chars=5000)); FINAL(f'Found {len(project_emails)} emails about Project Alpha\\n\\n{status}')"]

Found 47 emails about Project Alpha over the last 30 days.

## Project Alpha Status Assessment

**1. Current Status:** ⚠️ At Risk
The project is approximately 2 weeks behind original timeline. Core functionality is 85% complete, but QA has identified critical bugs that pushed the release from Jan 25 to Feb 8. The team is currently in bug-fixing sprint with daily triage meetings.

**2. Key Risks:**
- **Technical Debt:** Quick fixes early in development creating stability issues
- **Resource Constraints:** Sarah (lead developer) departing Jan 31, knowledge transfer incomplete
- **Scope Creep:** Marketing requesting additional features for launch that weren't in original spec
- **Integration Dependencies:** Third-party API delays affecting timeline

**3. Next Milestones:**
- Jan 22: QA regression testing complete
- Jan 25: Stakeholder demo of fixed version
- Jan 29: Final approval from product team
- Feb 1: Production deployment decision
- Feb 8: Target launch date (if approved)

**4. Overall Assessment:**
Project is recoverable but needs immediate attention. The Feb 8 date is achievable if scope is held firm and QA findings are addressed this week. However, stakeholder confidence is waning due to repeated delays. Recommend: 1) Lock scope immediately, 2) Accelerate Sarah's knowledge transfer, 3) Add QA resource for parallel testing, 4) Schedule executive alignment meeting.

**Sentiment Trend:** Communications shifted from optimistic (3 weeks ago) to concerned (last week) to cautiously focused (this week).

Cost: $0.15 | 47 emails analyzed

Would you like me to extract specific action items or identify key decision makers?
```

---

## Example 7: Attack Chain Detection

**User:** "Find attack chains in security alerts from today"

**Agent:**
```
I'll analyze today's security alerts for multi-stage attack patterns.

[Executes: .venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py --query "label:security-alerts newer_than:1d" --max-results 200 --code "chains = detect_attack_chains(emails, window_minutes=5); critical = [c for c in chains if c['severity'] in ['P1', 'P2']]; if critical: output = '## Critical Attack Chains\\n\\n'; [output := output + f\"**{c['attack_id']}** ({c['severity']})\\nPattern: {c['pattern']}\\nMITRE: {', '.join(c['mitre_techniques'])}\\nConfidence: {c['confidence']:.0%}\\nAffected: {', '.join(c['affected_systems'][:3])}\\n\\n\" for c in critical]; FINAL(output); else: FINAL('No critical attack chains detected.')"]

## Critical Attack Chains Detected

### Attack Chain 1: chain_20260119_001 (P1 - Critical)
**Pattern:** Phishing Email → Macro Execution → Credential Harvesting
**Duration:** 12 minutes (10:23 AM - 10:35 AM)
**MITRE Techniques:** T1566.001, T1204.002, T1056.001
**Confidence:** 94%
**Affected Systems:**
- jennifer.wong@company.com
- DESKTOP-8HK3M (192.168.10.67)
- Domain Controller query attempts

**Attack Narrative:**
Employee received targeted phishing email impersonating IT department. Opened attached Excel document with malicious macro. Macro executed keylogger and attempted to harvest domain credentials. Endpoint detection triggered alerts for suspicious PowerShell activity and unauthorized credential access attempts.

**Current Status:** ACTIVE INCIDENT
**Recommended Actions:**
1. IMMEDIATE: Isolate DESKTOP-8HK3M from network
2. Reset credentials for jennifer.wong@company.com
3. Force password reset for entire finance department (precautionary)
4. Audit domain controller access logs for last 2 hours
5. Scan email for similar phishing attempts

### Attack Chain 2: chain_20260119_002 (P2 - High)
**Pattern:** Port Scan → SMB Enumeration → Brute Force
**Duration:** 28 minutes (2:10 PM - 2:38 PM)
**MITRE Techniques:** T1046, T1021.002, T1110.001
**Confidence:** 87%
**Affected Systems:**
- 192.168.20.0/24 subnet (file servers)
- Source IP: 45.142.215.89 (external)

**Attack Narrative:**
External IP conducted systematic port scan of file server subnet, identified SMB shares, attempted brute force on admin accounts. Firewall logs show 1,247 connection attempts. Attack ceased after account lockout threshold triggered.

**Current Status:** BLOCKED
**Recommended Actions:**
1. Verify source IP 45.142.215.89 is blocked at perimeter
2. Review account lockout events for compromised credentials
3. Audit SMB share permissions on affected subnet
4. Consider geo-blocking if source country not business-relevant

**Summary:** 2 critical attack chains detected today requiring immediate response. Incident response team should prioritize chain_20260119_001 (active credential compromise).

Cost: $0.98 | 187 alerts analyzed, 2 chains detected

Should I generate incident response tickets for these chains?
```

---

## Example 8: Phishing Analysis

**User:** "Check my inbox for phishing attempts"

**Agent:**
```
I'll analyze your inbox for potential phishing emails.

[Executes: .venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py --query "is:inbox newer_than:7d" --max-results 150 --code "results = phishing_analysis(emails); print(f'Credential Harvesting: {len(results[\"credential_harvesting\"])}'); print(f'BEC Attempts: {len(results[\"bec_attempts\"])}'); FINAL_VAR('results')"]

## Phishing Analysis - Inbox (Last 7 Days)

**Threats Detected:**
- Credential Harvesting: 3 attempts
- Business Email Compromise (BEC): 1 attempt
- Brand Impersonation: 2 attempts
- Malicious Links: 4 suspicious URLs
- Risky Attachments: 1 high-risk file

### High Risk: Credential Harvesting (3)

1. **Subject:** "Your Microsoft Account Has Been Suspended"
   **From:** noreply@micros0ft-security.com
   **Reason:** Domain squatting (micros0ft vs microsoft), urgency language, fake login link
   **Risk Level:** HIGH
   **Action:** Delete immediately, report to IT security

2. **Subject:** "Verify Your Payroll Information"
   **From:** hr@c0mpany.com
   **Reason:** Internal domain spoofing, requests credential verification
   **Risk Level:** HIGH
   **Action:** Report to HR and IT security immediately

3. **Subject:** "Update Payment Method for Netflix"
   **From:** account@netflix-billing.xyz"
   **Reason:** Suspicious TLD (.xyz), not from legitimate Netflix domain
   **Risk Level:** MEDIUM
   **Action:** Delete, do not click links

### Medium Risk: BEC Attempt (1)

1. **Subject:** "Urgent Wire Transfer Request"
   **From:** CEO@company.com (Display Name: "John Smith CEO")
   **Actual Email:** john.ceo@gmail.com
   **Reason:** Display name spoofing, urgency, financial request
   **Risk Level:** HIGH
   **Action:** DO NOT TRANSFER FUNDS. Verify with CEO via phone call.

### Medium Risk: Brand Impersonation (2)

1. **From:** Amazon.com Customer Service <amaz0n-orders@mailservice.ru>
   **Reason:** Russian email domain, Amazon brand impersonation

2. **From:** PayPal Security <verify@paypa1.com>
   **Reason:** Number substitution (paypa1), suspicious domain

### Suspicious URLs Detected (4)
- bit.ly/3xK9mP2 - URL shortener in financial context
- 185.220.102.8/login - IP address instead of domain
- g00gle-verify.tk - Typosquatting + suspicious TLD

### Risky Attachment (1)
- invoice_january.exe - Executable disguised as invoice

**Summary:**
Your inbox shows active phishing targeting with both generic attacks (Netflix, PayPal) and targeted BEC attempt impersonating your CEO. The CEO impersonation email is particularly concerning and may indicate reconnaissance. Recommend: immediately report the BEC attempt to security team and delete all flagged emails without opening links/attachments.

**Recommended Actions:**
1. Report BEC attempt to security@company.com
2. Delete all flagged emails
3. Enable 2FA if not already active
4. Schedule security awareness training refresher

Cost: $0.38 | 147 emails analyzed, 11 threats identified

Would you like me to help draft a security incident report?
```

---

## Example 9: Budget Control

**User:** "Analyze all my emails from the last month"

**Agent:**
```
I can analyze your emails from the last month. Based on typical volumes, this would involve ~2,000 emails and cost approximately $4.00-$5.00.

This exceeds the default budget of $1.00. Would you like me to:

1. Proceed with full analysis (budget: $5.00)
2. Narrow the scope (e.g., last 2 weeks, specific senders, certain topics)
3. Use faster/cheaper model (Haiku instead of Sonnet, ~$0.50 but less accurate)

What would you prefer?
```

**User:** "Option 2, focus on work emails only"

**Agent:**
```
Good choice. I'll focus on work-related emails by filtering to your company domain and excluding newsletters.

[Executes: .venv/bin/python skills/gmail/scripts/gmail_rlm_repl.py --query "from:*@company.com newer_than:30d -category:promotions" --max-results 500 --max-budget 2.00 --code "summary = weekly_summary(emails); FINAL(summary)"]

## Work Email Summary (Last 30 Days)

Analyzed 487 emails from company.com domain.

**Major Initiatives:**
- Project Alpha: Launch timeline adjusted, now targeting Feb 8
- Q1 Budget: Review cycle in progress, proposals due this Friday
- Team Restructuring: Sarah's departure planned, hiring for 2 positions approved
- Security Posture: Incident response improvements after finance dept breach
...

Cost: $1.82 | 487 emails analyzed (saved $3.18 by filtering)

This focused analysis provided the key information at 40% of the original cost estimate.
```

---

## Example 10: Multi-Turn Dialogue with Context

**User:** "Triage my inbox"

**Agent:**
```
[Executes inbox triage...]

Inbox Triage Complete:
- Urgent: 5 emails
- Action Required: 12 emails
- FYI: 48 emails
- Newsletters: 23 emails

Cost: $0.20
```

**User:** "What are the urgent ones about?"

**Agent (accesses cached triage result, no re-execution):**
```
The 5 urgent emails are:

1. Q1 Budget Review - boss needs your input by EOD
2. Client deliverable clarification - timeline question
3. P1 Security Alert - account access attempt
4. Board presentation - CEO requesting draft by tomorrow
5. Contract approval - legal team needs signature today

All require action today. Which would you like to tackle first?

No additional cost (using cached result)
```

**User:** "Help me draft a response to the budget review request"

**Agent (still using cached context, reading that specific email):**
```
Based on the email from your boss, they're asking for:
- Q1 spending breakdown by department
- Forecast for Q2 hiring needs
- Justification for any budget increases

I can help draft a response. Do you have:
1. The spending breakdown ready?
2. Specific hiring plans you'd like to mention?

Or would you like me to draft a message requesting a deadline extension?
```

**User:** "Draft an extension request"

**Agent:**
```
Here's a draft:

---
Subject: Re: Q1 Budget Review - Need Input by EOD

Hi [Boss],

I received your request for the Q1 budget analysis. To provide you with accurate and comprehensive data, I'd like to request an extension until Monday (Jan 22) at 10 AM.

This will allow me to:
- Coordinate with department heads for detailed spending breakdowns
- Review Q2 hiring pipeline with HR
- Validate numbers with finance team

I can provide a preliminary summary by EOD today if you need high-level numbers for an urgent meeting.

Would Monday morning work for the detailed submission?

Thanks,
[Your name]
---

Would you like me to modify this or shall we send it?
```

**Total Conversation Cost:** $0.20 (only the initial triage, all follow-ups used cached data)

---

## Key Patterns Demonstrated

1. **Cost Transparency:** Always estimate and show costs
2. **Confirmations:** Ask before expensive operations (>$1)
3. **Caching:** Reuse RLM results for follow-up questions
4. **Budget Optimization:** Suggest alternatives when cost is high
5. **Natural Flow:** Conversational, not robotic
6. **Actionable Insights:** Always offer next steps
7. **Context Preservation:** Remember previous analysis across turns
8. **Clear Formatting:** Use markdown, headers, lists for readability
9. **Technical Details When Needed:** Show MITRE techniques, IOCs for security
10. **Session Stats:** Display cost/tokens when relevant

---

## Error Handling Examples

### Error: Missing API Key

**User:** "Triage security alerts"

**Agent:**
```
I encountered an error: the ANTHROPIC_API_KEY environment variable is not set.

RLM email analysis requires access to Claude AI for processing. To fix this:

1. Get your API key from: https://console.anthropic.com/
2. Set the environment variable:
   ```
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```
3. Then try the command again

Would you like help with anything that doesn't require RLM analysis?
```

### Error: Gmail Authentication Failed

**User:** "Summarize my emails"

**Agent:**
```
I encountered an authentication error with Gmail. Your OAuth tokens may have expired.

To fix this, you need to re-authenticate:

```bash
.venv/bin/python skills/gmail/scripts/gmail_auth.py
```

This will open a browser window for you to grant access. After completing authentication, try your request again.
```

### Error: Budget Exceeded

**User:** "Analyze 5000 emails"

**Agent:**
```
The analysis started but hit the budget limit midway through.

Partial results (1,247 of 5,000 emails analyzed):
- Budget used: $1.00 (limit reached)
- ...partial summary...

To complete the analysis, you can:
1. Increase budget: --max-budget 4.00 (estimated $3.50 total)
2. Narrow scope: Analyze specific senders or time ranges
3. Use checkpoint feature: Resume from where we stopped

What would you prefer?
```

---

This document provides comprehensive examples for Claude Code's Agent to learn natural, effective RLM orchestration patterns.
