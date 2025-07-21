#!/usr/bin/env python3
"""
Test Runner for RHSTOR Tools
Sets up environment and runs unit tests safely
"""

import os
import sys
import unittest

def setup_test_environment():
    """Set up environment variables needed for testing"""
    # Set dummy JIRA token for testing (won't be used in mocked tests)
    os.environ['JIRA_API_TOKEN'] = 'dummy-token-for-testing'
    
    # Set JIRA server if not already set
    if 'JIRA_SERVER' not in os.environ:
        os.environ['JIRA_SERVER'] = 'https://issues.redhat.com'

def run_tests():
    """Run all unit tests"""
    print("🔧 Setting up test environment...")
    setup_test_environment()
    
    print("🚀 Running RHSTOR Tools Unit Tests...")
    print("=" * 60)
    
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.discover('.', pattern='test_rhstor_tools.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    if result.wasSuccessful():
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {len(result.failures)} failures, {len(result.errors)} errors")
        return 1

if __name__ == '__main__':
    sys.exit(run_tests()) 