def test_app_imports():
    import app
    if app is None:
        raise AssertionError("App is None")