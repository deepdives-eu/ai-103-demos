#!/usr/bin/env bash
# Find one agent run in the Log Analytics workspace from the command line.
# Usage: ./query_trace.sh [trace-id]   (default: the trace ID of the last run)
# Read-only. Source: https://learn.microsoft.com/azure/azure-monitor/logs/api/overview
set -euo pipefail
cd "$(dirname "$0")"

TRACE_ID=${1:-$(python3 -c 'import json; print(json.load(open(".last_run.json"))["trace_id"])')}

# The query command wants the workspace GUID (customerId), not its name.
WS=$(az monitor log-analytics workspace show -g rg-ai103-d2 -n law-ai103-d2 --query customerId -o tsv)

QUERY=$(cat <<EOF
union withsource=TableName AppRequests, AppDependencies
| where OperationId == "$TRACE_ID"
| project TimeGenerated, TableName, Name, DurationMs, Success
| order by TimeGenerated asc
EOF
)

az monitor log-analytics query --workspace "$WS" --analytics-query "$QUERY" --timespan PT1H -o table
