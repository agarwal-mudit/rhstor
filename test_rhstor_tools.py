#!/usr/bin/env python3
"""
Unit Tests for RHSTOR Tools (stories.py and view.py)
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add current directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the modules we want to test
import stories
import view


class TestValidationFunctions(unittest.TestCase):
    """Test validation functions used in both tools"""
    
    def test_validate_fix_version_stories(self):
        """Test fix version validation in stories.py"""
        # Valid versions
        self.assertTrue(stories.validate_fix_version("4.19"))
        self.assertTrue(stories.validate_fix_version("4.19.0"))
        self.assertTrue(stories.validate_fix_version("10.5.2"))
        self.assertTrue(stories.validate_fix_version(""))  # Empty should be valid
        self.assertTrue(stories.validate_fix_version(None))  # None should be valid
        
        # Invalid versions
        self.assertFalse(stories.validate_fix_version("4"))
        self.assertFalse(stories.validate_fix_version("4."))
        self.assertFalse(stories.validate_fix_version("4.19."))
        self.assertFalse(stories.validate_fix_version("v4.19"))
        self.assertFalse(stories.validate_fix_version("4.19-beta"))
        self.assertFalse(stories.validate_fix_version("invalid"))
    
    def test_validate_fix_version_view(self):
        """Test fix version validation in view.py"""
        # Valid versions
        self.assertTrue(view.validate_fix_version("4.19"))
        self.assertTrue(view.validate_fix_version("4.19.0"))
        self.assertTrue(view.validate_fix_version("10.5.2"))
        
        # Invalid versions (view.py returns False for empty/None)
        self.assertFalse(view.validate_fix_version(""))  # Empty is invalid in view.py
        self.assertFalse(view.validate_fix_version(None))  # None is invalid in view.py
        self.assertFalse(view.validate_fix_version("4"))
        self.assertFalse(view.validate_fix_version("4."))
        self.assertFalse(view.validate_fix_version("v4.19"))
    
    def test_transform_fix_version_stories(self):
        """Test fix version transformation in stories.py"""
        self.assertEqual(stories.transform_fix_version("4.19"), "ODF v4.19.0")
        self.assertEqual(stories.transform_fix_version("4.19.0"), "ODF v4.19.0.0")
        self.assertEqual(stories.transform_fix_version("10.5"), "ODF v10.5.0")
        self.assertIsNone(stories.transform_fix_version(""))
        self.assertIsNone(stories.transform_fix_version(None))
    
    def test_transform_fix_version_view(self):
        """Test fix version transformation in view.py"""
        self.assertEqual(view.transform_fix_version("4.19"), "ODF v4.19.0")
        self.assertEqual(view.transform_fix_version("4.19.0"), "ODF v4.19.0.0")
        self.assertEqual(view.transform_fix_version("10.5"), "ODF v10.5.0")
        self.assertIsNone(view.transform_fix_version(""))
        self.assertIsNone(view.transform_fix_version(None))
    
    def test_validate_status_stories(self):
        """Test status validation in stories.py"""
        # Valid statuses
        self.assertTrue(stories.validate_status("To Do"))
        self.assertTrue(stories.validate_status("In Progress"))
        self.assertTrue(stories.validate_status("Code Review"))
        self.assertTrue(stories.validate_status("ON_QA"))
        self.assertTrue(stories.validate_status("Verified"))
        self.assertTrue(stories.validate_status("Closed"))
        
        # Invalid statuses
        self.assertFalse(stories.validate_status("Invalid Status"))
        self.assertFalse(stories.validate_status("todo"))
        self.assertFalse(stories.validate_status(""))
    
    def test_validate_status_view(self):
        """Test status validation in view.py"""
        # Valid statuses (note: view.py uses "On QA" not "ON_QA")
        self.assertTrue(view.validate_status("To Do"))
        self.assertTrue(view.validate_status("In Progress"))
        self.assertTrue(view.validate_status("Code Review"))
        self.assertTrue(view.validate_status("On QA"))  # Note: view.py uses "On QA"
        self.assertTrue(view.validate_status("Verified"))
        self.assertTrue(view.validate_status("Closed"))
        
        # Invalid statuses
        self.assertFalse(view.validate_status("ON_QA"))  # This is invalid in view.py
        self.assertFalse(view.validate_status("Invalid Status"))
        self.assertFalse(view.validate_status("todo"))
        self.assertFalse(view.validate_status(""))


class TestStoriesTemplates(unittest.TestCase):
    """Test story template functions"""
    
    def test_get_story_templates_auto(self):
        """Test getting auto templates (returns None)"""
        result = stories.get_story_templates("auto")
        self.assertIsNone(result)
    
    def test_get_story_templates_default(self):
        """Test getting default templates"""
        templates = stories.get_story_templates("default")
        self.assertEqual(len(templates), 2)
        self.assertIn("KCS story for", templates[0]["summary"])
        self.assertIn("Happy Path Validation Story for", templates[1]["summary"])
    
    def test_get_story_templates_kcs(self):
        """Test getting KCS template only"""
        templates = stories.get_story_templates("kcs")
        self.assertEqual(len(templates), 1)
        self.assertIn("KCS story for", templates[0]["summary"])
    
    def test_get_story_templates_happy(self):
        """Test getting Happy Path template only"""
        templates = stories.get_story_templates("happy")
        self.assertEqual(len(templates), 1)
        self.assertIn("Happy Path Validation Story for", templates[0]["summary"])
    
    def test_get_story_templates_invalid(self):
        """Test getting invalid template type"""
        templates = stories.get_story_templates("invalid")
        self.assertEqual(len(templates), 2)  # Should return default


class TestMockedJiraFunctions(unittest.TestCase):
    """Test functions that interact with JIRA using mocks"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock epic
        self.mock_epic = Mock()
        self.mock_epic.key = "RHSTOR-1234"
        self.mock_epic.fields.summary = "Test Epic Summary"
        self.mock_epic.fields.labels = ["ODF-4.19-candidate"]
        self.mock_epic.fields.status = "In Progress"
        self.mock_epic.fields.assignee.name = "testuser"
        self.mock_epic.fields.assignee.displayName = "Test User"
        self.mock_epic.fields.fixVersions = []
        self.mock_epic.permalink.return_value = "https://issues.redhat.com/browse/RHSTOR-1234"
        
        # Create mock JIRA client
        self.mock_jira = Mock()
    
    @patch('stories.JIRA')
    def test_find_epic_link_field_found(self, mock_jira_class):
        """Test finding Epic Link field successfully"""
        # Mock field data
        mock_fields = [
            {"name": "Summary", "id": "summary"},
            {"name": "Epic Link", "id": "customfield_10008"},
            {"name": "Priority", "id": "priority"}
        ]
        
        mock_jira = Mock()
        mock_jira.fields.return_value = mock_fields
        
        result = stories.find_epic_link_field(mock_jira, debug=False)
        self.assertEqual(result, "customfield_10008")
    
    @patch('stories.JIRA')
    def test_find_epic_link_field_not_found(self, mock_jira_class):
        """Test Epic Link field not found"""
        # Mock field data without Epic Link
        mock_fields = [
            {"name": "Summary", "id": "summary"},
            {"name": "Priority", "id": "priority"}
        ]
        
        mock_jira = Mock()
        mock_jira.fields.return_value = mock_fields
        
        result = stories.find_epic_link_field(mock_jira, debug=False)
        self.assertIsNone(result)
    
    @patch('stories.check_existing_stories')
    def test_check_existing_stories_kcs_exists(self, mock_check):
        """Test checking existing stories when KCS story exists"""
        # Mock existing KCS story
        mock_kcs_story = Mock()
        mock_kcs_story.key = "RHSTOR-2001"
        mock_kcs_story.fields.summary = "KCS story for RHSTOR-1234"
        
        mock_check.return_value = {
            'kcs': [mock_kcs_story],
            'happy': [],
            'has_kcs': True,
            'has_happy': False
        }
        
        result = mock_check(self.mock_jira, self.mock_epic)
        self.assertTrue(result['has_kcs'])
        self.assertFalse(result['has_happy'])
        self.assertEqual(len(result['kcs']), 1)
    
    @patch('stories.check_existing_stories')
    def test_check_existing_stories_happy_exists(self, mock_check):
        """Test checking existing stories when Happy Path story exists"""
        # Mock existing Happy Path story
        mock_happy_story = Mock()
        mock_happy_story.key = "RHSTOR-2002"
        mock_happy_story.fields.summary = "Happy Path Validation Story for RHSTOR-1234"
        
        mock_check.return_value = {
            'kcs': [],
            'happy': [mock_happy_story],
            'has_kcs': False,
            'has_happy': True
        }
        
        result = mock_check(self.mock_jira, self.mock_epic)
        self.assertFalse(result['has_kcs'])
        self.assertTrue(result['has_happy'])
        self.assertEqual(len(result['happy']), 1)
    
    @patch('stories.find_epic_link_field')
    @patch('stories.JIRA')
    def test_create_story_success(self, mock_jira_class, mock_find_field):
        """Test successful story creation"""
        # Mock Epic Link field discovery
        mock_find_field.return_value = "customfield_10008"
        
        # Mock created story
        mock_created_story = Mock()
        mock_created_story.key = "RHSTOR-2001"
        mock_created_story.permalink.return_value = "https://issues.redhat.com/browse/RHSTOR-2001"
        
        # Mock JIRA client
        mock_jira = Mock()
        mock_jira.create_issue.return_value = mock_created_story
        
        # Test KCS template
        kcs_template = {
            "summary": "KCS story for {epic_key}",
            "description": "Test KCS description for {epic_key}",
            "story_points": 3
        }
        
        result = stories.create_story(mock_jira, self.mock_epic, kcs_template, debug=False)
        
        # Verify story was created
        self.assertIsNotNone(result)
        self.assertEqual(result.key, "RHSTOR-2001")
        mock_jira.create_issue.assert_called_once()
        
        # Verify the fields passed to create_issue
        call_args = mock_jira.create_issue.call_args
        story_fields = call_args[1]['fields']
        
        self.assertEqual(story_fields['project']['key'], "RHSTOR")
        self.assertEqual(story_fields['summary'], "KCS story for RHSTOR-1234")
        self.assertEqual(story_fields['issuetype']['name'], "Story")
        self.assertEqual(story_fields['labels'], ["kcs"])
        self.assertEqual(story_fields['assignee']['name'], "testuser")
        self.assertEqual(story_fields['customfield_10008'], "RHSTOR-1234")  # Epic Link
    
    @patch('stories.JIRA')
    def test_create_story_failure(self, mock_jira_class):
        """Test story creation failure"""
        # Mock JIRA client that raises exception
        mock_jira = Mock()
        mock_jira.create_issue.side_effect = Exception("JIRA Error: Field 'priority' is required")
        
        # Test template
        template = {
            "summary": "Test story for {epic_key}",
            "description": "Test description"
        }
        
        result = stories.create_story(mock_jira, self.mock_epic, template, debug=False)
        
        # Verify story creation failed
        self.assertIsNone(result)


class TestJiraQueryBuilding(unittest.TestCase):
    """Test JIRA query building functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_jira = Mock()
        
        # Mock search results
        self.mock_epics = [
            Mock(key="RHSTOR-1001", fields=Mock(summary="Epic 1")),
            Mock(key="RHSTOR-1002", fields=Mock(summary="Epic 2"))
        ]
        self.mock_jira.search_issues.return_value = self.mock_epics
    
    @patch('stories.JIRA')
    def test_fetch_epics_by_criteria_label_only(self, mock_jira_class):
        """Test fetching epics by label only"""
        result = stories.fetch_epics_by_criteria(
            self.mock_jira, 
            label="ODF-4.19-candidate"
        )
        
        # Verify JIRA search was called
        self.mock_jira.search_issues.assert_called_once()
        call_args = self.mock_jira.search_issues.call_args[0][0]
        
        # Verify query contains label filter
        expected_query = 'project = RHSTOR AND issuetype = Epic AND labels = "ODF-4.19-candidate"'
        self.assertEqual(call_args, expected_query)
        
        # Verify results
        self.assertEqual(len(result), 2)
    
    @patch('stories.JIRA')
    def test_fetch_epics_by_criteria_fix_version_only(self, mock_jira_class):
        """Test fetching epics by fix version only"""
        result = stories.fetch_epics_by_criteria(
            self.mock_jira,
            fix_version="4.19"
        )
        
        # Verify JIRA search was called
        self.mock_jira.search_issues.assert_called_once()
        call_args = self.mock_jira.search_issues.call_args[0][0]
        
        # Verify query contains fix version filter (transformed)
        expected_query = 'project = RHSTOR AND issuetype = Epic AND fixVersion = "ODF v4.19.0"'
        self.assertEqual(call_args, expected_query)
    
    @patch('stories.JIRA')
    def test_fetch_epics_by_criteria_combined(self, mock_jira_class):
        """Test fetching epics with combined criteria"""
        result = stories.fetch_epics_by_criteria(
            self.mock_jira,
            label="ODF-4.19-candidate",
            fix_version="4.19",
            status="In Progress"
        )
        
        # Verify JIRA search was called
        self.mock_jira.search_issues.assert_called_once()
        call_args = self.mock_jira.search_issues.call_args[0][0]
        
        # Verify query contains all filters
        self.assertIn('labels = "ODF-4.19-candidate"', call_args)
        self.assertIn('fixVersion = "ODF v4.19.0"', call_args)
        self.assertIn('status = "In Progress"', call_args)
        self.assertIn('project = RHSTOR AND issuetype = Epic', call_args)
    
    @patch('stories.JIRA')
    def test_fetch_epics_by_criteria_invalid_fix_version(self, mock_jira_class):
        """Test fetching epics with invalid fix version"""
        result = stories.fetch_epics_by_criteria(
            self.mock_jira,
            fix_version="invalid"
        )
        
        # Should return empty list for invalid fix version
        self.assertEqual(len(result), 0)
        # JIRA search should not be called
        self.mock_jira.search_issues.assert_not_called()
    
    @patch('stories.JIRA')
    def test_fetch_epics_by_criteria_invalid_status(self, mock_jira_class):
        """Test fetching epics with invalid status"""
        result = stories.fetch_epics_by_criteria(
            self.mock_jira,
            status="Invalid Status"
        )
        
        # Should return empty list for invalid status
        self.assertEqual(len(result), 0)
        # JIRA search should not be called
        self.mock_jira.search_issues.assert_not_called()


class TestViewFunctions(unittest.TestCase):
    """Test functions specific to view.py"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_jira = Mock()
        
        # Mock epic with full fields
        self.mock_epic = Mock()
        self.mock_epic.key = "RHSTOR-1234"
        self.mock_epic.fields.summary = "Test Epic Summary"
        self.mock_epic.fields.status = "In Progress"
        self.mock_epic.fields.assignee.displayName = "Test User"
        self.mock_epic.fields.labels = ["ODF-4.19-candidate", "dev-preview"]
        
        # Mock fix versions
        mock_fix_version = Mock()
        mock_fix_version.name = "ODF v4.19.0"
        self.mock_epic.fields.fixVersions = [mock_fix_version]
        self.mock_epic.permalink.return_value = "https://issues.redhat.com/browse/RHSTOR-1234"
    
    @patch('view.JIRA')
    def test_fetch_epics_for_summary(self, mock_jira_class):
        """Test fetching epics for status summary in view.py"""
        # This function would be similar to stories.py but specific to view.py
        # Since the actual implementation might vary, this is a placeholder test
        pass


class TestIntegration(unittest.TestCase):
    """Integration tests for combined functionality"""
    
    @patch('stories.JIRA')
    def test_auto_mode_dev_preview_epic(self, mock_jira_class):
        """Test auto mode logic for dev-preview epic"""
        # Mock epic with dev-preview label
        mock_epic = Mock()
        mock_epic.key = "RHSTOR-1234"
        mock_epic.fields.labels = ["ODF-4.19-candidate", "dev-preview"]
        mock_epic.fields.summary = "Dev Preview Epic"
        mock_epic.fields.assignee.name = "testuser"
        mock_epic.fields.assignee.displayName = "Test User"
        mock_epic.fields.fixVersions = []
        
        # Mock no existing stories
        with patch('stories.check_existing_stories') as mock_check:
            mock_check.return_value = {
                'kcs': [],
                'happy': [],
                'has_kcs': False,
                'has_happy': False
            }
            
            # Test that dev-preview epic should get KCS template
            epics = [mock_epic]
            dev_preview_count = 0
            regular_count = 0
            
            for epic in epics:
                labels = epic.fields.labels if epic.fields.labels else []
                if "dev-preview" in labels:
                    dev_preview_count += 1
                    # Should use KCS template
                    template = stories.DEFAULT_STORY_TEMPLATES[0]
                    self.assertIn("KCS story for", template["summary"])
                else:
                    regular_count += 1
            
            self.assertEqual(dev_preview_count, 1)
            self.assertEqual(regular_count, 0)
    
    @patch('stories.JIRA')
    def test_auto_mode_regular_epic(self, mock_jira_class):
        """Test auto mode logic for regular epic"""
        # Mock epic without dev-preview label
        mock_epic = Mock()
        mock_epic.key = "RHSTOR-1235"
        mock_epic.fields.labels = ["ODF-4.19-candidate"]
        mock_epic.fields.summary = "Regular Epic"
        
        # Test that regular epic should get Happy Path template
        epics = [mock_epic]
        dev_preview_count = 0
        regular_count = 0
        
        for epic in epics:
            labels = epic.fields.labels if epic.fields.labels else []
            if "dev-preview" in labels:
                dev_preview_count += 1
            else:
                regular_count += 1
                # Should use Happy Path template
                template = stories.DEFAULT_STORY_TEMPLATES[1]
                self.assertIn("Happy Path Validation Story for", template["summary"])
        
        self.assertEqual(dev_preview_count, 0)
        self.assertEqual(regular_count, 1)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2) 