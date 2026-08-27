import re

def is_valid_github_url(url: str) -> bool:
    pattern = r"https?://github\.com/[^/]+/[^/]+"
    return bool(re.match(pattern, url.strip()))
