# Prior Auth Autopilot

> **DevPost Agents Assemble 2026** — The Healthcare AI Endgame Challenge
> > Build Interoperable Healthcare Agents at the Intersection of MCP, A2A, and FHIR
> >
> > [![Live Demo](https://img.shields.io/badge/Live%20Demo-Online-brightgreen)](https://4ytrnqnxpl.execute-api.us-east-1.amazonaws.com/)
> > [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
> > [![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
> > [![FHIR R4](https://img.shields.io/badge/FHIR-R4-orange.svg)](https://hl7.org/fhir/R4/)
> >
> > ---
> >
> > ## What It Does
> >
> > **Prior Auth Autopilot** automates the prior authorization (PA) decision workflow for specialty biologics (step-therapy use case: Humira/Enbrel for RA and psoriasis).
> >
> > A physician clicks one button. The system:
> > 1. Wakes a HAPI FHIR R4 server (via AWS Lambda warmup)
> > 2. 2. Fetches the patient's clinical record (Condition, MedicationStatement, Observation, MedicationRequest)
> >    3. 3. Calls the **Criteria Composer MCP server** (`evaluate_criteria` tool) with patient data + payer criteria set
> >       4. 4. The MCP server queries the FHIR bundle and checks it against hardcoded payer step-therapy rules (UHC, Aetna, BCBS Arkansas)
> >          5. 5. **Claude Sonnet 4.6** on AWS Bedrock synthesizes the evidence grid and renders an APPROVE / DENY / APPROVE_VIA_EXCEPTION decision with clinical rationale
> >             6. 6. Decision + evidence grid is returned to the demo portal in ~12–14 seconds end-to-end
> >               
> >                7. **Live result: 3/3 scenarios, 100% accuracy.**
> >               
> >                8. ---
> >               
> >                9. ## Live Demo
> >
> > 🔗 **Demo Portal**: https://4ytrnqnxpl.execute-api.us-east-1.amazonaws.com/
> >
> > Three pre-loaded test scenarios:
> > | Patient | Payer | Drug | Expected | Result |
> > |---|---|---|---|---|
> > | Mary Johnson | BCBS Arkansas | RA Biologic | APPROVE | ✅ APPROVE |
> > | Robert Chen | Aetna | Psoriasis Biologic | DENY | ✅ DENY |
> > | Patricia Williams | BCBS Arkansas | RA Biologic + TB Risk | DENY | ✅ DENY |
> >
> > ---
> >
> > ## Architecture
> >
> > ```
> > ┌─────────────────────────────────────────────────────────┐
> > │                  Demo Portal (HTML/JS)                   │
> > │         AWS API Gateway + Lambda (prior-auth-demo)       │
> > └──────────────────────┬──────────────────────────────────┘
> >                        │ HTTP invoke
> >           ┌────────────▼────────────┐
> >           │   AWS Lambda            │
> >           │   criteria-composer-mcp │
> >           │   (FastMCP Python)      │
> >           │                         │
> >           │  Tools exposed:         │
> >           │  • evaluate_criteria()  │
> >           │  • list_criteria_sets() │
> >           │  • get_criteria_detail()│
> >           └────────┬────────────────┘
> >                    │ MCP tool call
> >      ┌─────────────▼──────────────────┐
> >      │  AWS Bedrock                   │
> >      │  Claude Sonnet 4.6             │
> >      │  (clinical reasoning engine)   │
> >      └─────────────┬──────────────────┘
> >                    │ FHIR R4 query
> >      ┌─────────────▼──────────────────┐
> >      │  HAPI FHIR R4 Server           │
> >      │  AWS EC2 (t3.medium)           │
> >      │  Port 8080 — in-memory H2 DB   │
> >      │  16 synthetic FHIR resources   │
> >      └────────────────────────────────┘
> > ```
> >
> > **Platform integrations:**
> > - **Prompt Opinion** — A2A agent ("Prior Auth Autopilot") with `prior_auth_evaluation` skill, MCP-connected
> > - - **SHARP Extension** — Patient context + FHIR token propagation (never hardcoded)
> >  
> >   - ---
> >
> > ## Tech Stack
> >
> > | Layer | Technology |
> > |---|---|
> > | LLM | Claude Sonnet 4.6 via AWS Bedrock |
> > | MCP Server | FastMCP Python (AWS Lambda) |
> > | Agent Platform | Prompt Opinion (A2A, SHARP) |
> > | FHIR Server | HAPI FHIR R4 (EC2, Docker) |
> > | Demo Portal | AWS API Gateway + Lambda (Python) |
> > | FHIR Data | Synthea-style synthetic patients |
> > | Use Case | Specialty Biologics Step-Therapy (RA / Psoriasis) |
> > | Payer Criteria | UHC, Aetna, BCBS Arkansas (RA biologics 2026) |
> >
> > ---
> >
> > ## Repository Structure
> >
> > ```
> > prior-auth-autopilot/
> > ├── README.md                          # This file
> > ├── DEVPOST_SUBMISSION.md              # Judges' companion doc
> > ├── LICENSE                            # MIT
> > ├── .gitignore                         # Python
> > │
> > ├── mcp/
> > │   └── criteria_composer_mcp.py       # FastMCP server — core PA logic (1,095 lines)
> > │
> > ├── demo/
> > │   ├── prior_auth_autopilot_fhir_demo.py   # Production end-to-end demo script
> > │   ├── load_fhir_data.py                   # FHIR R4 data loader (transaction bundles)
> > │   ├── prior_auth_autopilot_demo.py        # Lambda demo portal handler
> > │   └── lambda_wakeup/
> > │       └── lambda_function.py             # EC2 auto-start Lambda
> > │
> > ├── fhir/
> > │   ├── mary_johnson_bundle.json       # Scenario A: APPROVE (RA, BCBS)
> > │   ├── robert_chen_bundle.json        # Scenario B: DENY (Psoriasis, Aetna)
> > │   └── patricia_williams_bundle.json  # Scenario C: DENY (RA + TB risk, BCBS)
> > │
> > └── docs/
> >     └── scenario_templates.md          # Payer criteria scenario reference
> > ```
> >
> > ---
> >
> > ## Key Files
> >
> > ### `mcp/criteria_composer_mcp.py`
> > The heart of the system. A **FastMCP Python server** that:
> > - Exposes 3 MCP tools: `evaluate_criteria`, `list_criteria_sets`, `get_criteria_detail`
> > - - Hardcodes payer step-therapy criteria for UHC, Aetna, BCBS Arkansas (RA biologics)
> >   - - Fetches FHIR R4 patient data (Patient, Condition, MedicationStatement, Observation, MedicationRequest)
> >     - - Builds an evidence grid: each criterion → MET / NOT_MET / UNKNOWN + FHIR citation
> >       - - Returns structured `EvidenceGrid` JSON to the LLM
> >         - - Supports both `stdio` and HTTP transport (Mangum adapter for AWS Lambda)
> >           - - Includes contraindication-bypass logic (Scenario C: TB test positive)
> >            
> >             - ### `demo/prior_auth_autopilot_fhir_demo.py`
> >             - End-to-end demo runner. Invokes the MCP Lambda directly via boto3 (HTTP API Gateway event format), runs all 3 scenarios, prints timing + accuracy.
> >            
> >             - ### `demo/load_fhir_data.py`
> >             - Loads 16 synthetic FHIR R4 resources (3 transaction bundles) into the HAPI FHIR server.
> >            
> >             - ---
> >
> > ## MCP Tool Specification
> >
> > ### `evaluate_criteria(patient_id, criteria_set_id, fhir_token)`
> >
> > **Input:**
> > ```json
> > {
> >   "patient_id": "patient-mary-johnson",
> >   "criteria_set_id": "bcbs_biologics_ra_2026",
> >   "fhir_token": "<SHARP-propagated bearer token>"
> > }
> > ```
> >
> > **Output — EvidenceGrid JSON:**
> > ```json
> > {
> >   "patient_id": "patient-mary-johnson",
> >   "criteria_set_id": "bcbs_biologics_ra_2026",
> >   "overall_decision": "APPROVE",
> >   "confidence_score": 0.95,
> >   "criteria_results": [
> >     {
> >       "criterion_id": "bcbs_ra_001",
> >       "criterion_name": "Confirmed RA Diagnosis",
> >       "status": "MET",
> >       "fhir_evidence": "Condition/cond-mary-ra: Rheumatoid arthritis (M05.79)",
> >       "notes": "ICD-10 M05.79 confirmed in FHIR record"
> >     }
> >   ],
> >   "clinical_summary": "All 4 BCBS criteria met: confirmed RA diagnosis, 6-month MTX trial, negative TB/HBV screens, no contraindications",
> >   "fhir_citations": ["Condition/cond-mary-ra", "MedicationStatement/medstmt-mary-mtx"]
> > }
> > ```
> >
> > ### `list_criteria_sets()`
> > Returns available payer criteria templates: `uhc_biologics_ra_2026`, `aetna_biologics_ra_2026`, `bcbs_biologics_ra_2026`
> >
> > ### `get_criteria_detail(criteria_set_id)`
> > Returns individual criterion requirements for a given payer criteria set.
> >
> > ---
> >
> > ## Setup & Deployment
> >
> > ### Prerequisites
> > - Python 3.11+
> > - - AWS account with Bedrock access (Claude Sonnet 4.6, us-east-1)
> >   - - HAPI FHIR R4 server running (Docker or EC2)
> >    
> >     - ### Environment Variables
> >     - ```bash
> >       # Required
> >       FHIR_BASE_URL=http://<your-fhir-server>:8080/fhir
> >       AWS_REGION=us-east-1
> >       BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-5   # or claude-sonnet-4-6 when available
> >
> >       # Lambda deployment
> >       MCP_LAMBDA_FUNCTION_NAME=criteria-composer-mcp
> >       DEMO_LAMBDA_FUNCTION_NAME=prior-auth-demo-portal
> >
> >       # Optional
> >       LOG_LEVEL=INFO
> >       ```
> >
> > ### Local Development
> > ```bash
> > # Install dependencies
> > pip install fastmcp boto3 requests mangum
> >
> > # Run MCP server locally (stdio mode)
> > python mcp/criteria_composer_mcp.py
> >
> > # Run demo (requires FHIR server + AWS Bedrock access)
> > python demo/prior_auth_autopilot_fhir_demo.py
> > ```
> >
> > ### Lambda Deployment
> > ```bash
> > # Package MCP server
> > zip -r criteria_composer_mcp.zip mcp/criteria_composer_mcp.py
> >
> > # Deploy via AWS CLI
> > aws lambda update-function-code \
> >   --function-name criteria-composer-mcp \
> >   --zip-file fileb://criteria_composer_mcp.zip
> >
> > # Set Lambda config
> > # Runtime: Python 3.11 | Memory: 512MB | Timeout: 29s | Auth: NONE
> > ```
> >
> > ### Load FHIR Test Data
> > ```bash
> > # Start HAPI FHIR (Docker)
> > docker run -p 8080:8080 hapiproject/hapi:r4
> >
> > # Load synthetic patients
> > python demo/load_fhir_data.py
> > ```
> >
> > ---
> >
> > ## Payer Criteria (Use Case: Specialty Biologics Step-Therapy)
> >
> > ### BCBS Arkansas — RA Biologics 2026
> > 1. Confirmed RA diagnosis (ICD-10 M05.x or M06.x)
> > 2. 2. Documented 6-month trial of conventional DMARD (MTX preferred)
> >    3. 3. Negative TB screening (QuantiFERON or TST) within 12 months
> >       4. 4. Negative Hepatitis B surface antigen
> >         
> >          5. ### Aetna — RA/Psoriasis Biologics 2026
> >          6. 1. Confirmed diagnosis (RA or plaque psoriasis)
> >             2. 2. Step-therapy: documented trial of ≥2 conventional agents
> >                3. 3. Adequate disease activity score (DAS28 > 3.2 for RA)
> >                   4. 4. No active serious infection or malignancy
> >                     
> >                      5. ### UHC — RA Biologics 2026
> >                      6. 1. Confirmed RA diagnosis
> >                         2. 2. Methotrexate trial ≥ 3 months (unless contraindicated)
> >                            3. 3. Negative TB test
> >                               4. 4. Prescriber is rheumatologist
> >                                 
> >                                  5. ---
> >                                 
> >                                  6. ## Clinical Test Scenarios
> >                                 
> >                                  7. ### Scenario A — APPROVE: Mary Johnson (RA, BCBS Arkansas)
> > - **Diagnosis**: Rheumatoid arthritis (M05.79)
> > - - **Step therapy**: 6-month MTX trial documented
> >   - - **Screens**: TB negative, HBV negative
> >     - - **Decision**: ✅ APPROVE — all 4 BCBS criteria met
> >      
> >       - ### Scenario B — DENY: Robert Chen (Psoriasis, Aetna)
> >       - - **Diagnosis**: Plaque psoriasis (L40.0)
> >         - - **Step therapy**: ❌ No documented conventional systemic agent trial
> >           - - **Decision**: ❌ DENY — missing step-therapy requirement
> >            
> >             - ### Scenario C — DENY: Patricia Williams (RA + TB Risk, BCBS Arkansas)
> >             - - **Diagnosis**: Rheumatoid arthritis (M05.79)
> >               - - **Step therapy**: MTX trial documented
> >                 - - **Safety flag**: ⚠️ Positive QuantiFERON-TB Gold — TNF inhibitor contraindicated
> >                   - - **Decision**: ❌ DENY — safety contraindication (contraindication-bypass logic triggered)
> >                    
> >                     - ---
> >
> > ## Prompt Opinion Integration
> >
> > The MCP server is registered as a **Prompt Opinion agent**:
> > - **Agent name**: Prior Auth Autopilot (Default)
> > - - **Version**: 2.1
> >   - - **A2A**: Enabled
> >     - - **Skill**: `prior_auth_evaluation`
> >       - - **Transport**: HTTP (Streamable HTTP POST)
> >         - - **Auth**: x-api-key header (set in Lambda code, not hardcoded in repo)
> >          
> >           - The agent can be invoked by any A2A-compatible orchestrator via the Prompt Opinion Marketplace.
> >          
> >           - ---
> >
> > ## SHARP Extension
> >
> > Patient context (patient ID, FHIR bearer token) is propagated via **Prompt Opinion's SHARP Extension SDK**:
> > ```python
> > from sharp import get_patient_context  # one import
> > # Never hardcode patient IDs or tokens — always receive from platform context
> > ```
> > This is what makes it "healthcare-ready" vs. a toy demo.
> >
> > ---
> >
> > ## Hackathon Context
> >
> > - **Contest**: [DevPost Agents Assemble — The Healthcare AI Endgame](https://agents-assemble.devpost.com/)
> > - - **Deadline**: May 11, 2026 @ 10:00pm CDT
> >   - - **Prize pool**: $25,000
> >     - - **Platform requirement**: Prompt Opinion (SHARP / A2A / MCP)
> >       - - **Use case lane**: Specialty Biologics Step-Therapy (Humira/Enbrel for RA/Psoriasis)
> >        
> >         - ---
> >
> > ## License
> >
> > MIT — see [LICENSE](LICENSE)
> >
> > ---
> >
> > *Built with the AI Party Line (Claude, Grok, Gemini, ChatGPT) + Claude Google Extension for DevPost Agents Assemble 2026.*
