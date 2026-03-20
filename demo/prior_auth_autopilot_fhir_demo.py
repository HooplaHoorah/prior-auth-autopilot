#!/usr/bin/env python3
"""
prior_auth_autopilot_fhir_demo.py - End-to-end demo runner for Prior Auth Autopilot.
Invokes the MCP Lambda directly via boto3 and runs all 3 clinical scenarios.

Environment variables:
    AWS_REGION                  (default: us-east-1)
    MCP_LAMBDA_FUNCTION_NAME    (default: criteria-composer-mcp)
    FHIR_BASE_URL               (e.g. http://ec2-ip:8080/fhir)
"""

import json
import time
import os
import boto3

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
MCP_LAMBDA = os.environ.get("MCP_LAMBDA_FUNCTION_NAME", "criteria-composer-mcp")
FHIR_BASE_URL = os.environ.get("FHIR_BASE_URL", "http://localhost:8080/fhir")

SCENARIOS = [
    {
        "name": "Scenario A: Mary Johnson (RA, BCBS Arkansas)",
        "patient_id": "patient-mary-johnson",
        "criteria_set_id": "bcbs_biologics_ra_2026",
        "fhir_token": "demo-token",
        "expected": "APPROVE",
    },
    {
        "name": "Scenario B: Robert Chen (Psoriasis, Aetna)",
        "patient_id": "patient-robert-chen",
        "criteria_set_id": "aetna_biologics_ra_2026",
        "fhir_token": "demo-token",
        "expected": "DENY",
    },
    {
        "name": "Scenario C: Patricia Williams (RA + TB Risk, BCBS)",
        "patient_id": "patient-patricia-williams",
        "criteria_set_id": "bcbs_biologics_ra_2026",
        "fhir_token": "demo-token",
        "expected": "DENY",
    },
]


def invoke_mcp_tool(client, function_name, tool_name, tool_args):
    """Invoke MCP tool via HTTP API Gateway event format."""
    mcp_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": tool_args},
        "id": 1,
    }
    event = {
        "version": "2.0",
        "routeKey": "POST /",
        "rawPath": "/",
        "rawQueryString": "",
        "headers": {
            "content-type": "application/json",
            "accept": "application/json, text/event-stream",
        },
        "requestContext": {"http": {"method": "POST", "path": "/", "protocol": "HTTP/1.1"}},
        "body": json.dumps(mcp_request),
        "isBase64Encoded": False,
    }
    response = client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(event).encode(),
    )
    payload = json.loads(response["Payload"].read())
    if "body" in payload:
        body = json.loads(payload["body"]) if isinstance(payload["body"], str) else payload["body"]
        if "result" in body and "content" in body["result"]:
            return json.loads(body["result"]["content"][0]["text"])
    return payload


def run_demo():
    print("=" * 60)
    print("PRIOR AUTH AUTOPILOT - END-TO-END DEMO")
    print(f"Lambda: {MCP_LAMBDA} | FHIR: {FHIR_BASE_URL}")
    print("=" * 60)

    client = boto3.client("lambda", region_name=AWS_REGION)
    results = []
    total_start = time.time()

    for i, scenario in enumerate(SCENARIOS, 1):
        print(f"\n[{i}/3] {scenario['name']}")
        start = time.time()
        try:
            result = invoke_mcp_tool(
                client, MCP_LAMBDA, "evaluate_criteria",
                {
                    "patient_id": scenario["patient_id"],
                    "criteria_set_id": scenario["criteria_set_id"],
                    "fhir_token": scenario["fhir_token"],
                },
            )
            elapsed = time.time() - start
            decision = result.get("overall_decision", "ERROR")
            summary = result.get("clinical_summary", "")
            citations = result.get("fhir_citations", [])
            match = decision == scenario["expected"]
            print(f"  Decision: {decision} | Expected: {scenario['expected']} | {'PASS' if match else 'FAIL'}")
            print(f"  Summary: {summary}")
            print(f"  Citations: {len(citations)} FHIR resources | Time: {elapsed:.1f}s")
            results.append({"pass": match, "elapsed": elapsed})
        except Exception as e:
            elapsed = time.time() - start
            print(f"  ERROR: {e} | Time: {elapsed:.1f}s")
            results.append({"pass": False, "elapsed": elapsed})

    total = time.time() - total_start
    passed = sum(1 for r in results if r["pass"])
    print(f"\nRESULTS: {passed}/{len(results)} passed | Total: {total:.1f}s | Avg: {total/len(results):.1f}s/case")
    return passed == len(results)


if __name__ == "__main__":
    exit(0 if run_demo() else 1)
