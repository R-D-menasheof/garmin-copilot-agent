"""Quick Azure cost check for Vitalis."""
import subprocess, json

sub_id = subprocess.check_output(
    ["az", "account", "show", "--query", "id", "-o", "tsv"]
).decode().strip()

body = json.dumps({
    "type": "ActualCost",
    "timeframe": "MonthToDate",
    "dataset": {
        "granularity": "None",
        "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
        "grouping": [{"type": "Dimension", "name": "ServiceName"}],
    },
})

result = subprocess.check_output([
    "az", "rest", "--method", "POST",
    "--headers", "Content-Type=application/json",
    "--uri", f"https://management.azure.com/subscriptions/{sub_id}/providers/Microsoft.CostManagement/query?api-version=2023-11-01",
    "--body", body,
]).decode()

data = json.loads(result)
rows = data.get("properties", {}).get("rows", [])
total = 0
print("\n  Azure Costs — April 2026 (Month to Date)")
print("  " + "-" * 50)
for row in sorted(rows, key=lambda r: r[0], reverse=True):
    cost, currency, service = row[0], row[1], row[2]
    total += cost
    print(f"  {service:40s} ${cost:.2f} {currency}")
print("  " + "-" * 50)
print(f"  {'TOTAL':40s} ${total:.2f}")
print(f"\n  Budget: $10/mo  |  Used: ${total:.2f}  |  Remaining: ${10 - total:.2f}")
