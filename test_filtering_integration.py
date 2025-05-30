#!/usr/bin/env python3
"""
Quick integration test for the filtering system.
"""


def test_basic_imports():
    """Test that all filtering components can be imported."""
    try:
        from src.zigi_amazon_mcp.filtering import FilterDatabase, FilterLibrary, FilterManager

        print("✅ Basic imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_database_initialization():
    """Test database initialization."""
    try:
        from src.zigi_amazon_mcp.filtering import FilterDatabase

        # Test database creation
        db = FilterDatabase(":memory:")  # Use in-memory database for testing
        health = db.get_health_check()

        if health["status"] == "healthy":
            print("✅ Database initialization successful")
            return True
        else:
            print(f"❌ Database health check failed: {health}")
            return False

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False


def test_filter_library():
    """Test filter library basic functionality."""
    try:
        from src.zigi_amazon_mcp.filtering import FilterLibrary

        # Test filter library creation
        lib = FilterLibrary(":memory:")

        # Test search (should return empty initially)
        filters = lib.search_filters()
        print(f"✅ Filter library initialized with {len(filters)} filters")
        return True

    except Exception as e:
        print(f"❌ Filter library test failed: {e}")
        return False


def test_filter_manager():
    """Test filter manager functionality."""
    try:
        from src.zigi_amazon_mcp.filtering import FilterManager

        # Test filter manager creation
        manager = FilterManager(":memory:")

        # Test filter discovery
        result = manager.get_available_filters()
        print(f"✅ Filter manager initialized, found {result['total_filters']} filters")
        return True

    except Exception as e:
        print(f"❌ Filter manager test failed: {e}")
        return False


def test_jsonquerylang_dependency():
    """Test that jsonquerylang is available."""
    try:
        from jsonquerylang import jsonquery

        # Simple test
        data = [{"name": "test", "value": 10}]
        result = jsonquery(data, "filter(.value > 5)")

        if len(result) == 1:
            print("✅ jsonquerylang dependency working")
            return True
        else:
            print("❌ jsonquerylang test failed")
            return False

    except ImportError:
        print("❌ jsonquerylang not installed - run: pip install jsonquerylang")
        return False
    except Exception as e:
        print(f"❌ jsonquerylang test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Testing Filtering System Integration...")
    print("=" * 50)

    tests = [
        test_basic_imports,
        test_database_initialization,
        test_filter_library,
        test_filter_manager,
        test_jsonquerylang_dependency,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! Filtering system is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Check dependencies and implementation.")
        return False


if __name__ == "__main__":
    main()
