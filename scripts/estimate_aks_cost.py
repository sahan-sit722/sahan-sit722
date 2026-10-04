#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

HOURS_PER_MONTH = 730


def normalise_region(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def find_aks(plan: dict) -> dict:
    for rc in plan.get("resource_changes", []):
        if rc.get("type") != "azurerm_kubernetes_cluster":
            continue
        after = (rc.get("change") or {}).get("after") or {}
        pools = after.get("default_node_pool") or []
        if not pools:
            continue
        pool = pools[0]
        return {
            "node_count": int(pool["node_count"]),
            "vm_size": str(pool["vm_size"]),
            "location": str(after.get("location") or ""),
        }
    raise RuntimeError("No planned azurerm_kubernetes_cluster resource was found in the Terraform plan.")


def get_retail_price(vm_size: str, region: str, timeout: int = 20) -> tuple[float, str]:
    filter_expr = (
        f"serviceName eq 'Virtual Machines' and "
        f"armSkuName eq '{vm_size}' and "
        f"armRegionName eq '{region}'"
    )
    params = urllib.parse.urlencode({"$filter": filter_expr})
    url = f"https://prices.azure.com/api/retail/prices?{params}"

    candidates = []
    while url:
        req = urllib.request.Request(url, headers={"User-Agent": "koalatech-cost-gate/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.load(response)

        for item in payload.get("Items", []):
            text = " ".join(
                str(item.get(k, ""))
                for k in ("productName", "skuName", "meterName")
            ).lower()
            if str(item.get("type", "")).lower() != "consumption":
                continue
            if item.get("unitOfMeasure") != "1 Hour":
                continue
            if any(term in text for term in ("windows", "spot", "low priority")):
                continue
            price = float(item.get("retailPrice") or 0)
            if price <= 0:
                continue
            candidates.append((price, str(item.get("currencyCode") or "USD")))

        url = payload.get("NextPageLink")

    if not candidates:
        raise RuntimeError(
            f"Azure Retail Prices API returned no suitable Linux consumption price for {vm_size} in {region}."
        )

    candidates.sort(key=lambda x: x[0])
    return candidates[0]


def set_output(name: str, value) -> None:
    output_file = os.getenv("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Estimate AKS worker-node cost from a Terraform plan.")
    parser.add_argument("--plan", required=True, help="Path to terraform show -json output")
    parser.add_argument("--max-hourly-cost", required=True, type=float)
    parser.add_argument(
        "--fallback-unit-price",
        type=float,
        default=None,
        help="Optional hourly VM price used only if the Azure Retail Prices API cannot be reached.",
    )
    args = parser.parse_args()

    with open(args.plan, "r", encoding="utf-8") as f:
        plan = json.load(f)

    aks = find_aks(plan)
    region = normalise_region(aks["location"])
    if not region:
        raise RuntimeError("AKS location is unknown in the Terraform plan.")

    price_source = "Azure Retail Prices API"
    try:
        unit_price, currency = get_retail_price(aks["vm_size"], region)
    except Exception as exc:
        if args.fallback_unit_price is None:
            raise
        unit_price = args.fallback_unit_price
        currency = "USD"
        price_source = f"fallback value ({exc})"

    hourly = unit_price * aks["node_count"]
    monthly = hourly * HOURS_PER_MONTH
    allowed = hourly <= args.max_hourly_cost

    print("AKS planned cost estimate")
    print(f"  Region: {region}")
    print(f"  VM size: {aks['vm_size']}")
    print(f"  Node count: {aks['node_count']}")
    print(f"  Unit price: {unit_price:.6f} {currency}/hour")
    print(f"  Cluster worker-node cost: {hourly:.4f} {currency}/hour")
    print(f"  Approx. 730-hour run rate: {monthly:.2f} {currency}/month")
    print(f"  Gate limit: {args.max_hourly_cost:.4f} {currency}/hour")
    print(f"  Price source: {price_source}")
    print(f"  Result: {'PASS' if allowed else 'BLOCK'}")

    for key, value in {
        "region": region,
        "vm_size": aks["vm_size"],
        "node_count": aks["node_count"],
        "unit_price": f"{unit_price:.6f}",
        "hourly_cost": f"{hourly:.4f}",
        "monthly_cost": f"{monthly:.2f}",
        "currency": currency,
        "price_source": price_source,
        "allowed": str(allowed).lower(),
    }.items():
        set_output(key, value)

    return 0 if allowed else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
