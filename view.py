#!/usr/bin/env python3
"""
RHSTOR Epic Fetcher
A simplified tool to fetch and display RHSTOR epics with specific labels
"""

from jira import JIRA
import sys
import os


# JIRA Configuration
server = 'https://issues.redhat.com'
api_token = os.getenv('JIRA_API_TOKEN')

if not api_token:
    print("❌ Error: JIRA_API_TOKEN environment variable not set!")
    print("Please set it using: export JIRA_API_TOKEN='your-token-here'")
    sys.exit(1)


def connect_to_jira():
    """Connect to JIRA instance"""
    try:
        jira = JIRA(server=server, token_auth=api_token)
        print(f"✅ Connected to JIRA: {server}")
        return jira
    except Exception as e:
        print(f"❌ Failed to connect to JIRA: {e}")
        return None


def fetch_epics_by_label(jira, label, max_results=100):
    """
    Fetch RHSTOR epics with a specific label
    
    Args:
        jira: JIRA instance
        label: Label to search for
        max_results: Maximum number of results to return
    
    Returns:
        List of epic issues
    """
    search_query = f'project = RHSTOR AND issuetype = Epic AND labels = "{label}"'
    
    try:
        print(f"🔍 Searching for epics with label: {label}")
        print(f"📝 Query: {search_query}")
        print("-" * 60)
        
        issues = jira.search_issues(search_query, maxResults=max_results)
        return issues
    except Exception as e:
        print(f"❌ Error searching for epics: {e}")
        return []


def print_epic_details(issues):
    """Print details of epic issues"""
    if not issues:
        print("No epics found with the specified label.")
        return
    
    print(f"📊 Found {len(issues)} epic(s):")
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


def main():
    """Main function"""
    # Default label to search for (can be modified)
    default_label = "ODF-4.19-candidate"
    
    # Allow label to be passed as command line argument
    if len(sys.argv) > 1:
        label_to_search = sys.argv[1]
    else:
        label_to_search = default_label
    
    print(f"🚀 RHSTOR Epic Fetcher")
    print(f"🏷️  Searching for label: {label_to_search}")
    print("=" * 80)
    
    # Connect to JIRA
    jira = connect_to_jira()
    if not jira:
        return
    
    # Fetch epics
    epics = fetch_epics_by_label(jira, label_to_search)
    
    # Print results
    print_epic_details(epics)
    
    print(f"\n✅ Search completed!")


if __name__ == '__main__':
    main() 