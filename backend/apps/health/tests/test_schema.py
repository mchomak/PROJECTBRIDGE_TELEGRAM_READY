from rest_framework.test import APIClient


def test_development_schema_exposes_health_operation_and_swagger_docs():
    client = APIClient()

    schema_response = client.get(
        "/api/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json"
    )
    assert schema_response.status_code == 200
    schema = schema_response.json()
    assert schema["paths"]["/api/v1/health/"]["get"]["operationId"] == "health_check"

    docs_response = client.get("/api/docs/")
    assert docs_response.status_code == 200
    assert b"swagger-ui" in docs_response.content
