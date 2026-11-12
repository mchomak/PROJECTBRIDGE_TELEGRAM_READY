import pytest

from apps.questionnaire.schemas.registry import (
    get_schema,
    get_visible_questions,
    validate_answers,
)


@pytest.mark.parametrize(
    ("project_type", "type_branch"),
    [
        ("website", "has_existing_site"),
        ("telegram_bot", "has_existing_bot"),
        ("automation", "trigger_type"),
        ("other", "project_area"),
    ],
)
def test_all_project_types_have_version_one_product_schemas(project_type, type_branch):
    schema = get_schema(project_type)

    assert schema["schema_key"] == project_type
    assert schema["project_type"] == project_type
    assert schema["version"] == 1
    assert type_branch in {question["key"] for question in schema["questions"]}


@pytest.mark.parametrize(
    ("project_type", "answers", "visible", "hidden"),
    [
        (
            "website",
            {"has_existing_site": True},
            "existing_site_url",
            None,
        ),
        (
            "website",
            {"has_existing_site": False},
            None,
            "existing_site_url",
        ),
        (
            "telegram_bot",
            {"has_existing_bot": True},
            "existing_bot_url",
            None,
        ),
        (
            "telegram_bot",
            {"has_existing_bot": False},
            None,
            "existing_bot_url",
        ),
        (
            "automation",
            {"trigger_type": "scheduled"},
            "schedule_details",
            "event_source",
        ),
        (
            "automation",
            {"trigger_type": "event"},
            "event_source",
            "schedule_details",
        ),
        (
            "automation",
            {"trigger_type": "manual"},
            None,
            "schedule_details",
        ),
        ("other", {}, "project_area", None),
    ],
)
def test_branch_visibility_is_deterministic(project_type, answers, visible, hidden):
    schema = get_schema(project_type)
    keys = {question["key"] for question in get_visible_questions(schema, answers)}

    if visible:
        assert visible in keys
    if hidden:
        assert hidden not in keys


@pytest.mark.parametrize(
    ("project_type", "answers"),
    [
        (
            "website",
            {"has_existing_site": False, "existing_site_url": "https://old.test"},
        ),
        (
            "telegram_bot",
            {"has_existing_bot": False, "existing_bot_url": "https://old.test"},
        ),
        ("automation", {"trigger_type": "manual", "schedule_details": "Every day"}),
    ],
)
def test_inactive_branch_answers_are_rejected(project_type, answers):
    with pytest.raises(ValueError, match="inactive branch"):
        validate_answers(get_schema(project_type), answers)


def test_required_fields_and_integration_branch_are_validated():
    schema = get_schema("website")

    with pytest.raises(ValueError, match="goal"):
        validate_answers(
            schema, {"target_audience": "Customers"}, require_complete=True
        )

    complete = {
        "goal": "Launch a portal",
        "target_audience": "Customers",
        "expected_result": "Customers can self-serve",
        "functional_scope": "Accounts and requests",
        "has_integrations": True,
        "integrations": ["Billing"],
        "has_existing_site": False,
    }
    assert validate_answers(schema, complete, require_complete=True) == complete

    with pytest.raises(ValueError, match="integrations"):
        validate_answers(
            schema,
            {**complete, "has_integrations": True, "integrations": []},
            require_complete=True,
        )


def test_date_budget_and_currency_rules_are_server_validated():
    schema = get_schema("other")
    common = {
        "goal": "Coordinate a community event",
        "target_audience": "Local residents",
        "expected_result": "An event registration system",
        "functional_scope": "Registration and reminders",
        "has_integrations": False,
        "project_area": "Community services",
    }

    with pytest.raises(ValueError, match="deadline"):
        validate_answers(schema, {**common, "deadline": "31-12-2026"})
    for deadline in ("20261112", "2026-W46-4"):
        with pytest.raises(ValueError, match="deadline"):
            validate_answers(schema, {**common, "deadline": deadline})
    with pytest.raises(ValueError, match="budget_min"):
        validate_answers(
            schema,
            {**common, "budget_min": "50", "budget_max": "20", "currency": "USD"},
        )
    with pytest.raises(ValueError, match="currency"):
        validate_answers(schema, {**common, "budget_min": "20"})
    with pytest.raises(ValueError, match="currency"):
        validate_answers(schema, {**common, "currency": "1$D"})


def test_draft_validation_allows_partial_answers_but_checks_present_values():
    schema = get_schema("website")

    assert validate_answers(schema, {"goal": ""}) == {"goal": ""}
    with pytest.raises(ValueError, match="goal"):
        validate_answers(schema, {"goal": 42})


@pytest.mark.parametrize("value", [["scheduled"], {"value": "scheduled"}])
def test_select_validation_rejects_non_scalar_values(value):
    with pytest.raises(ValueError, match="trigger_type"):
        validate_answers(get_schema("automation"), {"trigger_type": value})


@pytest.mark.parametrize(
    "value",
    [
        "https://[::1",
        "https://bad host",
        "https://example.com:99999",
    ],
)
def test_url_validation_reports_malformed_authority(value):
    schema = get_schema("website")

    with pytest.raises(ValueError, match="existing_site_url"):
        validate_answers(
            schema,
            {
                "has_existing_site": True,
                "existing_site_url": value,
            },
        )
