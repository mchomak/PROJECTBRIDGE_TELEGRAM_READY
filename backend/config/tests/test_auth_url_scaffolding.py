from django.urls import URLResolver, get_resolver


def test_auth_router_includes_separate_core_and_verification_url_modules():
    auth_router = next(
        pattern
        for pattern in get_resolver().url_patterns
        if isinstance(pattern, URLResolver) and str(pattern.pattern) == "api/v1/auth/"
    )

    included_modules = [
        pattern.urlconf_name.__name__ for pattern in auth_router.url_patterns
    ]

    assert included_modules == [
        "apps.accounts.api.core_urls",
        "apps.accounts.api.verification_urls",
    ]
