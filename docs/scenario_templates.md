# Prior Auth Autopilot — Payer Criteria Scenario Templates
# Use case: Specialty Biologics Step-Therapy (RA / Psoriasis)

---

## BCBS Arkansas — RA Biologics 2026 (bcbs_biologics_ra_2026)

**Drug class**: TNF inhibitors / Biologics for Rheumatoid Arthritis
**Effective**: January 1, 2026

### Criteria

1. **Confirmed RA Diagnosis** (REQUIRED)
   - ICD-10: M05.x (seropositive RA) or M06.x (other RA)
   - FHIR resource: Condition
   - Verification: Condition.code.coding.code starts with M05 or M06

2. **Conventional DMARD Trial** (REQUIRED)
   - Documented 6-month trial of methotrexate (preferred) or equivalent DMARD
   - Acceptable DMARDs: MTX, hydroxychloroquine, sulfasalazine, leflunomide
   - FHIR resource: MedicationStatement
   - Verification: MedicationStatement with DMARD code + effectivePeriod >= 6 months

3. **Negative TB Screening** (REQUIRED — CONTRAINDICATION IF POSITIVE)
   - QuantiFERON-TB Gold or TST within 12 months of request
   - LOINC: 54187-1 (QuantiFERON-TB Gold), 71773-6 (TST)
   - FHIR resource: Observation
   - Verification: Observation.valueCodeableConcept = Negative
   - **SAFETY**: Positive result = DENY regardless of other criteria (TNF inhibitors contraindicated)

4. **Negative Hepatitis B Surface Antigen** (REQUIRED)
   - HBsAg within 12 months of request
   - FHIR resource: Observation
   - Verification: Observation with "hepatitis b" in code.text + Negative value

### Decision Logic
- ALL 4 criteria MET + no contraindications = **APPROVE**
- Any criterion NOT_MET = **DENY**
- TB or HBV positive = **DENY** (safety contraindication, overrides step therapy)

---

## Aetna — RA/Psoriasis Biologics 2026 (aetna_biologics_ra_2026)

**Drug class**: Biologics for RA and Plaque Psoriasis
**Effective**: January 1, 2026

### Criteria

1. **Confirmed Diagnosis** (REQUIRED)
   - RA: ICD-10 M05.x or M06.x
   - Plaque psoriasis: ICD-10 L40.0
   - FHIR resource: Condition

2. **Step Therapy — Conventional Agents** (REQUIRED)
   - Documented trial of >= 2 conventional systemic agents
   - RA: MTX + 1 additional DMARD (or DMARD x 2)
   - Psoriasis: methotrexate or cyclosporine or acitretin
   - FHIR resource: MedicationStatement
   - **Denial trigger**: No conventional systemic agent documented = DENY

3. **Disease Activity Score** (REQUIRED)
   - RA: DAS28 > 3.2 (moderate-to-severe disease)
   - Psoriasis: BSA >= 10% or DLQI >= 10
   - FHIR resource: Observation
   - LOINC: disease activity assessment codes

4. **No Active Serious Infection or Malignancy** (REQUIRED)
   - Exclusion: active serious infection, active malignancy within 5 years
   - FHIR resource: Condition (status = active)

### Decision Logic
- All criteria MET = **APPROVE**
- Missing step therapy documentation = **DENY** (most common denial reason)
- Active infection/malignancy = **DENY**

---

## UnitedHealthcare — RA Biologics 2026 (uhc_biologics_ra_2026)

**Drug class**: TNF inhibitors and JAK inhibitors for RA
**Effective**: January 1, 2026

### Criteria

1. **Confirmed RA Diagnosis** (REQUIRED)
   - ICD-10 M05.x or M06.x
   - FHIR resource: Condition

2. **MTX Trial** (REQUIRED unless contraindicated)
   - Methotrexate >= 3 months at adequate dose (>= 15mg/week)
   - Exception: documented MTX contraindication (renal disease, hepatic disease, pregnancy)
   - FHIR resource: MedicationStatement

3. **Negative TB Test** (REQUIRED)
   - Within 12 months of biologic initiation
   - FHIR resource: Observation

4. **Rheumatologist Prescriber** (REQUIRED)
   - Prescribing physician must be board-certified rheumatologist
   - FHIR resource: MedicationRequest.requester
   - Verification: Practitioner resource with specialty = rheumatology

### Decision Logic
- All criteria MET = **APPROVE**
- MTX trial < 3 months (without documented contraindication) = **DENY**

---

## Clinical Test Scenarios

### Scenario A — Mary Johnson — BCBS Arkansas — APPROVE
| Criterion | Status | FHIR Evidence |
|---|---|---|
| Confirmed RA Diagnosis | MET | Condition/cond-mary-ra: M05.79 |
| DMARD Trial (MTX 6mo) | MET | MedicationStatement/medstmt-mary-mtx |
| TB Screening Negative | MET | Observation/obs-mary-tb: QFT Negative |
| HBV Screening Negative | MET | Observation/obs-mary-hbv: HBsAg Negative |
**Decision: APPROVE (confidence 0.95)**

### Scenario B — Robert Chen — Aetna — DENY
| Criterion | Status | FHIR Evidence |
|---|---|---|
| Confirmed Psoriasis Dx | MET | Condition/cond-robert-psoriasis: L40.0 |
| Conventional Agent Trial | NOT_MET | No MedicationStatement found |
| Disease Activity Score | UNKNOWN | No DAS/BSA observation found |
| No Active Infection | MET | No active infection conditions |
**Decision: DENY — Missing step-therapy (confidence 0.90)**

### Scenario C — Patricia Williams — BCBS Arkansas — DENY (Safety)
| Criterion | Status | FHIR Evidence |
|---|---|---|
| Confirmed RA Diagnosis | MET | Condition/cond-patricia-ra: M05.79 |
| DMARD Trial (MTX) | MET | MedicationStatement/medstmt-patricia-mtx |
| TB Screening | CONTRAINDICATION | Observation/obs-patricia-tb: QFT POSITIVE |
| HBV Screening | UNKNOWN | Not found |
**Decision: DENY — Safety contraindication: Positive TB test (confidence 0.97)**
**Note: TB positive overrides all other criteria — TNF inhibitors contraindicated**

---

## FHIR R4 Resources Used

| Resource | Purpose | Key Fields |
|---|---|---|
| Patient | Patient identity | id, name, birthDate, gender |
| Condition | Diagnoses | code (ICD-10), clinicalStatus, verificationStatus |
| MedicationStatement | Drug history | medicationCodeableConcept, effectivePeriod, status |
| Observation | Lab/screening results | code (LOINC), valueCodeableConcept, effectiveDateTime |
| MedicationRequest | Prescription | medication, requester, authoredOn |

---

## EvidenceGrid Output Schema

The MCP evaluate_criteria tool returns an EvidenceGrid JSON:

```json
{
  "patient_id": "string",
  "criteria_set_id": "string",
  "payer": "string",
  "overall_decision": "APPROVE | DENY | APPROVE_VIA_EXCEPTION | NEEDS_MORE_INFO",
  "confidence_score": 0.0-1.0,
  "clinical_summary": "string",
  "criteria_results": [
    {
      "criterion_id": "string",
      "criterion_name": "string",
      "status": "MET | NOT_MET | UNKNOWN | CONTRAINDICATION",
      "fhir_evidence": "ResourceType/id: description",
      "notes": "string",
      "contraindication": false
    }
  ],
  "fhir_citations": ["ResourceType/id", ...]
}
```
