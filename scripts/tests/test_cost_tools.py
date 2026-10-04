import importlib.util
import json
import pathlib
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


estimate = load_module("estimate_aks_cost", ROOT / "scripts" / "estimate_aks_cost.py")
budget = load_module("check_budget", ROOT / "scripts" / "check_budget.py")


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def fake_json_load(response):
    return response.payload


class CostToolTests(unittest.TestCase):
    def test_find_aks_reads_plan(self):
        plan = {
            "resource_changes": [{
                "type": "azurerm_kubernetes_cluster",
                "change": {"after": {
                    "location": "Australia East",
                    "default_node_pool": [{"node_count": 3, "vm_size": "Standard_D2s_v3"}],
                }},
            }]
        }
        self.assertEqual(
            estimate.find_aks(plan),
            {"node_count": 3, "vm_size": "Standard_D2s_v3", "location": "Australia East"},
        )

    def test_region_normalisation(self):
        self.assertEqual(estimate.normalise_region("Australia East"), "australiaeast")

    @patch("urllib.request.urlopen")
    def test_retail_price_filters_spot_and_windows(self, mock_open):
        mock_open.return_value = FakeResponse({
            "Items": [
                {"type": "Consumption", "unitOfMeasure": "1 Hour", "retailPrice": 0.02,
                 "currencyCode": "USD", "productName": "Virtual Machines Dsv3 Series", "meterName": "D2s v3 Spot"},
                {"type": "Consumption", "unitOfMeasure": "1 Hour", "retailPrice": 0.20,
                 "currencyCode": "USD", "productName": "Virtual Machines Dsv3 Series Windows", "meterName": "D2s v3"},
                {"type": "Consumption", "unitOfMeasure": "1 Hour", "retailPrice": 0.125,
                 "currencyCode": "USD", "productName": "Virtual Machines Dsv3 Series", "meterName": "D2s v3"},
            ],
            "NextPageLink": None,
        })
        with patch("json.load", side_effect=fake_json_load):
            price, currency = estimate.get_retail_price("Standard_D2s_v3", "australiaeast")
        self.assertEqual(price, 0.125)
        self.assertEqual(currency, "USD")

    def test_budget_below_threshold(self):
        threshold, percentage, action = budget.evaluate(10, 50, 80)
        self.assertEqual(threshold, 40)
        self.assertEqual(percentage, 20)
        self.assertFalse(action)

    def test_budget_at_threshold(self):
        threshold, percentage, action = budget.evaluate(40, 50, 80)
        self.assertEqual(threshold, 40)
        self.assertEqual(percentage, 80)
        self.assertTrue(action)


if __name__ == "__main__":
    unittest.main()
