#!/usr/bin/env python3
"""
RHSTOR Epic Fetcher
A simplified tool to fetch and display RHSTOR epics with specific labels or fix versions
"""

from jira import JIRA
import sys
import os
import argparse
import re
from collections import Counter

# Version information
__version__ = "1.3.0"
__author__ = "Mudit Agarwal"
__email__ = "muditag85@gmail.com"

# JIRA Configuration
server = 'https://issues.redhat.com'
api_token = os.getenv('JIRA_API_TOKEN')

# Allowed JIRA statuses
ALLOWED_STATUSES = [
    "To Do",
    "In Progress", 
    "Code Review",
    "ON_QA",
    "Verified",
    "Closed"
]

if not api_token:
    print("❌ Error: JIRA_API_TOKEN environment variable not set!")
    print("Please set it using: export JIRA_API_TOKEN='your-token-here'")
    sys.exit(1)


def validate_fix_version(version):
    """
    Validate that fix_version is in numerical format (e.g., 4.19.0, 4.19, 1.2.3)
    
    Args:
        version: Version string to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not version:
        return False
    
    # Pattern for numerical versions: digits.digits.digits or digits.digits
    pattern = r'^\d+\.\d+(?:\.\d+)?$'
    return bool(re.match(pattern, version))


def validate_status(status):
    """
    Validate that status is one of the allowed JIRA statuses
    
    Args:
        status: Status string to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not status:
        return False
    
    return status in ALLOWED_STATUSES


def transform_fix_version(fix_version):
    """
    Transform numerical fix version input to JIRA format
    
    Args:
        fix_version: Numerical version (e.g., "4.19" or "4.19.0")
        
    Returns:
        str: Transformed version in JIRA format (e.g., "ODF v4.19.0")
    """
    if not fix_version:
        return None
    
    return f"ODF v{fix_version}.0"


def connect_to_jira():
    """Connect to JIRA instance"""
    try:
        jira = JIRA(server=server, token_auth=api_token)
        print(f"✅ Connected to JIRA: {server}")
        return jira
    except Exception as e:
        print(f"❌ Failed to connect to JIRA: {e}")
        return None


def fetch_epics_for_status_summary(jira, label=None, fix_version=None, max_results=1000):
    """
    Fetch all RHSTOR epics for status summary (without status filter)
    
    Args:
        jira: JIRA instance
        label: Label to search for (optional)
        fix_version: Numerical fix version to search for (optional)
        max_results: Maximum number of results to return
    
    Returns:
        List of epic issues
    """
    # Build search query based on provided criteria (excluding status)
    base_query = 'project = RHSTOR AND issuetype = Epic'
    query_parts = []
    
    if label:
        query_parts.append(f'labels = "{label}"')
    
    if fix_version:
        if not validate_fix_version(fix_version):
            print(f"❌ Error: Invalid fix version format '{fix_version}'. Use numerical format like '4.19.0' or '4.19'")
            return []
        
        # Transform numerical input to JIRA format
        jira_fix_version = transform_fix_version(fix_version)
        query_parts.append(f'fixVersion = "{jira_fix_version}"')
    
    if query_parts:
        search_query = f'{base_query} AND {" AND ".join(query_parts)}'
    else:
        # For summary, use base query without default label filter
        search_query = base_query
    
    try:
        issues = jira.search_issues(search_query, maxResults=max_results)
        return issues
    except Exception as e:
        print(f"❌ Error searching for epics: {e}")
        return []


def print_status_summary(issues, target_status=None):
    """
    Print summary of epics by status
    
    Args:
        issues: List of JIRA issues
        target_status: If specified, highlight this status
    """
    if not issues:
        print("📊 No epics found for status summary.")
        return
    
    # Count epics by status
    status_counts = Counter(str(issue.fields.status) for issue in issues)
    
    print("📊 Epic Status Summary:")
    print("=" * 60)
    
    total_epics = len(issues)
    
    # Show counts for all allowed statuses (even if 0)
    for status in ALLOWED_STATUSES:
        count = status_counts.get(status, 0)
        percentage = (count / total_epics * 100) if total_epics > 0 else 0
        
        # Highlight target status if specified
        if target_status and status == target_status:
            print(f"  ➤ {status:<15} : {count:>3} epics ({percentage:>5.1f}%) ← FILTERED")
        else:
            print(f"    {status:<15} : {count:>3} epics ({percentage:>5.1f}%)")
    
    # Show any unexpected statuses
    unexpected_statuses = set(status_counts.keys()) - set(ALLOWED_STATUSES)
    if unexpected_statuses:
        print("\n  Other statuses:")
        for status in unexpected_statuses:
            count = status_counts[status]
            percentage = (count / total_epics * 100) if total_epics > 0 else 0
            print(f"    {status:<15} : {count:>3} epics ({percentage:>5.1f}%)")
    
    print(f"\n  {'Total':<15} : {total_epics:>3} epics")
    print("=" * 60)


def fetch_epics_by_criteria(jira, label=None, fix_version=None, status=None, max_results=100):
    """
    Fetch RHSTOR epics with a specific label, fix version, and/or status
    
    Args:
        jira: JIRA instance
        label: Label to search for (optional)
        fix_version: Numerical fix version to search for (optional, e.g., "4.19.0")
        status: Status to search for (optional, e.g., "In Progress")
        max_results: Maximum number of results to return
    
    Returns:
        List of epic issues
    """
    # Build search query based on provided criteria
    base_query = 'project = RHSTOR AND issuetype = Epic'
    query_parts = []
    search_descriptions = []
    
    if label:
        query_parts.append(f'labels = "{label}"')
        search_descriptions.append(f"label: {label}")
    
    if fix_version:
        if not validate_fix_version(fix_version):
            print(f"❌ Error: Invalid fix version format '{fix_version}'. Use numerical format like '4.19.0' or '4.19'")
            return []
        
        # Transform numerical input to JIRA format
        jira_fix_version = transform_fix_version(fix_version)
        query_parts.append(f'fixVersion = "{jira_fix_version}"')
        search_descriptions.append(f"fix version: {fix_version} (JIRA: {jira_fix_version})")
    
    if status:
        if not validate_status(status):
            print(f"❌ Error: Invalid status '{status}'. Allowed statuses: {', '.join(ALLOWED_STATUSES)}")
            return []
        
        query_parts.append(f'status = "{status}"')
        search_descriptions.append(f"status: {status}")
    
    if query_parts:
        search_query = f'{base_query} AND {" AND ".join(query_parts)}'
        search_type = " AND ".join(search_descriptions)
    else:
        # Default fallback
        default_label = "ODF-4.19-candidate"
        search_query = f'{base_query} AND labels = "{default_label}"'
        search_type = f"default label: {default_label}"
    
    try:
        print(f"🔍 Searching for epics with {search_type}")
        print(f"📝 Query: {search_query}")
        print("-" * 60)
        
        issues = jira.search_issues(search_query, maxResults=max_results)
        return issues
    except Exception as e:
        print(f"❌ Error searching for epics: {e}")
        return []


def print_epic_details(issues, show_count=True):
    """Print details of epic issues"""
    if not issues:
        print("No epics found with the specified criteria.")
        return
    
    if show_count:
        print(f"📋 Found {len(issues)} epic(s):")
    print("=" * 80)
    
    for i, issue in enumerate(issues, 1):
        print(f"\n{i}. Epic: {issue.key}")
        print(f"   Title: {issue.fields.summary}")
        print(f"   Status: {issue.fields.status}")
        print(f"   Assignee: {getattr(issue.fields.assignee, 'displayName', 'Unassigned')}")
        print(f"   Labels: {', '.join(issue.fields.labels) if issue.fields.labels else 'None'}")
        print(f"   Link: {issue.permalink()}")
        
        # Print fix versions if available
        if issue.fields.fixVersions:
            versions = [version.name for version in issue.fields.fixVersions]
            print(f"   Fix Versions: {', '.join(versions)}")
        
        print("-" * 60)


def print_detailed_help():
    """Print detailed help information"""
    help_text = f"""
{'='*80}
RHSTOR Epic Fetcher v{__version__}
{'='*80}

DESCRIPTION:
    A command-line tool to fetch and display Red Hat Storage (RHSTOR) epics 
    from JIRA based on labels, fix versions, and/or status with summary capabilities.

SETUP:
    1. Set your JIRA API token:
       export JIRA_API_TOKEN='your-jira-api-token-here'
    
    2. Get your token from: https://issues.redhat.com
       → Account Settings → Security → API Tokens

USAGE PATTERNS:

    1. Search by Label Only:
       python3 view.py --label "ODF-4.19-candidate"
       python3 view.py -l "QE-Needed"
    
    2. Search by Fix Version Only (Numerical Input):
       python3 view.py --fix-version "4.19.0"    # Queries "ODF v4.19.0.0" 
       python3 view.py -f "4.19"                 # Queries "ODF v4.19.0"
    
    3. Search by Status Only:
       python3 view.py --status "In Progress"
       python3 view.py -s "ON_QA"
    
    4. Status Summary (Shows counts for all statuses):
       python3 view.py --status-summary
       python3 view.py --status-summary --label "ODF-4.19-candidate"
       python3 view.py --status-summary --fix-version "4.19"
    
    5. Status Summary + Filter (Shows counts + lists specific status):
       python3 view.py --status-summary --status "ON_QA"
       python3 view.py --status-summary -s "In Progress" -l "QE-Needed"
    
    6. Search by Multiple Criteria (AND Condition):
       python3 view.py --label "ODF-4.19-candidate" --fix-version "4.19.0"
       python3 view.py -l "QE-Needed" -f "4.19" -s "In Progress"
       python3 view.py --status "ON_QA" --fix-version "4.19"
    
    7. Backward Compatibility (Positional Argument):
       python3 view.py "ODF-4.19-candidate"
    
    8. Use Default Label:
       python3 view.py
    
    9. Limit Results:
       python3 view.py --label "ODF-4.19-candidate" --max-results 20

COMMON LABELS:
    • ODF-4.19-candidate    - Candidate for ODF 4.19 release
    • QE-Needed            - Requires QE attention
    • Dev-Preview          - Development preview features
    • no-qe-needed         - Does not require QE
    • QE-improvement       - QE process improvements

ALLOWED STATUSES:
    • To Do                - Not yet started
    • In Progress          - Currently being worked on
    • Code Review          - Under code review
    • ON_QA               - In QA testing
    • Verified            - QA verified
    • Closed              - Completed

FIX VERSION TRANSFORMATION:
    Input (Numerical)      →    JIRA Query Format
    • "4.19"              →    "ODF v4.19.0"
    • "4.19.0"            →    "ODF v4.19.0.0"
    • "4.18"              →    "ODF v4.18.0"

OUTPUT INFORMATION:
    For each epic found, the tool displays:
    • Epic Key (e.g., RHSTOR-1234)
    • Title/Summary
    • Current Status
    • Assignee
    • All Labels
    • Direct Link to JIRA issue
    • Fix Versions (if any)

TROUBLESHOOTING:
    • "JIRA_API_TOKEN not set" → Set the environment variable
    • "Failed to connect" → Check your API token and network
    • "No epics found" → Try different search criteria
    • "Invalid fix version format" → Use numerical format like "4.19.0" or "4.19"
    • "Invalid status" → Use one of the allowed statuses

EXAMPLES:
    # Find all epics for version 4.19 (queries "ODF v4.19.0")
    python3 view.py --fix-version "4.19"
    
    # Show status summary for all epics
    python3 view.py --status-summary
    
    # Show status summary for specific label
    python3 view.py --status-summary --label "ODF-4.19-candidate"
    
    # Show status summary + list only ON_QA epics
    python3 view.py --status-summary --status "ON_QA"
    
    # Find candidate epics that need QE attention
    python3 view.py --label "ODF-4.19-candidate"
    
    # Find epics currently in QA testing
    python3 view.py --status "ON_QA"
    
    # Find specific candidates for version 4.19 that are in progress
    python3 view.py -l "ODF-4.19-candidate" -f "4.19" -s "In Progress"
    
    # Find all closed epics for version 4.19 with summary
    python3 view.py --status-summary --fix-version "4.19" --status "Closed"
    
    # Quick search with positional argument
    python3 view.py "QE-Needed"

STATUS SUMMARY OUTPUT:
    When using --status-summary, you'll see:
    
    📊 Epic Status Summary:
    ============================================================
      To Do           :   5 epics ( 12.5%)
      In Progress     :  10 epics ( 25.0%)
      Code Review     :   3 epics (  7.5%)
    ➤ ON_QA           :   8 epics ( 20.0%) ← FILTERED
      Verified        :   6 epics ( 15.0%)
      Closed          :   8 epics ( 20.0%)
    
      Total           :  40 epics

AUTHOR: {__author__} <{__email__}>
VERSION: {__version__}
JIRA SERVER: {server}
{'='*80}
"""
    print(help_text)


def main():
    """Main function"""
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Fetch and display RHSTOR epics by label, fix version, and/or status with summary capabilities',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
EXAMPLES:
  %(prog)s --label "ODF-4.19-candidate"                          # Search by label only
  %(prog)s --fix-version "4.19"                                  # Search by fix version (becomes "ODF v4.19.0")
  %(prog)s --status "In Progress"                                # Search by status only
  %(prog)s --status-summary                                      # Show status counts for all epics
  %(prog)s --status-summary --label "ODF-4.19-candidate"        # Show status counts for specific label
  %(prog)s --status-summary --status "ON_QA"                    # Show status counts + list ON_QA epics
  %(prog)s --label "ODF-4.19-candidate" --fix-version "4.19"    # Search by label and version
  %(prog)s -l "QE-Needed" -f "4.19" -s "ON_QA"                  # Search by all three criteria
  %(prog)s "ODF-4.19-candidate"                                  # Positional argument (label)
  %(prog)s                                                       # Use default label
  %(prog)s --detailed-help                                       # Show comprehensive help

ALLOWED STATUSES: {', '.join(f'"{s}"' for s in ALLOWED_STATUSES)}

AUTHOR: {__author__} <{__email__}>
VERSION: {__version__}

NOTE: Fix versions are automatically transformed: "4.19" → "ODF v4.19.0"
For comprehensive help with examples and setup instructions, use: --detailed-help
        """
    )
    
    parser.add_argument(
        'search_term', 
        nargs='?', 
        help='Label to search for (positional argument, treated as label)'
    )
    parser.add_argument(
        '--label', '-l',
        help='Search for epics with this specific label'
    )
    parser.add_argument(
        '--fix-version', '-f',
        help='Search for epics with this numerical fix version (auto-converted to "ODF v{version}.0")'
    )
    parser.add_argument(
        '--status', '-s',
        help=f'Search for epics with this status. Allowed: {", ".join(ALLOWED_STATUSES)}'
    )
    parser.add_argument(
        '--status-summary',
        action='store_true',
        help='Show summary of epic counts by status (can be combined with other filters)'
    )
    parser.add_argument(
        '--max-results', '-m',
        type=int,
        default=100,
        help='Maximum number of results to return (default: 100, summary uses 1000)'
    )
    parser.add_argument(
        '--version', '-V',
        action='version',
        version=f'RHSTOR Epic Fetcher v{__version__} by {__author__}'
    )
    parser.add_argument(
        '--detailed-help',
        action='store_true',
        help='Show detailed help with comprehensive examples and setup instructions'
    )
    
    args = parser.parse_args()
    
    # Handle detailed help
    if args.detailed_help:
        print_detailed_help()
        return
    
    # Determine search criteria
    label = None
    fix_version = None
    status = None
    
    if args.label:
        label = args.label
    elif args.search_term:
        # Treat positional argument as label for backward compatibility
        label = args.search_term
    
    if args.fix_version:
        fix_version = args.fix_version
    
    if args.status:
        status = args.status
    
    # Display header
    print(f"🚀 RHSTOR Epic Fetcher v{__version__}")
    
    search_criteria = []
    if label:
        search_criteria.append(f"🏷️  Label: {label}")
    if fix_version:
        jira_version = transform_fix_version(fix_version)
        search_criteria.append(f"🔧 Fix Version: {fix_version} (JIRA: {jira_version})")
    if status:
        search_criteria.append(f"📊 Status: {status}")
    if args.status_summary:
        search_criteria.append("📈 Mode: Status Summary")
    
    if search_criteria:
        print("Search criteria:")
        for criterion in search_criteria:
            print(f"  {criterion}")
    else:
        print(f"🏷️  Using default search criteria")
    
    print("=" * 80)
    
    # Connect to JIRA
    jira = connect_to_jira()
    if not jira:
        return
    
    # Handle status summary
    if args.status_summary:
        print("Fetching epics for status summary...")
        summary_issues = fetch_epics_for_status_summary(jira, label=label, fix_version=fix_version, max_results=1000)
        print_status_summary(summary_issues, target_status=status)
        
        # If status is specified, also show the filtered list
        if status:
            print(f"\n📋 Epics with status '{status}':")
            print("=" * 80)
            filtered_issues = [issue for issue in summary_issues if str(issue.fields.status) == status]
            print_epic_details(filtered_issues, show_count=False)
        
        print(f"\n✅ Status summary completed!")
    else:
        # Regular search
        epics = fetch_epics_by_criteria(jira, label=label, fix_version=fix_version, status=status, max_results=args.max_results)
        print_epic_details(epics)
        print(f"\n✅ Search completed!")


if __name__ == '__main__':
    main() 