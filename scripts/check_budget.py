#!/usr/bin/env python3
import argparse
import os


def set_output(name: str, value) -> None:
    output_file = os.getenv("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")


def evaluate(spend: float, budget: float, threshold_percent: float):
    if budget <= 0:
        raise ValueError("Budget must be greater than zero.")
    if not 0 < threshold_percent <= 100:
        raise ValueError("Threshold percent must be between 0 and 100.")

    threshold_value = budget * threshold_percent / 100.0
    percentage = spend / budget * 100.0
    action_required = spend >= threshold_value
    return threshold_value, percentage, action_required


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Azure spend against a cost-control threshold.")
    parser.add_argument("--spend", required=True, type=float)
    parser.add_argument("--budget", required=True, type=float)
    parser.add_argument("--threshold-percent", required=True, type=float)
    parser.add_argument("--currency", default="USD")
    args = parser.parse_args()

    threshold_value, percentage, action_required = evaluate(
        args.spend, args.budget, args.threshold_percent
    )

    print(f"Current spend: {args.spend:.2f} {args.currency}")
    print(f"Budget: {args.budget:.2f} {args.currency}")
    print(f"Threshold: {args.threshold_percent:.1f}% ({threshold_value:.2f} {args.currency})")
    print(f"Budget used: {percentage:.1f}%")
    print(f"Action required: {'YES' if action_required else 'NO'}")

    set_output("threshold_value", f"{threshold_value:.2f}")
    set_output("percentage", f"{percentage:.1f}")
    set_output("action_required", str(action_required).lower())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
