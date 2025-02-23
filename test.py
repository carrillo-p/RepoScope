def test_language_detection():
    analyzer = GitHubAnalyzer()
    # Use a known repository with multiple languages
    test_repo = "https://github.com/python/cpython"  
    stats = analyzer.get_repo_stats(test_repo)
    print("Languages found:", stats.get('languages', []))

if __name__ == "__main__":
    test_language_detection()