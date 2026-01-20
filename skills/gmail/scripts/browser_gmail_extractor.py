#!/usr/bin/env python3
"""
Real browser-based Gmail email extractor using agent-browser.

This module provides the actual browser automation to extract emails from Gmail
when API access is blocked.
"""

import json
import subprocess
import time
from typing import Optional
from datetime import datetime


class AgentBrowserError(Exception):
    """Error running agent-browser command."""
    pass


class GmailBrowserExtractor:
    """
    Extract emails from Gmail using agent-browser automation.

    This class handles:
    - Session management (persistent login)
    - Navigation to Gmail
    - Email list extraction
    - Individual email content extraction
    """

    def __init__(self, session_name: str = "gmail_corporate", headless: bool = True):
        """
        Initialize Gmail browser extractor.

        Args:
            session_name: Agent-browser session name (persists cookies/auth)
            headless: Run in headless mode (False = show browser window)
        """
        self.session_name = session_name
        self.headless = headless

    def _run_command(self, *args, expect_json: bool = False, timeout: int = 30) -> dict | str:
        """
        Run agent-browser command and return output.

        Args:
            *args: Command arguments
            expect_json: Parse output as JSON
            timeout: Command timeout in seconds

        Returns:
            Parsed JSON dict if expect_json=True, otherwise raw stdout string

        Raises:
            AgentBrowserError: If command fails
        """
        cmd = ["agent-browser", "--session", self.session_name]

        if not self.headless:
            cmd.append("--headed")

        if expect_json:
            cmd.append("--json")

        cmd.extend(str(arg) for arg in args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                raise AgentBrowserError(
                    f"Command failed: {' '.join(cmd)}\n"
                    f"Exit code: {result.returncode}\n"
                    f"Stderr: {result.stderr}"
                )

            if expect_json:
                response = json.loads(result.stdout)
                if not response.get("success"):
                    raise AgentBrowserError(
                        f"Command returned error: {response.get('error', 'Unknown error')}"
                    )
                return response.get("data", {})

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            raise AgentBrowserError(f"Command timed out after {timeout}s")
        except json.JSONDecodeError as e:
            raise AgentBrowserError(f"Failed to parse JSON output: {e}\n{result.stdout}")
        except Exception as e:
            raise AgentBrowserError(f"Unexpected error: {e}")

    def open_gmail(self, url: str = "https://mail.google.com/mail/u/0") -> None:
        """
        Open Gmail and wait for login if needed.

        Args:
            url: Gmail URL to open
        """
        print(f"Opening Gmail at {url}...")
        self._run_command("open", url, timeout=60)

        # Wait for page to load
        print("Waiting for Gmail to load...")
        time.sleep(5)

        # Check if we need to login
        title = self._run_command("get", "title", expect_json=True)
        current_title = title.get("value", "")

        if "sign in" in current_title.lower() or "login" in current_title.lower():
            print("\n" + "="*60)
            print("MANUAL LOGIN REQUIRED")
            print("="*60)
            print("A browser window will open. Please:")
            print("1. Log in to your Gmail account")
            print("2. Complete any MFA/2FA if required")
            print("3. Wait for Gmail inbox to fully load")
            print("4. Come back to this terminal")
            print("="*60)

            # Open in headed mode for login
            if self.headless:
                print("\nNote: Opening browser window for login...")
                self._run_command("open", url)  # This will reopen in headed mode if needed

            input("\nPress Enter once you've logged in and Gmail inbox is visible...")

    def get_email_list_elements(self, max_results: int = 10) -> list[str]:
        """
        Get list of email row elements from Gmail inbox.

        This uses JavaScript evaluation to find email rows in Gmail's DOM.
        Gmail uses dynamic class names, so we search for specific patterns.

        Args:
            max_results: Maximum number of emails to find

        Returns:
            List of element selectors for email rows
        """
        print(f"Finding email rows (max {max_results})...")

        # Gmail email rows are typically in a table with role="row"
        # We'll use JavaScript to find them
        js_code = f"""
        (() => {{
            // Find email rows - Gmail uses tr.zA for email rows
            const rows = Array.from(document.querySelectorAll('tr.zA'))
                .filter(row => {{
                    // Filter out non-email rows
                    // Gmail email rows have class 'zA' and are in the main table
                    return row.querySelector('td') !== null;
                }})
                .slice(0, {max_results});

            // Return count for debugging
            return rows.length;
        }})()
        """

        result = self._run_command("eval", js_code, expect_json=True)
        count = result.get("result", 0)

        print(f"Found {count} email rows")

        # Return selectors for the rows
        return [f"tr.zA:nth-child({i+1})" for i in range(count)]

    def extract_email_from_row(self, row_index: int) -> Optional[dict]:
        """
        Extract email data from a specific row.

        This clicks the email to open it, extracts content, then goes back.

        Args:
            row_index: Index of email row (0-based)

        Returns:
            Email dict with subject, from, to, date, body, or None if failed
        """
        try:
            print(f"  Extracting email {row_index + 1}...")

            # Click the email row using JavaScript (more reliable than CSS selector)
            click_js = f"""
            (() => {{
                const rows = Array.from(document.querySelectorAll('tr.zA'))
                    .filter(row => row.querySelector('td') !== null);
                if (rows[{row_index}]) {{
                    rows[{row_index}].click();
                    return true;
                }}
                return false;
            }})()
            """

            click_result = self._run_command("eval", click_js, expect_json=True)
            if not click_result.get("result"):
                print(f"  Could not find row {row_index}")
                return None

            # Wait for email to open
            time.sleep(3)

            # Extract email data using JavaScript
            js_extract = """
            (() => {
                // Find subject - Gmail uses h2 for subject in opened email
                const subject = document.querySelector('h2')?.textContent ||
                               document.querySelector('.hP')?.textContent ||
                               '(No subject)';

                // Find sender - look for email attribute on sender elements
                const senderElem = document.querySelector('.gD[email]') ||
                                  document.querySelector('.go[email]') ||
                                  document.querySelector('[email]');
                const from = senderElem?.getAttribute('email') ||
                            senderElem?.textContent ||
                            '(Unknown sender)';

                // Find date - Gmail shows date in various places
                const dateElem = document.querySelector('.g3')?.getAttribute('title') ||
                                document.querySelector('[data-tooltip]')?.getAttribute('data-tooltip') ||
                                document.querySelector('.g3')?.textContent ||
                                new Date().toISOString();

                // Find email body - Gmail uses div.ii for message body
                const bodyElem = document.querySelector('.ii') ||
                                document.querySelector('.a3s');
                const body = bodyElem?.textContent ||
                            '(Body not available)';

                // Find recipients - to field
                const toElems = document.querySelectorAll('.g2[email]');
                const to = Array.from(toElems)
                    .map(el => el.getAttribute('email'))
                    .filter(Boolean)
                    .join(', ') || '';

                return {
                    subject: subject.trim(),
                    from: from.trim(),
                    to: to.trim(),
                    date: dateElem,
                    body: body.trim().substring(0, 10000) // Limit body size
                };
            })()
            """

            result = self._run_command("eval", js_extract, expect_json=True)
            email_data = result.get("result", {})

            if not email_data or not email_data.get("subject"):
                print(f"  Warning: Could not extract full email data")

            # Go back to email list
            self._run_command("back")
            time.sleep(2)

            return email_data

        except Exception as e:
            print(f"  Failed to extract email {row_index + 1}: {e}")
            # Try to go back anyway
            try:
                self._run_command("back")
                time.sleep(1)
            except:
                pass
            return None

    def _click_older_button(self) -> bool:
        """
        Find and click Gmail's [Older] pagination button.

        Uses multiple fallback strategies to locate the button:
        1. Search by aria-label containing "Older"
        2. Find navigation div and select rightmost button
        3. Search by title/tooltip attributes
        4. Check button is not disabled before clicking

        Returns:
            True if button was found and clicked, False otherwise
        """
        js_click = """
        (() => {
            // Strategy 1: Find by aria-label
            let olderBtn = Array.from(document.querySelectorAll('button, div[role="button"]'))
                .find(btn => {
                    const label = btn.getAttribute('aria-label') || btn.textContent || '';
                    return label.toLowerCase().includes('older');
                });

            // Strategy 2: Find in navigation div
            if (!olderBtn) {
                const navDiv = document.querySelector('div[role="navigation"]');
                if (navDiv) {
                    const buttons = navDiv.querySelectorAll('button');
                    if (buttons.length >= 2) {
                        olderBtn = buttons[buttons.length - 1];  // Rightmost button
                    }
                }
            }

            // Strategy 3: Find by title/tooltip
            if (!olderBtn) {
                olderBtn = document.querySelector('[title*="Older"], [data-tooltip*="Older"]');
            }

            // Strategy 4: Check if button is enabled and click
            if (olderBtn && olderBtn.getAttribute('aria-disabled') !== 'true') {
                olderBtn.click();
                return true;
            }
            return false;
        })()
        """

        try:
            result = self._run_command("eval", js_click, expect_json=True)
            return result.get("result", False)
        except Exception:
            return False

    def _filter_duplicates(self, existing: list[dict], new: list[dict]) -> list[dict]:
        """
        Remove emails already in accumulated list.

        Uses a temporary _page_unique_id field to identify duplicates.

        Args:
            existing: List of already-accumulated emails
            new: List of newly extracted emails from current page

        Returns:
            List of new emails not in existing list
        """
        if not existing:
            return new

        existing_ids = {
            email.get('_page_unique_id', email.get('subject', '') + email.get('from', ''))
            for email in existing
        }

        return [
            email for email in new
            if email.get('_page_unique_id', email.get('subject', '') + email.get('from', ''))
            not in existing_ids
        ]

    def _extract_emails_from_current_page(self, max_results: int) -> list[dict]:
        """
        Extract emails from currently visible Gmail page.

        This reuses the JavaScript extraction logic from extract_emails_from_list
        but adds a _page_unique_id field for deduplication across pages.

        Args:
            max_results: Maximum number of emails to extract from this page

        Returns:
            List of email dicts with _page_unique_id field
        """
        js_extract_all = f"""
        (() => {{
            const rows = Array.from(document.querySelectorAll('tr.zA'))
                .filter(row => row.querySelector('td') !== null)
                .slice(0, {max_results});

            return rows.map(row => {{
                const cells = row.querySelectorAll('td');

                // Extract sender (typically cell 3 or 4)
                const senderCell = cells[3] || cells[4];
                const sender = senderCell?.querySelector('[email]')?.getAttribute('email') ||
                              senderCell?.querySelector('.yP, .yW')?.innerText ||
                              senderCell?.innerText?.trim() ||
                              '(Unknown sender)';

                // Extract subject and snippet (typically cell 4 or 5)
                const subjectCell = cells[4] || cells[5];
                const subjectText = subjectCell?.innerText?.trim() || '(No subject)';

                // Try to separate subject from snippet
                let subject = subjectText;
                let snippet = '';
                if (subjectText.includes('\\n')) {{
                    const parts = subjectText.split('\\n');
                    subject = parts[0];
                    snippet = parts.slice(1).join(' ');
                }} else {{
                    snippet = subjectText;
                }}

                // Extract date (typically one of the last cells)
                const dateCell = cells[cells.length - 2] || cells[cells.length - 1];
                const date = dateCell?.querySelector('span')?.getAttribute('title') ||
                            dateCell?.innerText?.trim() ||
                            new Date().toISOString();

                const body = snippet;

                // Create unique ID for deduplication (subject||sender||date)
                const uniqueId = subject.substring(0, 100) + '||' + sender + '||' + date;

                return {{
                    subject: subject.substring(0, 500),
                    from: sender,
                    to: '',  // Not available in list view
                    date: date,
                    body: body.substring(0, 10000),
                    _page_unique_id: uniqueId
                }};
            }});
        }})()
        """

        try:
            result = self._run_command("eval", js_extract_all, expect_json=True)
            emails = result.get("result", [])
            return emails
        except Exception as e:
            print(f"  Warning: Failed to extract emails from current page: {e}")
            return []

    def paginate_to_load_more_emails(
        self,
        target_count: int,
        max_pages: int = 20,
        page_size: int = 50
    ) -> tuple[int, list[dict]]:
        """
        Navigate Gmail pages using [Older] button clicks to load more emails.

        Gmail uses server-side pagination with [Older]/[Newer] buttons instead
        of infinite scroll. This method clicks through pages to accumulate emails.

        Args:
            target_count: Target number of emails to accumulate
            max_pages: Maximum number of pages to navigate (default: 20)
            page_size: Expected emails per page (default: 50)

        Returns:
            Tuple of (total_count, all_emails_list)
        """
        print(f"Loading emails via pagination (target: {target_count}, max pages: {max_pages})...")

        accumulated_emails = []
        current_page = 1
        stall_count = 0

        while len(accumulated_emails) < target_count and current_page <= max_pages:
            print(f"  Page {current_page}: Extracting emails...")

            # Extract emails from current page
            page_emails = self._extract_emails_from_current_page(
                max_results=min(page_size, target_count - len(accumulated_emails))
            )

            if not page_emails:
                print(f"  Page {current_page}: No emails found, stopping")
                break

            # Filter duplicates
            new_emails = self._filter_duplicates(accumulated_emails, page_emails)

            # Detect stalls (no new emails)
            if not new_emails:
                stall_count += 1
                print(f"  Page {current_page}: No new emails (stall count: {stall_count})")
                if stall_count >= 2:
                    print(f"  No new emails after {stall_count} pages, stopping")
                    break
            else:
                accumulated_emails.extend(new_emails)
                stall_count = 0
                print(f"  Page {current_page}: Added {len(new_emails)} new emails (total: {len(accumulated_emails)})")

            # Check if target reached
            if len(accumulated_emails) >= target_count:
                print(f"  Target reached: {len(accumulated_emails)} emails")
                break

            # Click [Older] button to next page
            print(f"  Page {current_page}: Clicking [Older] button...")
            if not self._click_older_button():
                print(f"  [Older] button not found or disabled, stopping")
                break

            time.sleep(2.5)  # Wait for page load
            current_page += 1

        print(f"Pagination complete: {len(accumulated_emails)} emails across {current_page} pages")
        return len(accumulated_emails), accumulated_emails

    def extract_emails_from_list(self, max_results: int = 10) -> list[dict]:
        """
        Extract email data directly from the inbox list (fast method).

        This extracts subject, sender, date, and snippet from the email list
        without opening individual emails. Much faster than clicking each email.

        For large requests (>50 emails), automatically uses pagination with
        [Older] button clicks to navigate through multiple pages.

        Args:
            max_results: Maximum number of emails to extract

        Returns:
            List of email dicts
        """
        print(f"\nExtracting up to {max_results} emails from Gmail inbox list...")

        if max_results <= 50:
            # Single page - use direct extraction
            emails = self._extract_emails_from_current_page(max_results)

            # Remove temporary _page_unique_id field
            for email in emails:
                email.pop('_page_unique_id', None)

            print(f"Successfully extracted {len(emails)} emails from list")
            return emails
        else:
            # Multi-page - use pagination
            max_pages = min((max_results // 50) + 2, 25)
            total_count, all_emails = self.paginate_to_load_more_emails(
                target_count=max_results,
                max_pages=max_pages,
                page_size=50
            )

            # Remove temporary _page_unique_id field
            for email in all_emails:
                email.pop('_page_unique_id', None)

            print(f"Successfully extracted {len(all_emails)} emails across multiple pages")
            return all_emails[:max_results]

    def extract_emails(self, max_results: int = 10, include_body: bool = False) -> list[dict]:
        """
        Extract multiple emails from Gmail inbox.

        Args:
            max_results: Maximum number of emails to extract
            include_body: If True, click each email to get full body (slower)

        Returns:
            List of email dicts
        """
        if include_body:
            # Slow method: click each email to get full body
            print(f"\nExtracting up to {max_results} emails (with full body)...")

            # Get email row count
            email_selectors = self.get_email_list_elements(max_results)

            emails = []
            for idx in range(len(email_selectors)):
                email_data = self.extract_email_from_row(idx)
                if email_data:
                    emails.append(email_data)

            print(f"\nSuccessfully extracted {len(emails)} emails")
            return emails
        else:
            # Fast method: extract from list directly
            return self.extract_emails_from_list(max_results)


def main():
    """Test the Gmail browser extractor."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Gmail browser extraction")
    parser.add_argument("--max-results", type=int, default=5, help="Max emails to extract")
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    parser.add_argument("--session", default="gmail_test", help="Session name")
    args = parser.parse_args()

    extractor = GmailBrowserExtractor(
        session_name=args.session,
        headless=not args.headed
    )

    try:
        # Open Gmail
        extractor.open_gmail()

        # Extract emails
        emails = extractor.extract_emails(max_results=args.max_results)

        # Display results
        print("\n" + "="*60)
        print("EXTRACTED EMAILS")
        print("="*60)
        for idx, email in enumerate(emails, 1):
            print(f"\nEmail {idx}:")
            print(f"  Subject: {email.get('subject', 'N/A')}")
            print(f"  From: {email.get('from', 'N/A')}")
            print(f"  Date: {email.get('date', 'N/A')}")
            print(f"  Body preview: {email.get('body', '')[:100]}...")

        # Save to file
        output_file = "/tmp/gmail_browser_test.json"
        with open(output_file, 'w') as f:
            json.dump({
                "status": "success",
                "count": len(emails),
                "emails": emails
            }, f, indent=2)
        print(f"\nSaved to: {output_file}")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
