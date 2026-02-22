"""
Integration Test Runner

Validates backend components and runs end-to-end integration tests.
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and return success status"""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=False,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ {description} failed with exit code {e.returncode}")
        return False


def main():
    """Run validation and integration tests"""
    print("ReconcileAI Backend Integration Test Suite")
    print("="*80)
    
    # Step 1: Validate backend components
    print("\nStep 1: Validating backend components...")
    if not run_command("python validate_backend.py", "Backend Validation"):
        print("\n✗ Backend validation failed. Please fix issues before running tests.")
        return 1
    
    # Step 2: Run integration tests
    print("\nStep 2: Running integration tests...")
    if not run_command("pytest test_e2e_workflow.py -v -s", "Integration Tests"):
        print("\n✗ Integration tests failed.")
        return 1
    
    # Success
    print("\n" + "="*80)
    print("✓ ALL TESTS PASSED!")
    print("="*80)
    print("\nBackend integration is working correctly.")
    print("You can proceed to frontend development (Task 7).")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
