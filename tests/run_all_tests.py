#!/usr/bin/env python3
"""
Complete FQS Test Suite
Runs all tests and shows final status
"""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
TEST_DIR = Path(__file__).parent


def run_test(script_name, description):
    """Run a test script and return success status"""
    print(f"\n{'='*70}")
    print(f"🧪 {description}")
    print(f"{'='*70}\n")
    
    script_path = TEST_DIR / script_name
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=PROJECT_ROOT,
            capture_output=False,
            text=True
        )
        
        success = result.returncode == 0
        if success:
            print(f"\n✅ {description} - PASSED")
        else:
            print(f"\n❌ {description} - FAILED (exit code: {result.returncode})")
        
        return success
        
    except Exception as e:
        print(f"\n❌ {description} - ERROR: {e}")
        return False


def main():
    """Run all tests"""
    print("="*70)
    print("🚀 FQS Complete Test Suite")
    print("="*70)
    
    tests = [
        ("inspect_layout.py", "Layout Inspector"),
        ("test_backend.py", "Backend Tests"),
    ]
    
    results = []
    for script, description in tests:
        results.append(run_test(script, description))
    
    # Summary
    print("\n" + "="*70)
    print("📊 FINAL SUMMARY")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    for i, (script, description) in enumerate(tests):
        status = "✅ PASSED" if results[i] else "❌ FAILED"
        print(f"{status} - {description}")
    
    print(f"\n🎯 Overall: {passed}/{total} test suites passed")
    
    if all(results):
        print("\n✨ All tests passed! Your FQS installation is working correctly.")
        print("\n📝 Next steps:")
        print("   1. Stop any running FQS instance")
        print("   2. Restart FQS: python3 -m fqs.app")
        print("   3. Navigate to a football market")
        print("   4. You should see the new widgets in the right panel!")
    else:
        print("\n⚠️  Some tests failed. Check output above for details.")
    
    print("="*70 + "\n")
    
    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
