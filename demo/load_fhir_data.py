#!/usr/bin/env python3
"""
load_fhir_data.py
Loads synthetic FHIR R4 patient data into a HAPI FHIR server.
Creates 3 transaction bundles covering all test scenarios.

Usage:
    FHIR_BASE_URL=http://localhost:8080/fhir python demo/load_fhir_data.py
"""

import json
import os
import requests

FHIR_BASE_URL = os.environ.get("FHIR_BASE_URL", "http://localhost:8080/fhir")

# ─── Scenario A: Mary Johnson — APPROVE (RA, BCBS Arkansas) ──────────────────
MARY_JOHNSON_BUNDLE = {
    "resourceType": "Bundle",
    "type": "transaction",
    "entry": [
        {
            "resource": {
                "resourceType": "Patient",
                "id": "patient-mary-johnson",
                "name": [{"family": "Johnson", "given": ["Mary"]}],
                "birthDate": "1968-04-15",
                "gender": "female",
            },
            "request": {"method": "PUT", "url": "Patient/patient-mary-johnson"},
        },
        {
            "resource": {
                "resourceType": "Condition",
                "id": "cond-mary-ra",
                "subject": {"reference": "Patient/patient-mary-johnson"},
                "code": {
                    "coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "M05.79", "display": "Rheumatoid arthritis with rheumatoid factor of multiple sites"}],
                    "text": "Rheumatoid arthritis (seropositive)",
                },
                "clinicalStatus": {"coding": [{"code": "active"}]},
                "verificationStatus": {"coding": [{"code": "confirmed"}]},
            },
            "request": {"method": "PUT", "url": "Condition/cond-mary-ra"},
        },
        {
            "resource": {
                "resourceType": "MedicationStatement",
                "id": "medstmt-mary-mtx",
                "subject": {"reference": "Patient/patient-mary-johnson"},
                "status": "completed",
                "medicationCodeableConcept": {
                    "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "387381009", "display": "Methotrexate"}],
                    "text": "Methotrexate 15mg weekly x 6 months",
                },
                "effectivePeriod": {"start": "2025-01-01", "end": "2025-07-01"},
            },
            "request": {"method": "PUT", "url": "MedicationStatement/medstmt-mary-mtx"},
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-mary-tb",
                "subject": {"reference": "Patient/patient-mary-johnson"},
                "code": {"coding": [{"system": "http://loinc.org", "code": "54187-1", "display": "QuantiFERON-TB Gold"}], "text": "QuantiFERON-TB Gold"},
                "status": "final",
                "effectiveDateTime": "2025-12-01",
                "valueCodeableConcept": {"coding": [{"code": "LA6577-6", "display": "Negative"}], "text": "Negative"},
            },
            "request": {"method": "PUT", "url": "Observation/obs-mary-tb"},
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-mary-hbv",
                "subject": {"reference": "Patient/patient-mary-johnson"},
                "code": {"text": "Hepatitis B surface antigen (HBsAg)"},
                "status": "final",
                "effectiveDateTime": "2025-12-01",
                "valueCodeableConcept": {"text": "Negative"},
            },
            "request": {"method": "PUT", "url": "Observation/obs-mary-hbv"},
        },
    ],
}

# ─── Scenario B: Robert Chen — DENY (Psoriasis, Aetna, missing step therapy) ─
ROBERT_CHEN_BUNDLE = {
    "resourceType": "Bundle",
    "type": "transaction",
    "entry": [
        {
            "resource": {
                "resourceType": "Patient",
                "id": "patient-robert-chen",
                "name": [{"family": "Chen", "given": ["Robert"]}],
                "birthDate": "1975-09-22",
                "gender": "male",
            },
            "request": {"method": "PUT", "url": "Patient/patient-robert-chen"},
        },
        {
            "resource": {
                "resourceType": "Condition",
                "id": "cond-robert-psoriasis",
                "subject": {"reference": "Patient/patient-robert-chen"},
                "code": {
                    "coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "L40.0", "display": "Psoriasis vulgaris (plaque)"}],
                    "text": "Plaque psoriasis",
                },
                "clinicalStatus": {"coding": [{"code": "active"}]},
                "verificationStatus": {"coding": [{"code": "confirmed"}]},
            },
            "request": {"method": "PUT", "url": "Condition/cond-robert-psoriasis"},
        },
        # NOTE: No MedicationStatement for conventional agents — triggers DENY for step therapy
    ],
}

# ─── Scenario C: Patricia Williams — DENY (RA + positive TB = contraindication)
PATRICIA_WILLIAMS_BUNDLE = {
    "resourceType": "Bundle",
    "type": "transaction",
    "entry": [
        {
            "resource": {
                "resourceType": "Patient",
                "id": "patient-patricia-williams",
                "name": [{"family": "Williams", "given": ["Patricia"]}],
                "birthDate": "1962-11-03",
                "gender": "female",
            },
            "request": {"method": "PUT", "url": "Patient/patient-patricia-williams"},
        },
        {
            "resource": {
                "resourceType": "Condition",
                "id": "cond-patricia-ra",
                "subject": {"reference": "Patient/patient-patricia-williams"},
                "code": {
                    "coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "M05.79", "display": "Rheumatoid arthritis"}],
                    "text": "Rheumatoid arthritis (seropositive)",
                },
                "clinicalStatus": {"coding": [{"code": "active"}]},
                "verificationStatus": {"coding": [{"code": "confirmed"}]},
            },
            "request": {"method": "PUT", "url": "Condition/cond-patricia-ra"},
        },
        {
            "resource": {
                "resourceType": "MedicationStatement",
                "id": "medstmt-patricia-mtx",
                "subject": {"reference": "Patient/patient-patricia-williams"},
                "status": "completed",
                "medicationCodeableConcept": {
                    "coding": [{"code": "387381009", "display": "Methotrexate"}],
                    "text": "Methotrexate 15mg weekly",
                },
                "effectivePeriod": {"start": "2025-03-01", "end": "2025-09-01"},
            },
            "request": {"method": "PUT", "url": "MedicationStatement/medstmt-patricia-mtx"},
        },
        {
            "resource": {
                "resourceType": "Observation",
                "id": "obs-patricia-tb",
                "subject": {"reference": "Patient/patient-patricia-williams"},
                "code": {"coding": [{"system": "http://loinc.org", "code": "54187-1", "display": "QuantiFERON-TB Gold"}], "text": "QuantiFERON-TB Gold"},
                "status": "final",
                "effectiveDateTime": "2025-11-15",
                # POSITIVE TB — triggers contraindication, blocks TNF inhibitor approval
                "valueCodeableConcept": {"coding": [{"code": "10828004", "display": "Positive"}], "text": "Positive"},
            },
            "request": {"method": "PUT", "url": "Observation/obs-patricia-tb"},
        },
    ],
}


def load_bundle(bundle: dict, name: str) -> bool:
    """POST a FHIR transaction bundle to the server."""
    url = f"{FHIR_BASE_URL}"
    headers = {"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"}
    try:
        resp = requests.post(url, json=bundle, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        resources = len(result.get("entry", []))
        print(f"  [{name}] Loaded {resources} resources -> OK")
        return True
    except Exception as e:
        print(f"  [{name}] ERROR: {e}")
        return False


def main():
    print(f"Loading FHIR test data to: {FHIR_BASE_URL}")
    results = [
        load_bundle(MARY_JOHNSON_BUNDLE, "Mary Johnson (Scenario A — APPROVE)"),
        load_bundle(ROBERT_CHEN_BUNDLE, "Robert Chen (Scenario B — DENY)"),
        load_bundle(PATRICIA_WILLIAMS_BUNDLE, "Patricia Williams (Scenario C — DENY/TB)"),
    ]
    loaded = sum(results)
    print(f"\nLoaded {loaded}/3 bundles successfully.")
    print("FHIR server ready for Prior Auth Autopilot demo.")


if __name__ == "__main__":
    main()
