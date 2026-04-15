from unittest import mock
import requests
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User

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

    @mock.patch("cvat.apps.lambda_manager.views.LambdaGateway.list")
    def test_list_functions_empty(self, mock_list):
        mock_list.return_value = []

        response = self.client.get("/api/lambda/functions")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])
        mock_list.assert_called_once()

    def test_list_functions_unauthenticated(self):
        self.client.logout()

        response = self.client.get("/api/lambda/functions")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        )

    @mock.patch("cvat.apps.lambda_manager.views.LambdaGateway._http")
    def test_list_functions_handles_malformed_response(self, mock_http):
        """
        If Nuclio returns function metadata missing required fields,
        the API should not return a 500.
        """
        mock_http.return_value = {
            "good-function": {"metadata": {"name": "good-function"}, "spec": {}},
            "bad-function": {},
        }

        response = self.client.get("/api/lambda/functions")

        self.assertNotEqual(
            response.status_code,
            500,
            f"Server crashed on malformed Nuclio response: {response.content}",
        )

    @mock.patch("cvat.apps.lambda_manager.views.LambdaGateway.list")
    def test_list_functions_success(self, mock_list):
        """
        Verifies that a valid list of functions is returned correctly.
        """
        mock_list.return_value = [
            {
                "metadata": {"name": "test-model"},
                "spec": {"description": "A successful test model"}
            }
        ]

        response = self.client.get("/api/lambda/functions")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["metadata"]["name"], "test-model")

    @mock.patch("cvat.apps.lambda_manager.views.LambdaGateway.list")
    def test_list_functions_connection_error_returns_503(self, mock_list):
        mock_list.side_effect = requests.ConnectionError("Nuclio is unavailable")

        response = self.client.get("/api/lambda/functions")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
