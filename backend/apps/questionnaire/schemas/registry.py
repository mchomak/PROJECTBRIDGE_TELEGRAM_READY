import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import cache
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

SCHEMA_DIR = Path(__file__).resolve().parent
PROJECT_TYPES = ("website", "telegram_bot", "automation", "other")
_SCHEMA_FILENAME = re.compile(r"^(?P<key>[a-z_]+)\.v(?P<version>[1-9][0-9]*)\.json$")


class QuestionnaireSchemaError(ValueError):
    """The requested schema or answer payload does not meet its contract."""

    def __init__(self, message, *, field=None):
        super().__init__(f"{field}: {message}" if field else message)
        self.field = field


@cache
def _read_schema(schema_key, version):
    path = SCHEMA_DIR / f"{schema_key}.v{version}.json"
    try:
        with path.open(encoding="utf-8") as schema_file:
            schema = json.load(schema_file)
    except FileNotFoundError as exc:
        raise QuestionnaireSchemaError(
            "Questionnaire schema version is unavailable."
        ) from exc
    except json.JSONDecodeError as exc:
        raise QuestionnaireSchemaError("Questionnaire schema file is invalid.") from exc

    if (
        schema.get("schema_key") != schema_key
        or schema.get("version") != version
        or not isinstance(schema.get("questions"), list)
    ):
        raise QuestionnaireSchemaError("Questionnaire schema file is invalid.")
    return schema


def get_schema(project_type, version=None):
    """Load the latest or pinned immutable schema for a project type."""
    if project_type not in PROJECT_TYPES:
        raise QuestionnaireSchemaError(
            "A schema is not available for this project type."
        )

    if version is None:
        versions = []
        for path in SCHEMA_DIR.glob(f"{project_type}.v*.json"):
            match = _SCHEMA_FILENAME.fullmatch(path.name)
            if match:
                versions.append(int(match.group("version")))
        if not versions:
            raise QuestionnaireSchemaError(
                "A schema is not available for this project type."
            )
        version = max(versions)

    if type(version) is not int or version < 1:
        raise QuestionnaireSchemaError("Questionnaire schema version is invalid.")

    # Return a fresh value so consumers cannot mutate the registry cache.
    return json.loads(json.dumps(_read_schema(project_type, version)))


def get_visible_questions(schema, answers):
    """Evaluate the schema's declarative equality branches in question order."""
    visible = []
    for question in schema["questions"]:
        condition = question.get("visible_if")
        if (
            condition is None
            or answers.get(condition["question"]) == condition["equals"]
        ):
            visible.append(question)
    return visible


def get_passport_prefill(schema, passport):
    """Return values available through the explicit passport mapping only."""
    if passport is None:
        return {}

    project_type = schema["project_type"]
    answers = {}
    for key in ("goal", "target_audience", "expected_result"):
        value = getattr(passport, key, None)
        if isinstance(value, str) and value.strip():
            answers[key] = value

    for key in ("functional_scope", "constraints"):
        value = getattr(passport, key, None)
        if isinstance(value, dict):
            scoped = value.get(project_type)
            if scoped is not None and not _is_empty(scoped):
                answers[key] = scoped

    integration_data = getattr(passport, "integrations", None)
    if isinstance(integration_data, dict):
        scoped = integration_data.get(project_type)
        if isinstance(scoped, dict) and type(scoped.get("enabled")) is bool:
            answers["has_integrations"] = scoped["enabled"]
            items = scoped.get("items", [])
            if isinstance(items, list):
                answers["integrations"] = items if scoped["enabled"] else []

    deadline = getattr(passport, "deadline", None)
    if deadline is not None:
        answers["deadline"] = deadline.isoformat()
    for key in ("budget_min", "budget_max"):
        value = getattr(passport, key, None)
        if value is not None:
            answers[key] = str(value)
    currency = getattr(passport, "currency", None)
    if currency:
        answers["currency"] = currency

    try:
        return validate_answers(schema, answers)
    except QuestionnaireSchemaError:
        # Malformed/legacy JSON does not become a trusted customer answer.
        safe_answers = {
            key: value
            for key, value in answers.items()
            if key in {"goal", "target_audience", "expected_result"}
        }
        return validate_answers(schema, safe_answers)


def _is_empty(value):
    return value is None or value == "" or value == [] or value == {}


def _decimal_value(value, question):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise QuestionnaireSchemaError("Enter a valid number.", field=question["key"])
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise QuestionnaireSchemaError(
            "Enter a valid number.", field=question["key"]
        ) from exc
    if not number.is_finite():
        raise QuestionnaireSchemaError("Enter a valid number.", field=question["key"])
    if number < Decimal(question.get("minimum", "-Infinity")):
        raise QuestionnaireSchemaError(
            "Enter a value within the allowed range.", field=question["key"]
        )

    normalized = number.normalize()
    whole_digits = len(normalized.as_tuple().digits) + normalized.as_tuple().exponent
    decimal_places = max(0, -normalized.as_tuple().exponent)
    if whole_digits + decimal_places > question.get("maximum_digits", 30):
        raise QuestionnaireSchemaError(
            "Enter a number with fewer digits.", field=question["key"]
        )
    if decimal_places > question.get("decimal_places", 10):
        raise QuestionnaireSchemaError(
            "Enter a number with fewer decimal places.", field=question["key"]
        )
    return format(number, "f")


def _validate_value(question, value):
    key = question["key"]
    kind = question["type"]
    if _is_empty(value):
        return value

    if kind in {"text", "textarea"}:
        if not isinstance(value, str):
            raise QuestionnaireSchemaError("Enter text.", field=key)
        normalized = value.strip()
        if len(normalized) < question.get("min_length", 0):
            raise QuestionnaireSchemaError("Enter a longer answer.", field=key)
        if len(normalized) > question.get("max_length", 10000):
            raise QuestionnaireSchemaError("Enter a shorter answer.", field=key)
        return normalized

    if kind == "boolean":
        if type(value) is not bool:
            raise QuestionnaireSchemaError("Choose yes or no.", field=key)
        return value

    if kind == "select":
        allowed = {option["value"] for option in question["options"]}
        if not isinstance(value, str) or value not in allowed:
            raise QuestionnaireSchemaError("Choose an available option.", field=key)
        return value

    if kind == "url":
        if not isinstance(value, str):
            raise QuestionnaireSchemaError("Enter a valid HTTP(S) address.", field=key)
        value = value.strip()
        try:
            parsed = urlparse(value)
            hostname = parsed.hostname
            port = parsed.port
            URLValidator(schemes=["http", "https"])(value)
        except (ValueError, ValidationError) as exc:
            raise QuestionnaireSchemaError(
                "Enter a valid HTTP(S) address.", field=key
            ) from exc
        if (
            len(value) > question.get("max_length", 2048)
            or parsed.scheme not in {"http", "https"}
            or not hostname
            or any(character.isspace() for character in parsed.netloc)
            or (port is not None and not 0 <= port <= 65535)
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise QuestionnaireSchemaError("Enter a valid HTTP(S) address.", field=key)
        return value

    if kind == "date":
        if not isinstance(value, str):
            raise QuestionnaireSchemaError(
                "Enter a date in YYYY-MM-DD format.", field=key
            )
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise QuestionnaireSchemaError(
                "Enter a date in YYYY-MM-DD format.", field=key
            )
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise QuestionnaireSchemaError(
                "Enter a date in YYYY-MM-DD format.", field=key
            ) from exc
        return value

    if kind == "decimal":
        return _decimal_value(value, question)

    if kind == "currency":
        if not isinstance(value, str) or not re.fullmatch(
            r"[A-Za-z]{3}", value.strip()
        ):
            raise QuestionnaireSchemaError(
                "Enter a three-letter currency code.", field=key
            )
        return value.strip().upper()

    if kind == "string_list":
        if not isinstance(value, list) or any(
            not isinstance(item, str) for item in value
        ):
            raise QuestionnaireSchemaError("Enter a list of text values.", field=key)
        normalized = [item.strip() for item in value]
        if any(not item for item in normalized):
            raise QuestionnaireSchemaError(
                "Remove blank items from the list.", field=key
            )
        if len(normalized) > question.get("max_items", 100):
            raise QuestionnaireSchemaError("Remove some list items.", field=key)
        return normalized

    raise QuestionnaireSchemaError(
        "Questionnaire schema uses an unsupported field type.", field=key
    )


def validate_answers(schema, answers, *, require_complete=False):
    """Validate known, active answer keys and optionally require every visible field."""
    if not isinstance(answers, dict):
        raise QuestionnaireSchemaError("Answers must be an object.")

    questions = {question["key"]: question for question in schema["questions"]}
    unknown = set(answers) - set(questions)
    if unknown:
        key = sorted(unknown)[0]
        raise QuestionnaireSchemaError(
            "This question is not part of the schema.", field=key
        )

    visible_keys = {
        question["key"] for question in get_visible_questions(schema, answers)
    }
    normalized = {}
    for key, value in answers.items():
        if key not in visible_keys:
            # An empty integration list is the canonical result of answering no.
            if (
                key == "integrations"
                and answers.get("has_integrations") is False
                and value == []
            ):
                normalized[key] = []
                continue
            raise QuestionnaireSchemaError(
                "This answer belongs to an inactive branch.", field=key
            )
        normalized[key] = _validate_value(questions[key], value)

    if answers.get("has_integrations") is False:
        if answers.get("integrations", []) not in ([], None):
            raise QuestionnaireSchemaError(
                "Clear integrations when the answer is no.", field="integrations"
            )
        normalized["integrations"] = []

    if (
        answers.get("has_integrations") is True
        and require_complete
        and not normalized.get("integrations")
    ):
        raise QuestionnaireSchemaError(
            "List at least one integration.", field="integrations"
        )

    for question in get_visible_questions(schema, normalized):
        key = question["key"]
        value = normalized.get(key)
        empty = (
            key not in normalized
            or _is_empty(value)
            or (isinstance(value, str) and not value.strip())
        )
        if require_complete and question.get("required") and empty:
            raise QuestionnaireSchemaError("This answer is required.", field=key)

    for question in schema["questions"]:
        if question.get("required_if_any") and any(
            not _is_empty(normalized.get(key)) for key in question["required_if_any"]
        ):
            key = question["key"]
            if _is_empty(normalized.get(key)):
                raise QuestionnaireSchemaError(
                    "A currency is required for the budget.", field=key
                )

    minimum = normalized.get("budget_min")
    maximum = normalized.get("budget_max")
    if minimum is not None and minimum != "" and maximum is not None and maximum != "":
        if Decimal(minimum) > Decimal(maximum):
            raise QuestionnaireSchemaError(
                "The minimum budget cannot exceed the maximum budget.",
                field="budget_min",
            )

    return normalized
