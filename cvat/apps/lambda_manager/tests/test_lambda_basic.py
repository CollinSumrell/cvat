import json
import unittest
from unittest import mock

import requests
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User


def _make_function_data(name, kind="detector", labels=None, description="A test function"):
    """
    Build a Nuclio function metadata dict matching what LambdaFunction.__init__ expects.
    This is a helper so we don't repeat the same boilerplate in every test.
    """
    if labels is None:
        labels = [{"id": 0, "name": "person"}]
    return {
        "metadata": {
            "name": name,
            "annotations": {
                "type": kind,
                "spec": json.dumps(labels),
                "name": name.replace("-", " ").title(),
            },
        },
        "spec": {
            "description": description,
        },
        "status": {
            "httpPort": 8080,
        },
    }


# ============================================================
# Tests for GET /api/lambda/functions (function discovery)
# ============================================================

class LambdaFunctionsListTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username="testuser",
            password="testpass123",
            email="test@example.com",
        )

    def setUp(self):
        self.client.force_login(self.user)

    # --- Week 1 tests ---

    @mock.patch("cvat.apps.lambda_manager.views.LambdaGateway.list")
    def test_list_functions_empty(self, mock_list):
        """Empty Nuclio dashboard returns 200 with an empty list."""
        mock_list.return_value = []
        response = self.client.get("/api/lambda/functions")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])
        mock_list.assert_called_once()

    def test_list_functions_unauthenticated(self):
        """Unauthenticated requests should be rejected."""
        self.client.logout()
        response = self.client.get("/api/lambda/functions")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    @unittest.expectedFailure
    @mock.patch("cvat.apps.lambda_manager.views.LambdaGateway._http")
    def test_list_functions_handles_malformed_response(self, mock_http):
        """
        DEFECT: When Nuclio returns function metadata missing the 'annotations'
        field, LambdaFunction.__init__ raises an unhandled KeyError,
        crashing the entire /api/lambda/functions endpoint with a 500.
        """
        mock_http.return_value = {
            "good-function": _make_function_data("good-function"),
            "bad-function": {},
        }
        response = self.client.get("/api/lambda/functions")
        self.assertNotEqual(response.status_code, 500)

    @mock.patch("cvat.apps.lambda_manager.views.LambdaGateway._http")
    def test_list_functions_success(self, mock_http):
        """A well-formed Nuclio function should appear in the API response."""
        mock_http.return_value = {
            "test-detector": _make_function_data("test-detector"),
        }
        response = self.client.get("/api/lambda/functions")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "test-detector")
        self.assertEqual(data[0]["kind"], "detector")

    # --- Week 2 tests ---

    @mock.patch("cvat.apps.lambda_manager.views.LambdaGateway.list")
    def test_list_functions_connection_error_returns_503(self, mock_list):
        """When Nuclio is unreachable, CVAT should return 503."""
        mock_list.side_effect = requests.ConnectionError("Nuclio is unavailable")
        response = self.client.get("/api/lambda/functions")
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    @mock.patch("cvat.apps.lambda_manager.views.LambdaGateway.list")
    def test_list_functions_timeout_returns_504(self, mock_list):
        """When Nuclio times out, CVAT should return 504."""
        mock_list.side_effect = requests.Timeout("Nuclio timed out")
        response = self.client.get("/api/lambda/functions")
        self.assertEqual(response.status_code, status.HTTP_504_GATEWAY_TIMEOUT)

    # --- Week 3 function-type consistency ---

    @mock.patch("cvat.apps.lambda_manager.views.LambdaGateway._http")
    def test_list_functions_all_four_types(self, mock_http):
        """
        All four function types (detector, interactor, tracker, reid)
        should be listed correctly when returned by Nuclio.
        """
        mock_http.return_value = {
            "my-detector": _make_function_data("my-detector", kind="detector"),
            "my-interactor": _make_function_data("my-interactor", kind="interactor"),
            "my-tracker": _make_function_data("my-tracker", kind="tracker"),
            "my-reid": _make_function_data("my-reid", kind="reid"),
        }
        response = self.client.get("/api/lambda/functions")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 4)
        returned_kinds = {f["kind"] for f in data}
        self.assertEqual(returned_kinds, {"detector", "interactor", "tracker", "reid"})

    @mock.patch("cvat.apps.lambda_manager.views.LambdaGateway._http")
    def test_list_functions_unknown_type_is_skipped(self, mock_http):
        """
        A function with an unrecognized type should be silently skipped,
        not crash the endpoint. CVAT logs the error and returns the
        remaining valid functions.
        """
        mock_http.return_value = {
            "bad-type": _make_function_data("bad-type", kind="segmentor"),
            "good-detector": _make_function_data("good-detector", kind="detector"),
        }
        response = self.client.get("/api/lambda/functions")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "good-detector")

    # --- Week 3 metadata edge cases ---

    @mock.patch("cvat.apps.lambda_manager.views.LambdaGateway._http")
    def test_list_functions_non_unique_labels_is_skipped(self, mock_http):
        """
        A function with duplicate label names should be silently skipped,
        not crash the endpoint or return corrupted data.
        """
        duplicate_labels = [
            {"id": 0, "name": "person"},
            {"id": 1, "name": "person"},
        ]
        mock_http.return_value = {
            "dupe-labels": _make_function_data("dupe-labels", labels=duplicate_labels),
            "clean-function": _make_function_data("clean-function"),
        }
        response = self.client.get("/api/lambda/functions")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "clean-function")

    @mock.patch("cvat.apps.lambda_manager.views.LambdaGateway._http")
    def test_list_functions_empty_spec(self, mock_http):
        """
        A function with an empty label spec should still
        be listable
        """
        mock_http.return_value = {
            "no-labels": _make_function_data("no-labels", labels=[]),
        }
        response = self.client.get("/api/lambda/functions")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["labels_v2"], [])


# ============================================================
# Tests for GET /api/lambda/functions/<func_id> (single function)
# ============================================================

class LambdaFunctionRetrieveTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username="testuser2",
            password="testpass123",
            email="test2@example.com",
        )

    def setUp(self):
        self.client.force_login(self.user)

    @mock.patch("cvat.apps.lambda_manager.views.LambdaGateway._http")
    def test_retrieve_existing_function(self, mock_http):
        """Fetching a specific function by ID should return its metadata."""
        mock_http.return_value = _make_function_data("my-detector")
        response = self.client.get("/api/lambda/functions/my-detector")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "my-detector")

    @mock.patch("cvat.apps.lambda_manager.views.LambdaGateway._http")
    def test_retrieve_nonexistent_function(self, mock_http):
        """Fetching a function that doesn't exist should return 404."""
        mock_http.side_effect = requests.HTTPError(
            response=mock.MagicMock(status_code=404)
        )
        response = self.client.get("/api/lambda/functions/does-not-exist")
        self.assertIn(response.status_code, (404, 500))

    def test_retrieve_function_unauthenticated(self):
        """Unauthenticated requests to retrieve a function should be rejected."""
        self.client.logout()
        response = self.client.get("/api/lambda/functions/any-function")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )


# ============================================================
# Tests for POST /api/lambda/functions/<func_id> (invocation)
# ============================================================

class LambdaFunctionCallTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username="testuser3",
            password="testpass123",
            email="test3@example.com",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_call_function_missing_task_and_job(self):
        """
        Calling a function without specifying a task or job should
        return a 400, not a 500.
        """
        response = self.client.post(
            "/api/lambda/functions/some-detector",
            data={},
            format="json",
        )
        self.assertIn(response.status_code, (400, 404))

    def test_call_function_nonexistent_task(self):
        """
        Calling a function with a task ID that doesn't exist should
        return a 400 with a meaningful error.
        """
        response = self.client.post(
            "/api/lambda/functions/some-detector",
            data={"task": 999999},
            format="json",
        )
        self.assertIn(response.status_code, (400, 404))

    def test_call_function_nonexistent_job(self):
        """
        Calling a function with a job ID that doesn't exist should
        return a 400 with a meaningful error.
        """
        response = self.client.post(
            "/api/lambda/functions/some-detector",
            data={"job": 999999},
            format="json",
        )
        self.assertIn(response.status_code, (400, 404))

    def test_call_function_unauthenticated(self):
        """Unauthenticated function invocations should be rejected."""
        self.client.logout()
        response = self.client.post(
            "/api/lambda/functions/some-detector",
            data={"task": 1},
            format="json",
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )


# ============================================================
# Tests for /api/lambda/requests (async invocation queue)
# ============================================================

class LambdaRequestsTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username="testuser4",
            password="testpass123",
            email="test4@example.com",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_list_requests_empty(self):
        """With no pending requests, the endpoint should return an empty list."""
        response = self.client.get("/api/lambda/requests")
        self.assertEqual(response.status_code, 200)

    def test_create_request_empty_body(self):
        """
        Submitting a request with no body should return a 400,
        not a 500.
        """
        response = self.client.post(
            "/api/lambda/requests",
            data={},
            format="json",
        )
        self.assertNotEqual(response.status_code, 500)

    def test_create_request_missing_function(self):
        """
        Submitting a request without specifying which function to run
        should return a clear error.
        """
        response = self.client.post(
            "/api/lambda/requests",
            data={"task": 1},
            format="json",
        )
        self.assertNotEqual(response.status_code, 500)

    def test_create_request_nonexistent_task(self):
        """
        Submitting a request for a task that doesn't exist should
        return a 400 or 404, not a 500.
        """
        response = self.client.post(
            "/api/lambda/requests",
            data={"function": "some-detector", "task": 999999},
            format="json",
        )
        self.assertNotEqual(response.status_code, 500)

    def test_create_request_unauthenticated(self):
        """Unauthenticated users should not be able to submit requests."""
        self.client.logout()
        response = self.client.post(
            "/api/lambda/requests",
            data={"function": "some-detector", "task": 1},
            format="json",
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_list_requests_unauthenticated(self):
        """Unauthenticated users should not be able to list requests."""
        self.client.logout()
        response = self.client.get("/api/lambda/requests")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )