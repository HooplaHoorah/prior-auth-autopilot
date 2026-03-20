# Prior Auth Autopilot — DevPost Submission Guide

> DevPost Agents Assemble 2026 | Judges' Companion Document

## Quick Links

- **Live Demo**: https://4ytrnqnxpl.execute-api.us-east-1.amazonaws.com/
- **GitHub**: https://github.com/HooplaHoorah/prior-auth-autopilot

## Project Summary

Prior Auth Autopilot automates prior authorization decisions for specialty biologics (Humira/Enbrel step-therapy for RA and psoriasis). It demonstrates all three required platform capabilities — MCP, A2A, and FHIR R4 — on real AWS infrastructure with a one-click demo portal. Live result: 3/3 scenarios, 100% accuracy, ~12-14s end-to-end.

## Judging Criteria Mapping

### Technical Implementation (MCP + A2A + FHIR)

- **MCP Server**: criteria_composer_mcp.py — FastMCP Python on AWS Lambda. Tools: evaluate_criteria, list_criteria_sets, get_criteria_detail
- **A2A Agent**: Registered on Prompt Opinion as "Prior Auth Autopilot (Default)" v2.1 with prior_auth_evaluation skill, MCP endpoint connected
- **FHIR R4**: HAPI FHIR R4 on AWS EC2. 16 synthetic resources across 3 transaction bundles. MCP fetches Patient, Condition, MedicationStatement, Observation, MedicationRequest
- **SHARP Extension**: Patient context (patient_id, fhir_token) propagated via SHARP SDK — never hardcoded

### Healthcare Relevance

Prior authorization is one of healthcare's most burdensome administrative processes. This targets specialty biologics step-therapy — the highest-volume, highest-cost PA category. Biologics (Humira, Enbrel, Remicade) represent ~40% of all specialty drug PA requests.

### Innovation

- Full MCP + A2A + FHIR R4 stack in a single working system (not a prototype)
- Evidence Grid: each payer criterion maps to MET/NOT_MET/UNKNOWN + FHIR citation
- Contraindication-bypass logic (TB test positive overrides step-therapy approval)
- SHARP-native: patient context injected by platform, never hardcoded
- Claude Sonnet 4.6 as the clinical reasoning engine

## Architecture Flow

Physician clicks button
-> Demo Portal (API Gateway + Lambda)
-> [1] Lambda wakes HAPI FHIR EC2 server
-> [2] Criteria Composer MCP (Lambda/FastMCP)
       evaluate_criteria(patient_id, criteria_set_id, fhir_token)
       - Fetches FHIR R4 bundle
       - Checks each criterion against FHIR evidence
       - Returns EvidenceGrid JSON
-> [3] AWS Bedrock / Claude Sonnet 4.6
       Synthesizes clinical rationale
       Renders APPROVE / DENY decision
-> Decision + citations displayed in portal

## Test Scenarios (3/3 Accuracy)

- Scenario A: Mary Johnson, RA, BCBS Arkansas -> APPROVE (all 4 criteria met)
- Scenario B: Robert Chen, Psoriasis, Aetna -> DENY (missing step therapy)
- Scenario C: Patricia Williams, RA + TB Risk, BCBS -> DENY (safety contraindication)

## Live Infrastructure

- Demo Portal: https://4ytrnqnxpl.execute-api.us-east-1.amazonaws.com/
- MCP Lambda: criteria-composer-mcp (us-east-1)
- HAPI FHIR: EC2 t3.medium, auto-wakeup via Lambda
- Prompt Opinion Agent: "Prior Auth Autopilot (Default)" v2.1
- Bedrock: Claude Sonnet 4.6, us-east-1

## Key Files for Judges

- mcp/criteria_composer_mcp.py — Core PA logic (payer criteria, FHIR queries, evidence grid)
- demo/prior_auth_autopilot_fhir_demo.py — End-to-end test runner
- demo/load_fhir_data.py — Synthetic FHIR data loader
- fhir/*.json — FHIR transaction bundles (3 clinical scenarios)
- docs/scenario_templates.md — Payer criteria reference

## Submission Checklist

- [x] GitHub repo public
- [x] Live demo URL active
- [x] MCP server deployed and responding
- [x] A2A agent registered on Prompt Opinion
- [x] FHIR R4 integration live
- [x] SHARP Extension referenced in code
- [ ] 3-minute demo video (to record)
- [ ] DevPost project page (to submit)

---
DevPost Agents Assemble 2026 — Prior Auth Autopilot
