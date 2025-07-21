#!/usr/bin/env python3
"""
RHSTOR Story Creator
Creates stories for RHSTOR epics and links them appropriately
"""

import argparse
import os
import re
import sys
from collections import Counter
from jira import JIRA
from datetime import datetime

# Version information
__version__ = "1.0.0"
__author__ = "Mudit Agarwal"
__email__ = "muditag85@gmail.com"

# JIRA Configuration
server = 'https://issues.redhat.com'

# Allowed JIRA statuses
ALLOWED_STATUSES = [
    "To Do",
    "In Progress", 
    "Code Review",
    "ON_QA",
    "Verified",
    "Closed"
]

# Default story templates
DEFAULT_STORY_TEMPLATES = [
    {
        "summary": "KCS story for {epic_key}",
        "description": "For a dev preview epic, we need to add a KCS article.\nPlease use the following link to create a KCS and reach out to Lijo to publish the same.\n\nhttps://access.redhat.com/node/add/kcs-solution\n\n*Related Epic:* {epic_key}\n*Epic Summary:* {epic_summary}",
        "story_points": 3
    },
    {
        "summary": "Happy Path Validation Story for {epic_key}",
        "description": "Happy Path Validation:\n\n1) The epic should be moved to ON_QA only if the happy path validation steps are provided. Please add the steps.\n\n2) Make sure that the steps are clear and easy to follow.\n\n3) Steps must be tested on a downstream setup.\n\n*Related Epic:* {epic_key}\n*Epic Summary:* {epic_summary}",
        "story_points": 5
    }
]

def validate_fix_version(version):
    """Validate fix version format"""
    if not version:
        return True
    pattern = r'^\d+\.\d+(?:\.\d+)?$'
    return bool(re.match(pattern, version))

def transform_fix_version(fix_version):
    """Transform numerical fix version to JIRA format"""
    if not fix_version:
        return None
    return f"ODF v{fix_version}.0"

def validate_status(status):
    """Validate status"""
    return status in ALLOWED_STATUSES

def fetch_epics_by_criteria(jira, label=None, fix_version=None, status=None, max_results=100):
    """Fetch epics by specific criteria"""
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

def check_existing_stories(jira, epic):
    """Check if KCS or Happy Path stories already exist for this epic"""
    try:
        # Search for stories linked to this epic with our specific labels OR keywords in summary
        # Case-insensitive search for "kcs" in summary OR label "kcs"
        kcs_query = f'project = RHSTOR AND issuetype = Story AND "Epic Link" = {epic.key} AND (labels = "kcs" OR summary ~ "kcs")'
        
        # Case-insensitive search for "happy" in summary OR label "happy-path"  
        happy_query = f'project = RHSTOR AND issuetype = Story AND "Epic Link" = {epic.key} AND (labels = "happy-path" OR summary ~ "happy")'
        
        kcs_stories = jira.search_issues(kcs_query, maxResults=10)
        happy_stories = jira.search_issues(happy_query, maxResults=10)
        
        return {
            'kcs': kcs_stories,
            'happy': happy_stories,
            'has_kcs': len(kcs_stories) > 0,
            'has_happy': len(happy_stories) > 0
        }
    except Exception as e:
        print(f"   ⚠️ Warning: Could not check existing stories: {e}")
        return {
            'kcs': [],
            'happy': [],
            'has_kcs': False,
            'has_happy': False
        }

def find_epic_link_field(jira, debug=False):
    """Find the Epic Link field in JIRA"""
    try:
        all_fields = jira.fields()
        
        # Look for Epic Link field by name
        for field in all_fields:
            field_name_lower = field['name'].lower()
            if field_name_lower == 'epic link' or field_name_lower == 'epic name':
                if debug:
                    print(f"   🔍 Found Epic Link field: {field['name']} ({field['id']})")
                return field['id']
        
        # If not found by exact name, look for fields containing 'epic'
        for field in all_fields:
            if 'epic' in field['name'].lower() and 'link' in field['name'].lower():
                if debug:
                    print(f"   🔍 Found potential Epic Link field: {field['name']} ({field['id']})")
                return field['id']
                
        return None
        
    except Exception as e:
        if debug:
            print(f"   ❌ Error finding Epic Link field: {e}")
        return None

def create_story(jira, epic, template, project_key="RHSTOR", debug=False):
    """Create a story for an epic"""
    try:
        # Format template with epic information
        story_summary = template["summary"].format(
            epic_key=epic.key,
            epic_summary=epic.fields.summary
        )
        story_description = template["description"].format(
            epic_key=epic.key,
            epic_summary=epic.fields.summary
        )
        
        # Determine story label based on template type
        if "KCS story for" in template["summary"]:
            story_label = "kcs"
        elif "Happy Path Validation Story for" in template["summary"]:
            story_label = "happy-path"
        else:
            story_label = None
        
        # Prepare story fields
        story_fields = {
            'project': {'key': project_key},
            'summary': story_summary,
            'description': story_description,
            'issuetype': {'name': 'Story'},
        }
        
        # Add story type label
        if story_label:
            story_fields['labels'] = [story_label]
        
        # Add story points if available (skip for now to avoid field errors)
        # Story points field varies by JIRA instance and may not be configured
        # if "story_points" in template and template["story_points"]:
        #     story_fields['customfield_10002'] = template["story_points"]
        
        # Set assignee if epic has one
        if epic.fields.assignee:
            story_fields['assignee'] = {'name': epic.fields.assignee.name}
        
        # Try to add Epic Link field during creation (most reliable method)
        epic_link_field = find_epic_link_field(jira, debug)
        epic_link_added_during_creation = False
        
        if epic_link_field:
            try:
                story_fields[epic_link_field] = epic.key
                epic_link_added_during_creation = True
                if debug:
                    print(f"   🔗 Adding Epic Link during creation: {epic_link_field} = {epic.key}")
            except Exception as e:
                if debug:
                    print(f"   ⚠️ Could not add Epic Link during creation: {e}")
        
        # Debug: Print story fields being sent to JIRA (only in debug mode)
        if debug:
            print(f"   🔧 Debug: Creating story with fields: {story_fields}")
        
        # Create the story
        story = jira.create_issue(fields=story_fields)
        print(f"   ✅ Story created successfully: {story.key}")
        
        # Link story to epic - try multiple methods (skip if already linked during creation)
        if epic_link_added_during_creation:
            print(f"   🔗 Epic Link already set during creation")
            linked = True
        else:
            linked = False
            if debug:
                print(f"   🔗 Attempting to link story {story.key} to epic {epic.key} (post-creation)")
            
            # Method 2: Find and use the correct Epic Link field
            try:
                # Get all custom fields to find the Epic Link field
                all_fields = jira.fields()
                epic_link_field = None
                
                for field in all_fields:
                    if field['name'].lower() == 'epic link' or 'epic' in field['name'].lower():
                        epic_link_field = field['id']
                        if debug:
                            print(f"   🔍 Found Epic Link field: {field['name']} ({field['id']})")
                        break
                
                if epic_link_field:
                    story.update(fields={epic_link_field: epic.key})
                    print(f"   🔗 Linked to epic using field {epic_link_field}")
                    linked = True
                else:
                    if debug:
                        print(f"   ⚠️ Epic Link field not found in available fields")
                    
            except Exception as field_error:
                if debug:
                    print(f"   ❌ Method 2 failed: {field_error}")
            
            # Method 3: Try common epic link field names if Method 2 failed
            if not linked:
                try:
                    epic_link_fields = ['customfield_10001', 'customfield_10008', 'customfield_10014', 'customfield_10002']
                    
                    for field_name in epic_link_fields:
                        try:
                            story.update(fields={field_name: epic.key})
                            print(f"   🔗 Linked to epic using {field_name}")
                            linked = True
                            break
                        except Exception as e:
                            if debug:
                                print(f"   ❌ Failed with {field_name}: {e}")
                            continue
                            
                except Exception as method3_error:
                    if debug:
                        print(f"   ❌ Method 3 failed: {method3_error}")
            
            # Method 4: Try creating an issue link as fallback
            if not linked:
                try:
                    # Get available link types
                    link_types = jira.issue_link_types()
                    epic_link_type = None
                    
                    for link_type in link_types:
                        if 'epic' in link_type.name.lower():
                            epic_link_type = link_type.name
                            break
                    
                    if not epic_link_type:
                        epic_link_type = "Relates"  # Generic fallback
                    
                    jira.create_issue_link(
                        type=epic_link_type,
                        inwardIssue=story.key,
                        outwardIssue=epic.key,
                        comment={
                            "body": f"Story {story.key} created for epic {epic.key}"
                        }
                    )
                    print(f"   🔗 Linked to epic using issue link type '{epic_link_type}'")
                    linked = True
                    
                except Exception as link_error:
                    if debug:
                        print(f"   ❌ Method 4 failed: {link_error}")
        
        if not linked:
            print(f"   ⚠️ Warning: Could not link story to epic automatically")
            print(f"   💡 Manual action required: Set Epic Link for {story.key} to {epic.key}")
            print(f"   📝 Story URL: {story.permalink()}")
            print(f"   📝 Epic URL: {epic.permalink()}")
        
        return story
        
    except Exception as e:
        print(f"   ❌ Error creating story:")
        print(f"       Error type: {type(e).__name__}")
        print(f"       Error message: {str(e)}")
        
        # Try to extract more details from JIRA error
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"       JIRA response: {e.response.text}")
        
        if hasattr(e, 'text'):
            print(f"       Additional details: {e.text}")
            
        print(f"   🔧 Story fields that failed: {story_fields}")
        return None

def create_stories_for_epics(jira, epics, story_templates=None, dry_run=False, auto_mode=False, debug=False):
    """Create stories for a list of epics"""
    if not epics:
        print("📭 No epics found to create stories for.")
        return
    
    print(f"📋 Found {len(epics)} epic(s) to create stories for:")
    if auto_mode:
        print("🤖 Auto mode: Creating KCS stories for 'dev-preview' epics, Happy Path stories for others")
    print("=" * 80)
    
    total_stories_created = 0
    dev_preview_count = 0
    regular_count = 0
    
    for i, epic in enumerate(epics, 1):
        assignee = getattr(epic.fields.assignee, 'displayName', 'Unassigned')
        status = str(epic.fields.status)
        labels = epic.fields.labels if epic.fields.labels else []
        
        print(f"\n{i}. Epic: {epic.key}")
        print(f"   Title: {epic.fields.summary}")
        print(f"   Status: {status}")
        print(f"   Assignee: {assignee}")
        print(f"   Labels: {', '.join(labels) if labels else 'None'}")
        
        # Check for existing stories
        existing_stories = check_existing_stories(jira, epic)
        
        # Determine which stories to create
        if auto_mode:
            if "dev-preview" in labels:
                if existing_stories['has_kcs']:
                    existing_story = existing_stories['kcs'][0]
                    print(f"   ✅ KCS story already exists: {existing_story.key} - \"{existing_story.fields.summary}\"")
                    epic_templates = []  # Skip creation
                    story_type = "KCS story (already exists)"
                else:
                    epic_templates = [DEFAULT_STORY_TEMPLATES[0]]  # KCS story only
                    story_type = "KCS story (dev-preview epic)"
                dev_preview_count += 1
            else:
                if existing_stories['has_happy']:
                    existing_story = existing_stories['happy'][0]
                    print(f"   ✅ Happy Path story already exists: {existing_story.key} - \"{existing_story.fields.summary}\"")
                    epic_templates = []  # Skip creation
                    story_type = "Happy Path story (already exists)"
                else:
                    epic_templates = [DEFAULT_STORY_TEMPLATES[1]]  # Happy Path story only
                    story_type = "Happy Path story (regular epic)"
                regular_count += 1
            print(f"   🎯 Auto-selected: {story_type}")
        else:
            # For manual template selection, filter out existing story types
            epic_templates = []
            for template in (story_templates or DEFAULT_STORY_TEMPLATES):
                if "KCS story for" in template["summary"] and existing_stories['has_kcs']:
                    existing_story = existing_stories['kcs'][0]
                    print(f"   ✅ KCS story already exists: {existing_story.key} - \"{existing_story.fields.summary}\"")
                    continue
                elif "Happy Path Validation Story for" in template["summary"] and existing_stories['has_happy']:
                    existing_story = existing_stories['happy'][0]
                    print(f"   ✅ Happy Path story already exists: {existing_story.key} - \"{existing_story.fields.summary}\"")
                    continue
                else:
                    epic_templates.append(template)
        
        if len(epic_templates) == 0:
            print(f"   ⏭️ No new stories to create for this epic")
        elif dry_run:
            print(f"   🔍 DRY RUN: Would create {len(epic_templates)} stories:")
            for j, template in enumerate(epic_templates, 1):
                story_summary = template["summary"].format(
                    epic_key=epic.key,
                    epic_summary=epic.fields.summary
                )
                print(f"      {j}. {story_summary}")
        else:
            print(f"   📝 Creating {len(epic_templates)} stories...")
            epic_stories_created = 0
            
            for j, template in enumerate(epic_templates, 1):
                story = create_story(jira, epic, template, debug=debug)
                if story:
                    print(f"      ✅ {j}. Created story: {story.key}")
                    epic_stories_created += 1
                else:
                    print(f"      ❌ {j}. Failed to create story")
            
            total_stories_created += epic_stories_created
            if epic_stories_created > 0:
                print(f"   📊 Created {epic_stories_created}/{len(epic_templates)} stories for this epic")
            else:
                print(f"   📊 No new stories created for this epic")
        
        print("-" * 60)
    
    if auto_mode:
        if dry_run:
            print(f"\n🤖 AUTO MODE DRY RUN SUMMARY:")
            print(f"   📋 {dev_preview_count} dev-preview epics processed")
            print(f"   📋 {regular_count} regular epics processed")
            
            # Calculate how many epics actually need new stories
            print(f"   🔍 Checking existing stories to calculate accurate counts...")
            epics_needing_kcs = 0
            epics_needing_happy = 0
            
            for epic in epics:
                labels = epic.fields.labels if epic.fields.labels else []
                existing = check_existing_stories(jira, epic)
                
                if "dev-preview" in labels and not existing['has_kcs']:
                    epics_needing_kcs += 1
                elif "dev-preview" not in labels and not existing['has_happy']:
                    epics_needing_happy += 1
            
            total_new_stories = epics_needing_kcs + epics_needing_happy
            print(f"   ✨ Epics that would get new KCS stories: {epics_needing_kcs}")
            print(f"   ✨ Epics that would get new Happy Path stories: {epics_needing_happy}")
            print(f"   📈 Total new stories that would be created: {total_new_stories}")
            
            if total_new_stories == 0:
                print(f"   ℹ️ All epics already have the required stories - no new stories needed!")
            elif total_new_stories < len(epics):
                skipped = len(epics) - total_new_stories
                print(f"   ⏭️ {skipped} epics already have required stories and would be skipped")
        else:
            print(f"\n🤖 AUTO MODE SUMMARY:")
            print(f"   📋 {dev_preview_count} dev-preview epics processed")
            print(f"   📋 {regular_count} regular epics processed")
            print(f"   📊 Total: {total_stories_created} new stories created for {len(epics)} epics")
            if total_stories_created < len(epics):
                print(f"   ℹ️ Some epics already had the required stories")
    else:
        if dry_run:
            print(f"\n🔍 DRY RUN SUMMARY:")
            
            # Calculate how many stories would actually be created
            print(f"   🔍 Checking existing stories to calculate accurate counts...")
            epics_needing_stories = 0
            total_stories_to_create = 0
            
            for epic in epics:
                existing = check_existing_stories(jira, epic)
                epic_needs_stories = False
                
                for template in (story_templates or DEFAULT_STORY_TEMPLATES):
                    if "KCS story for" in template["summary"] and not existing['has_kcs']:
                        total_stories_to_create += 1
                        epic_needs_stories = True
                    elif "Happy Path Validation Story for" in template["summary"] and not existing['has_happy']:
                        total_stories_to_create += 1
                        epic_needs_stories = True
                
                if epic_needs_stories:
                    epics_needing_stories += 1
            
            print(f"   📋 Total epics found: {len(epics)}")
            print(f"   ✨ Epics that would get new stories: {epics_needing_stories}")
            print(f"   📈 Total new stories that would be created: {total_stories_to_create}")
            
            if total_stories_to_create == 0:
                print(f"   ℹ️ All epics already have the required story types - no new stories needed!")
            elif epics_needing_stories < len(epics):
                skipped = len(epics) - epics_needing_stories
                print(f"   ⏭️ {skipped} epics already have required stories and would be skipped")
        else:
            print(f"\n📊 SUMMARY: Created {total_stories_created} new stories for {len(epics)} epics")
            if total_stories_created == 0:
                print(f"   ℹ️ All epics already had the required stories")

def show_detailed_help():
    """Show comprehensive help"""
    help_text = f"""
RHSTOR Story Creator v{__version__}
===================================

DESCRIPTION:
    Creates JIRA stories for RHSTOR epics and links them appropriately.
    Each epic can have multiple stories created using predefined templates.

USAGE:
    python3 stories.py [OPTIONS]

OPTIONS:
    -l, --label LABEL           Filter epics by specific label (e.g., "ODF-4.19-candidate")
    -f, --fix-version VERSION   Filter by numerical fix version (e.g., "4.19", "4.19.0")
    -s, --status STATUS         Filter by epic status
    -m, --max-results N         Maximum number of epics to process (default: 20)
    -t, --templates TYPE        Story template type: default, dev, test, docs, custom
    -n, --dry-run              Show what would be created without actually creating
    -V, --version              Show version information
    -h, --help                 Show basic help
    --detailed-help            Show this detailed help

 STORY TEMPLATES:
     auto:    Smart mode - KCS stories for 'dev-preview' epics, Happy Path for others (default)
     default: Creates KCS + Happy Path stories (both)
     kcs:     Creates only KCS story (Knowledge Center Solution article)
     happy:   Creates only Happy Path validation story
     custom:  Prompts for custom story details

 EXAMPLES:
     # Auto mode - creates appropriate stories based on labels (default behavior)
     python3 stories.py --label "ODF-4.19-candidate"
     
     # Create stories for epics in specific version and status
     python3 stories.py --fix-version "4.19" --status "In Progress"
     
     # Dry run to see what would be created with auto mode
     python3 stories.py --label "ODF-4.19-candidate" --dry-run
     
     # Force create only KCS stories for all epics
     python3 stories.py --label "ODF-4.19-candidate" --templates kcs
     
     # Create both story types for all epics
     python3 stories.py --fix-version "4.19" --templates default
     
     # Limit to 5 epics with auto mode
     python3 stories.py --fix-version "4.19" --max-results 5

 STORY DETAILS:
     KCS Story:
     - Instructions for creating Knowledge Center Solution article
     - Link to KCS creation portal
     - Contact info for publishing (Lijo)
     - Labeled with "kcs"
     
     Happy Path Story:
     - Validation requirements for moving epic to ON_QA
     - Guidelines for clear and testable steps
     - Downstream testing requirements
     - Labeled with "happy-path"
     
     Both stories include:
     - Assignee copied from epic
     - Link to parent epic
     - Story type identification label

SETUP:
    1. Set JIRA API token: export JIRA_API_TOKEN='your-token-here'
    2. Get token from: https://issues.redhat.com
       → Account Settings → Security → API Tokens

 DUPLICATE PREVENTION:
     - Automatically checks for existing KCS and Happy Path stories
     - Detects by label ("kcs", "happy-path") OR by keywords in summary ("kcs", "happy")
     - Case-insensitive keyword matching in story summaries
     - Skips creation if appropriate story already exists for the epic
     - Reports existing story keys for reference

 SECURITY:
     - Uses environment variables for secure token storage
     - Dry-run mode available for safe testing
     - Confirmation prompts for bulk operations

Author: {__author__} <{__email__}>
JIRA Server: {server}
"""
    print(help_text)

def get_story_templates(template_type):
    """Get story templates based on type"""
    if template_type == "default":
        return DEFAULT_STORY_TEMPLATES
    elif template_type == "auto":
        return None  # Auto mode will determine templates per epic
    elif template_type == "kcs":
        return [DEFAULT_STORY_TEMPLATES[0]]  # KCS story only
    elif template_type == "happy":
        return [DEFAULT_STORY_TEMPLATES[1]]  # Happy path story only
    elif template_type == "custom":
        # For custom, we'll prompt the user
        return get_custom_templates()
    else:
        print(f"❌ Unknown template type: {template_type}")
        return DEFAULT_STORY_TEMPLATES

def get_custom_templates():
    """Get custom story templates from user input"""
    print("\n📝 Custom Story Template Creation")
    print("=" * 40)
    
    templates = []
    while True:
        print(f"\nCreating template #{len(templates) + 1}:")
        
        summary = input("Story summary template (use {epic_key} and {epic_summary}): ").strip()
        if not summary:
            break
            
        description = input("Story description template: ").strip()
        if not description:
            description = f"Work related to epic {{epic_key}}: {{epic_summary}}"
        
        try:
            story_points = input("Story points (or press Enter to skip): ").strip()
            story_points = int(story_points) if story_points else None
        except ValueError:
            story_points = None
        
        templates.append({
            "summary": summary,
            "description": description,
            "story_points": story_points
        })
        
        another = input("Add another template? (y/N): ").strip().lower()
        if another not in ['y', 'yes']:
            break
    
    return templates if templates else DEFAULT_STORY_TEMPLATES

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description=f"RHSTOR Story Creator v{__version__} - Create stories for RHSTOR epics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 Examples:
   python3 stories.py --label "ODF-4.19-candidate"  # Auto mode
   python3 stories.py --fix-version "4.19" --status "In Progress" --dry-run
   python3 stories.py --label "ODF-4.19-candidate" --templates kcs
        """
    )
    
    parser.add_argument('-l', '--label', 
                       help='Filter epics by specific label (e.g., "ODF-4.19-candidate")')
    parser.add_argument('-f', '--fix-version', 
                       help='Filter by numerical fix version (e.g., "4.19", "4.19.0")')
    parser.add_argument('-s', '--status', choices=ALLOWED_STATUSES,
                       help='Filter by epic status')
    parser.add_argument('-m', '--max-results', type=int, default=20,
                       help='Maximum number of epics to process (default: 20)')
    parser.add_argument('-t', '--templates', default='auto',
                       choices=['auto', 'default', 'kcs', 'happy', 'custom'],
                       help='Story template type (default: auto)')
    parser.add_argument('-n', '--dry-run', action='store_true',
                       help='Show what would be created without actually creating')
    parser.add_argument('-V', '--version', action='version', 
                       version=f'RHSTOR Story Creator v{__version__}')
    parser.add_argument('--detailed-help', action='store_true',
                       help='Show detailed help with examples')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode with verbose output')
    
    args = parser.parse_args()
    
    if args.detailed_help:
        show_detailed_help()
        return
    
    # Check for API token
    api_token = os.getenv('JIRA_API_TOKEN')
    if not api_token:
        print("❌ JIRA_API_TOKEN environment variable not set!")
        print("   Please set it using: export JIRA_API_TOKEN='your-token-here'")
        print("   Get your token from: https://issues.redhat.com")
        print("   → Account Settings → Security → API Tokens")
        sys.exit(1)
    
    print(f"🚀 RHSTOR Story Creator v{__version__}")
    print(f"📧 Author: {__author__} <{__email__}>")
    print(f"🌐 JIRA Server: {server}")
    print()
    
    # Connect to JIRA
    try:
        print("🔗 Connecting to JIRA...")
        jira = JIRA(server=server, token_auth=api_token)
        print("✅ Connected to JIRA successfully")
        
        # Test basic JIRA operations if debug mode
        if args.debug:
            print("\n🔧 Debug mode: Testing JIRA operations...")
            try:
                # Test project access
                project = jira.project("RHSTOR")
                print(f"   ✅ Can access RHSTOR project: {project.name}")
                
                # Test issue type access
                issue_types = jira.issue_types()
                story_type = None
                for it in issue_types:
                    if it.name.lower() == 'story':
                        story_type = it
                        break
                
                if story_type:
                    print(f"   ✅ Story issue type available: {story_type.name}")
                else:
                    print(f"   ⚠️ Story issue type not found in available types: {[it.name for it in issue_types]}")
                    
            except Exception as test_error:
                print(f"   ❌ JIRA access test failed: {test_error}")
                print(f"   💡 This may indicate permission or configuration issues")
                
    except Exception as e:
        print(f"❌ Failed to connect to JIRA: {e}")
        sys.exit(1)
    
    # Get story templates and check for auto mode
    auto_mode = args.templates == "auto"
    story_templates = get_story_templates(args.templates)
    
    if auto_mode:
        print("\n🤖 Auto Mode: Will create KCS stories for 'dev-preview' epics, Happy Path stories for others")
    elif not story_templates:
        print("❌ No story templates defined!")
        sys.exit(1)
    else:
        print(f"\n📋 Using {len(story_templates)} story template(s):")
        for i, template in enumerate(story_templates, 1):
            points_info = f" ({template.get('story_points', 'no')} points)" if template.get('story_points') else ""
            print(f"   {i}. {template['summary']}{points_info}")
    
    # Fetch epics
    epics = fetch_epics_by_criteria(
        jira, 
        label=args.label,
        fix_version=args.fix_version, 
        status=args.status,
        max_results=args.max_results
    )
    
    if not epics:
        print("📭 No epics found matching the criteria.")
        return
    
    # Debug mode: Show epic analysis
    if args.debug:
        print(f"\n🔧 Debug: Epic Analysis")
        print(f"   📊 Total epics found: {len(epics)}")
        
        if auto_mode:
            dev_preview_epics = []
            regular_epics = []
            
            for epic in epics:
                labels = epic.fields.labels if epic.fields.labels else []
                if "dev-preview" in labels:
                    dev_preview_epics.append(epic)
                else:
                    regular_epics.append(epic)
            
            print(f"   🏷️ Dev-preview epics: {len(dev_preview_epics)} (will get KCS stories)")
            print(f"   🏷️ Regular epics: {len(regular_epics)} (will get Happy Path stories)")
            
            # Check existing stories for accurate count
            epics_needing_kcs = 0
            epics_needing_happy = 0
            
            print(f"   🔍 Checking for existing stories...")
            for epic in dev_preview_epics:
                existing = check_existing_stories(jira, epic)
                if not existing['has_kcs']:
                    epics_needing_kcs += 1
            
            for epic in regular_epics:
                existing = check_existing_stories(jira, epic)
                if not existing['has_happy']:
                    epics_needing_happy += 1
            
            total_new_stories = epics_needing_kcs + epics_needing_happy
            print(f"   ✨ Epics needing new KCS stories: {epics_needing_kcs}")
            print(f"   ✨ Epics needing new Happy Path stories: {epics_needing_happy}")
            print(f"   📈 Total new stories to create: {total_new_stories}")
            
            if total_new_stories == 0:
                print(f"   ℹ️ All epics already have the required stories!")
            
        else:
            # Manual template mode
            selected_templates = story_templates or DEFAULT_STORY_TEMPLATES
            print(f"   📋 Templates selected: {len(selected_templates)}")
            
            epics_needing_stories = 0
            total_stories_to_create = 0
            
            print(f"   🔍 Checking existing stories for manual template mode...")
            for epic in epics:
                existing = check_existing_stories(jira, epic)
                epic_needs_stories = False
                
                for template in selected_templates:
                    if "KCS story for" in template["summary"] and not existing['has_kcs']:
                        total_stories_to_create += 1
                        epic_needs_stories = True
                    elif "Happy Path Validation Story for" in template["summary"] and not existing['has_happy']:
                        total_stories_to_create += 1
                        epic_needs_stories = True
                
                if epic_needs_stories:
                    epics_needing_stories += 1
            
            print(f"   ✨ Epics needing new stories: {epics_needing_stories}")
            print(f"   📈 Total new stories to create: {total_stories_to_create}")
            
            if total_stories_to_create == 0:
                print(f"   ℹ️ All epics already have the required story types!")
        
        print("   " + "="*50)
    
    # Confirmation for non-dry-run
    if not args.dry_run:
        if auto_mode:
            print(f"\n⚠️ Auto mode will create appropriate stories for {len(epics)} epics.")
            print("   📋 'dev-preview' epics → KCS stories")
            print("   📋 Other epics → Happy Path stories")
        else:
            total_stories = len(epics) * len(story_templates)
            print(f"\n⚠️ This will create {total_stories} stories for {len(epics)} epics.")
        
        confirm = input("Do you want to proceed? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("❌ Operation cancelled.")
            return
    
    # Create stories
    create_stories_for_epics(jira, epics, story_templates, args.dry_run, auto_mode, args.debug)
    
    if args.dry_run:
        print("\n💡 Run without --dry-run to actually create the stories.")
    else:
        print("\n✅ Story creation completed!")

if __name__ == '__main__':
    main() 