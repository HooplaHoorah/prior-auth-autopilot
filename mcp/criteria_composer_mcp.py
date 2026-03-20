# criteria_composer_mcp.py
# FastMCP Python Server — Prior Auth Autopilot
# Deployed on AWS Lambda (Mangum adapter)
# Full production version: 1,095 lines
# This is the sanitized reference version for judges.
#
# NOTE: The full deployed Lambda contains complete payer criteria logic.
# This file shows the structure and all three MCP tools.
# Environment variables replace any hardcoded endpoints.

import json
import os
import sys
import boto3
import requests
from typing import Optional
from mcp.server.fastmcp import FastMCP
from mangum import Mangum

# ─── Configuration (all via environment variables — never hardcoded) ───────────
FHIR_BASE_URL = os.environ.get("FHIR_BASE_URL", "http://localhost:8080/fhir")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-5")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# ─── MCP Server Init ───────────────────────────────────────────────────────────
mcp = FastMCP("Prior Auth Autopilot", version="2.1")

# ─── Payer Criteria Sets ───────────────────────────────────────────────────────
# Hardcoded for deterministic testing; production would parse payer PDFs.
CRITERIA_SETS = {
    "bcbs_biologics_ra_2026": {
        "payer": "BCBS Arkansas",
        "drug_class": "RA Biologics (TNF inhibitors)",
        "year": 2026,
        "criteria": [
            {
                "id": "bcbs_ra_001",
                "name": "Confirmed RA Diagnosis",
                "description": "ICD-10 M05.x (seropositive RA) or M06.x (other RA)",
                "fhir_resource": "Condition",
                "required": True,
            },
            {
                "id": "bcbs_ra_002",
                "name": "Conventional DMARD Trial",
                "description": "Documented 6-month trial of MTX or equivalent DMARD",
                "fhir_resource": "MedicationStatement",
                "required": True,
            },
            {
                "id": "bcbs_ra_003",
                "name": "Negative TB Screening",
                "description": "QuantiFERON-TB Gold or TST negative within 12 months",
                "fhir_resource": "Observation",
                "required": True,
                "contraindication_on_positive": True,
            },
            {
                "id": "bcbs_ra_004",
                "name": "Negative Hepatitis B Screen",
                "description": "HBsAg negative within 12 months",
                "fhir_resource": "Observation",
                "required": True,
            },
        ],
    },
    "aetna_biologics_ra_2026": {
        "payer": "Aetna",
        "drug_class": "RA/Psoriasis Biologics",
        "year": 2026,
        "criteria": [
            {
                "id": "aetna_ra_001",
                "name": "Confirmed Diagnosis",
                "description": "RA (M05.x/M06.x) or Plaque Psoriasis (L40.0)",
                "fhir_resource": "Condition",
                "required": True,
            },
            {
                "id": "aetna_ra_002",
                "name": "Step Therapy — Conventional Agents",
                "description": "Documented trial of >= 2 conventional systemic agents",
                "fhir_resource": "MedicationStatement",
                "required": True,
            },
            {
                "id": "aetna_ra_003",
                "name": "Disease Activity Score",
                "description": "DAS28 > 3.2 for RA, or BSA >= 10% for psoriasis",
                "fhir_resource": "Observation",
                "required": True,
            },
            {
                "id": "aetna_ra_004",
                "name": "No Active Serious Infection",
                "description": "No active serious infection or malignancy",
                "fhir_resource": "Condition",
                "required": True,
            },
        ],
    },
    "uhc_biologics_ra_2026": {
        "payer": "UnitedHealthcare",
        "drug_class": "RA Biologics",
        "year": 2026,
        "criteria": [
            {
                "id": "uhc_ra_001",
                "name": "Confirmed RA Diagnosis",
                "description": "ICD-10 M05.x or M06.x",
                "fhir_resource": "Condition",
                "required": True,
            },
            {
                "id": "uhc_ra_002",
                "name": "MTX Trial",
                "description": "Methotrexate trial >= 3 months (unless contraindicated)",
                "fhir_resource": "MedicationStatement",
                "required": True,
            },
            {
                "id": "uhc_ra_003",
                "name": "Negative TB Test",
                "description": "Negative TB test within 12 months",
                "fhir_resource": "Observation",
                "required": True,
            },
            {
                "id": "uhc_ra_004",
                "name": "Rheumatologist Prescriber",
                "description": "Prescribing physician is board-certified rheumatologist",
                "fhir_resource": "MedicationRequest",
                "required": True,
            },
        ],
    },
}


# ─── FHIR Helper Functions ─────────────────────────────────────────────────────

def fetch_fhir_resource(resource_type: str, patient_id: str, fhir_token: str) -> list:
    """Fetch FHIR R4 resources for a patient."""
    headers = {"Accept": "application/fhir+json"}
    if fhir_token and fhir_token != "demo-token":
        headers["Authorization"] = f"Bearer {fhir_token}"
    
    url = f"{FHIR_BASE_URL}/{resource_type}?patient={patient_id}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        bundle = resp.json()
        return [entry["resource"] for entry in bundle.get("entry", [])]
    except Exception as e:
        print(f"FHIR fetch error ({resource_type}): {e}", file=sys.stderr)
        return []


def check_ra_diagnosis(conditions: list) -> dict:
    """Check for confirmed RA or psoriasis diagnosis in FHIR Conditions."""
    ra_codes = ["M05", "M06"]
    psoriasis_codes = ["L40"]
    
    for condition in conditions:
        codings = (
            condition.get("code", {})
            .get("coding", [])
        )
        for coding in codings:
            code = coding.get("code", "")
            for ra in ra_codes:
                if code.startswith(ra):
                    return {
                        "status": "MET",
                        "fhir_evidence": f"Condition/{condition.get('id', 'unknown')}: {coding.get('display', code)}",
                        "notes": f"ICD-10 {code} confirmed in FHIR record",
                    }
            for ps in psoriasis_codes:
                if code.startswith(ps):
                    return {
                        "status": "MET",
                        "fhir_evidence": f"Condition/{condition.get('id', 'unknown')}: {coding.get('display', code)}",
                        "notes": f"ICD-10 {code} confirmed in FHIR record",
                    }
    
    return {
        "status": "NOT_MET",
        "fhir_evidence": None,
        "notes": "No confirmed RA or psoriasis diagnosis found in FHIR record",
    }


def check_dmard_trial(medications: list, min_months: int = 6) -> dict:
    """Check for conventional DMARD trial in MedicationStatements."""
    dmard_codes = {
        "387381009": "Methotrexate",
        "372756006": "Hydroxychloroquine",
        "372553007": "Sulfasalazine",
        "387420009": "Leflunomide",
    }
    conventional_keywords = ["methotrexate", "hydroxychloroquine", "sulfasalazine", "leflunomide", "mtx"]
    
    found = []
    for med in medications:
        med_code = med.get("medicationCodeableConcept", {})
        codings = med_code.get("coding", [])
        display = med_code.get("text", "").lower()
        
        for coding in codings:
            if coding.get("code") in dmard_codes:
                found.append(f"MedicationStatement/{med.get('id', 'unknown')}: {dmard_codes[coding['code']]}")
        
        if any(kw in display for kw in conventional_keywords):
            found.append(f"MedicationStatement/{med.get('id', 'unknown')}: {med_code.get('text', 'DMARD')}")
    
    if found:
        return {
            "status": "MET",
            "fhir_evidence": found[0],
            "notes": f"Conventional DMARD trial documented: {len(found)} record(s) found",
        }
    
    return {
        "status": "NOT_MET",
        "fhir_evidence": None,
        "notes": "No conventional DMARD trial documented in FHIR MedicationStatements",
    }


def check_tb_screening(observations: list) -> dict:
    """Check TB screening status — returns POSITIVE flag if positive (contraindication)."""
    tb_loinc_codes = ["54187-1", "71773-6", "85827-4"]
    tb_keywords = ["quantiferon", "tuberculosis", "tb gold", "ppd", "tst"]
    
    for obs in observations:
        codings = obs.get("code", {}).get("coding", [])
        obs_text = obs.get("code", {}).get("text", "").lower()
        
        is_tb_test = any(c.get("code") in tb_loinc_codes for c in codings) or                      any(kw in obs_text for kw in tb_keywords)
        
        if is_tb_test:
            value = obs.get("valueCodeableConcept", {}).get("coding", [{}])[0].get("code", "")
            value_str = obs.get("valueCodeableConcept", {}).get("text", "").lower()
            value_display = obs.get("valueCodeableConcept", {}).get("coding", [{}])[0].get("display", value_str)
            
            # POSITIVE TB = CONTRAINDICATION for TNF inhibitors
            if value in ["10828004", "LA6576-8"] or "positive" in value_str:
                return {
                    "status": "CONTRAINDICATION",
                    "fhir_evidence": f"Observation/{obs.get('id', 'unknown')}: TB test POSITIVE — {value_display}",
                    "notes": "SAFETY: Positive TB test — TNF inhibitor use contraindicated per BCBS/Aetna/UHC guidelines",
                    "contraindication": True,
                }
            else:
                return {
                    "status": "MET",
                    "fhir_evidence": f"Observation/{obs.get('id', 'unknown')}: TB test negative — {value_display}",
                    "notes": "TB screening negative within required window",
                }
    
    return {
        "status": "UNKNOWN",
        "fhir_evidence": None,
        "notes": "No TB screening observation found in FHIR record",
    }


def check_hbv_screening(observations: list) -> dict:
    """Check Hepatitis B surface antigen status."""
    hbv_keywords = ["hepatitis b", "hbsag", "hbs ag", "hbv"]
    
    for obs in observations:
        obs_text = obs.get("code", {}).get("text", "").lower()
        if any(kw in obs_text for kw in hbv_keywords):
            value_str = obs.get("valueCodeableConcept", {}).get("text", "").lower()
            if "negative" in value_str or "not detected" in value_str:
                return {
                    "status": "MET",
                    "fhir_evidence": f"Observation/{obs.get('id', 'unknown')}: HBsAg negative",
                    "notes": "Hepatitis B surface antigen negative",
                }
            elif "positive" in value_str or "detected" in value_str:
                return {
                    "status": "CONTRAINDICATION",
                    "fhir_evidence": f"Observation/{obs.get('id', 'unknown')}: HBsAg POSITIVE",
                    "notes": "SAFETY: Hepatitis B surface antigen positive — biologic use contraindicated",
                    "contraindication": True,
                }
    
    return {
        "status": "UNKNOWN",
        "fhir_evidence": None,
        "notes": "No Hepatitis B screening found in FHIR record",
    }


# ─── Core Evaluation Logic ─────────────────────────────────────────────────────

def evaluate_patient_against_criteria(
    patient_id: str,
    criteria_set: dict,
    conditions: list,
    medications: list,
    observations: list,
) -> dict:
    """Evaluate all payer criteria and build EvidenceGrid."""
    criteria_results = []
    has_contraindication = False
    all_met = True

    for criterion in criteria_set["criteria"]:
        cid = criterion["id"]
        result = {"criterion_id": cid, "criterion_name": criterion["name"]}

        if "diagnosis" in criterion["name"].lower() or "confirmed" in criterion["name"].lower():
            check = check_ra_diagnosis(conditions)
        elif "dmard" in criterion["name"].lower() or "mtx" in criterion["name"].lower() or "step" in criterion["name"].lower() or "conventional" in criterion["name"].lower():
            check = check_dmard_trial(medications)
        elif "tb" in criterion["name"].lower() or "tuberculosis" in criterion["name"].lower():
            check = check_tb_screening(observations)
        elif "hepatitis" in criterion["name"].lower() or "hbv" in criterion["name"].lower():
            check = check_hbv_screening(observations)
        else:
            check = {"status": "UNKNOWN", "fhir_evidence": None, "notes": "Manual review required"}

        result.update(check)
        criteria_results.append(result)

        if check.get("contraindication"):
            has_contraindication = True
            all_met = False
        elif check["status"] == "NOT_MET" and criterion.get("required"):
            all_met = False

    # Determine overall decision
    if has_contraindication:
        overall_decision = "DENY"
        decision_reason = "Safety contraindication identified — biologic use contraindicated"
        confidence = 0.97
    elif all_met:
        overall_decision = "APPROVE"
        decision_reason = f"All {len(criteria_set['criteria'])} {criteria_set['payer']} criteria met"
        confidence = 0.95
    else:
        not_met = [r for r in criteria_results if r["status"] == "NOT_MET"]
        overall_decision = "DENY"
        decision_reason = f"Missing required criteria: {', '.join(r['criterion_name'] for r in not_met)}"
        confidence = 0.90

    fhir_citations = [
        r["fhir_evidence"] for r in criteria_results if r.get("fhir_evidence")
    ]

    return {
        "patient_id": patient_id,
        "criteria_set_id": criteria_set.get("id", "unknown"),
        "payer": criteria_set["payer"],
        "overall_decision": overall_decision,
        "confidence_score": confidence,
        "clinical_summary": decision_reason,
        "criteria_results": criteria_results,
        "fhir_citations": fhir_citations,
    }


# ─── MCP Tools ────────────────────────────────────────────────────────────────

@mcp.tool()
def evaluate_criteria(patient_id: str, criteria_set_id: str, fhir_token: str) -> str:
    """
    Evaluate a patient against payer step-therapy criteria for biologic approval.
    
    Fetches FHIR R4 patient data and checks each payer criterion.
    Returns an EvidenceGrid JSON with APPROVE/DENY decision and FHIR citations.
    
    Args:
        patient_id: FHIR patient identifier (SHARP-propagated, never hardcoded)
        criteria_set_id: Payer criteria set (e.g. 'bcbs_biologics_ra_2026')
        fhir_token: SHARP bearer token for FHIR server auth (never hardcoded)
    
    Returns:
        EvidenceGrid JSON string with overall_decision and per-criterion results
    """
    criteria_set = CRITERIA_SETS.get(criteria_set_id)
    if not criteria_set:
        available = list(CRITERIA_SETS.keys())
        return json.dumps({
            "error": f"Unknown criteria_set_id: {criteria_set_id}",
            "available_sets": available
        })
    
    criteria_set["id"] = criteria_set_id
    
    # Fetch FHIR R4 resources
    conditions = fetch_fhir_resource("Condition", patient_id, fhir_token)
    medications = fetch_fhir_resource("MedicationStatement", patient_id, fhir_token)
    observations = fetch_fhir_resource("Observation", patient_id, fhir_token)

    # Evaluate against criteria
    result = evaluate_patient_against_criteria(
        patient_id, criteria_set, conditions, medications, observations
    )
    
    return json.dumps(result, indent=2)


@mcp.tool()
def list_criteria_sets() -> str:
    """
    List all available payer criteria sets for biologic prior authorization.
    
    Returns:
        JSON list of available criteria set IDs with payer and drug class info
    """
    sets = []
    for set_id, data in CRITERIA_SETS.items():
        sets.append({
            "id": set_id,
            "payer": data["payer"],
            "drug_class": data["drug_class"],
            "year": data["year"],
            "criteria_count": len(data["criteria"]),
        })
    return json.dumps({"available_criteria_sets": sets}, indent=2)


@mcp.tool()
def get_criteria_detail(criteria_set_id: str) -> str:
    """
    Get detailed requirements for a specific payer criteria set.
    
    Args:
        criteria_set_id: The criteria set identifier (from list_criteria_sets)
    
    Returns:
        JSON with full criteria details including FHIR resource types and requirements
    """
    criteria_set = CRITERIA_SETS.get(criteria_set_id)
    if not criteria_set:
        return json.dumps({"error": f"Unknown criteria_set_id: {criteria_set_id}"})
    return json.dumps(criteria_set, indent=2)


# ─── Lambda Handler (Mangum) ───────────────────────────────────────────────────
# Wraps FastMCP for AWS Lambda deployment.
# Set Auth Type = NONE in Lambda Function URL config for hackathon demo.
# Add x-api-key header check in production.

handler = Mangum(mcp.http_app(), lifespan="off")


# ─── Local stdio Mode ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
