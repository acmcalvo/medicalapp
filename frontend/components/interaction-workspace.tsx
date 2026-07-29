'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  checkInteractions,
  generateAdvice,
  submitReviewSignOff,
  type AdviceResponse,
  type InteractionCheckResponse,
  type Role,
  type ReviewSignOffResponse,
} from '@/lib/api';

type MedicationRow = {
  id: string;
  name: string;
  dose: string;
};

type PatientDraft = {
  age: string;
  pregnancy_status: 'pregnant' | 'not_pregnant' | 'unknown';
  egfr: string;
  liver_impairment: 'none' | 'mild' | 'moderate' | 'severe' | 'unknown';
  allergies: string;
  conditions: string;
};

const initialMedications: MedicationRow[] = [
  { id: 'med-1', name: 'Warfarin', dose: '5 mg daily' },
  { id: 'med-2', name: 'Ibuprofen', dose: '400 mg as needed' },
];

const evidenceBullets = [
  'Normalize medication names before querying the backend interaction engine.',
  'Show all high-severity findings before generating explanation text.',
  'Keep the AI summary constrained to citations and review-ready advice.',
];

const supportedFallbackPairs = [
  'Warfarin + Ibuprofen (including Advil, Motrin)',
  'Warfarin + Ginkgo Biloba',
  'Warfarin + Aspirin',
  'Warfarin + Alcohol',
  'Simvastatin + Clarithromycin (including Biaxin)',
  'Sildenafil (Viagra) + Nitroglycerin/Isosorbide',
  'Linezolid + Sertraline',
  'Digoxin + Amiodarone',
  'Lisinopril + Potassium supplements',
];

const sourceTypeLabelMap: Record<'live_rxcui' | 'external_api' | 'heuristic', string> = {
  live_rxcui: 'Live RxNorm',
  external_api: 'External API',
  heuristic: 'Fallback heuristic',
};

const sourceTypeClassMap: Record<'live_rxcui' | 'external_api' | 'heuristic', string> = {
  live_rxcui: 'source-pill source-live',
  external_api: 'source-pill source-external',
  heuristic: 'source-pill source-heuristic',
};

const severityLabelMap: Record<string, string> = {
  contraindicated: 'Contraindicated',
  major: 'Major',
  moderate: 'Moderate',
  minor: 'Minor',
  none: 'None',
};

const knownHighRiskPairKeywords: Array<[string[], string[]]> = [
  [['warfarin'], ['ibuprofen', 'advil', 'motrin']],
  [['warfarin'], ['ginkgo', 'ginko']],
  [['warfarin'], ['aspirin', 'acetylsalicylic']],
  [['warfarin'], ['alcohol', 'ethanol', 'beer', 'wine', 'whiskey', 'vodka']],
  [['linezolid'], ['sertraline', 'zoloft', 'ssri']],
  [['digoxin'], ['amiodarone']],
  [['lisinopril', 'ace inhibitor'], ['potassium', 'kcl', 'potassium chloride']],
  [['simvastatin'], ['clarithromycin', 'biaxin']],
  [['sildenafil', 'viagra'], ['nitroglycerin', 'isosorbide']],
];

function hasKeywordMatch(names: string[], keywords: string[]) {
  return names.some((name) => keywords.some((keyword) => name.includes(keyword)));
}

const reviewStorageKey = 'medical-app-review-result';
const auditTrailStorageKey = 'medical-app-audit-trail';
const auditVisibilityStorageKey = 'medical-app-audit-visibility';

type AuditEntry = {
  id: string;
  timestamp: string;
  action: string;
  detail: string;
};

export function InteractionWorkspace() {
  const [role, setRole] = useState<Role>('pharmacist');
  const [medications, setMedications] = useState<MedicationRow[]>(initialMedications);
  const [patient, setPatient] = useState<PatientDraft>({
    age: '',
    pregnancy_status: 'unknown',
    egfr: '',
    liver_impairment: 'unknown',
    allergies: '',
    conditions: '',
  });
  const [interactionResult, setInteractionResult] = useState<InteractionCheckResponse | null>(null);
  const [adviceResult, setAdviceResult] = useState<AdviceResponse | null>(null);
  const [reviewResult, setReviewResult] = useState<ReviewSignOffResponse | null>(null);
  const [reviewNote, setReviewNote] = useState('');
  const [auditTrail, setAuditTrail] = useState<AuditEntry[]>([]);
  const [isAuditVisible, setIsAuditVisible] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const hasPotentialInteraction = useMemo(() => {
    const names = medications.map((medication) => medication.name.toLowerCase());
    return knownHighRiskPairKeywords.some(([keywordsA, keywordsB]) => {
      const directMatch = hasKeywordMatch(names, keywordsA) && hasKeywordMatch(names, keywordsB);
      const reverseMatch = hasKeywordMatch(names, keywordsB) && hasKeywordMatch(names, keywordsA);
      return directMatch || reverseMatch;
    });
  }, [medications]);

  const displayedInteractions = interactionResult?.interactions ?? [];
  const usesFallbackEvidence = displayedInteractions.some((interaction) => interaction.source_type === 'heuristic');
  const reviewCaseId = interactionResult?.interactions.length ? 'case-001' : 'case-pending';

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const storedReview = window.localStorage.getItem(reviewStorageKey);
    if (!storedReview) {
      return;
    }

    try {
      setReviewResult(JSON.parse(storedReview) as ReviewSignOffResponse);
    } catch {
      window.localStorage.removeItem(reviewStorageKey);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const storedAuditVisibility = window.localStorage.getItem(auditVisibilityStorageKey);
    if (!storedAuditVisibility) {
      return;
    }

    try {
      setIsAuditVisible(JSON.parse(storedAuditVisibility) as boolean);
    } catch {
      window.localStorage.removeItem(auditVisibilityStorageKey);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const storedAuditTrail = window.localStorage.getItem(auditTrailStorageKey);
    if (!storedAuditTrail) {
      return;
    }

    try {
      setAuditTrail(JSON.parse(storedAuditTrail) as AuditEntry[]);
    } catch {
      window.localStorage.removeItem(auditTrailStorageKey);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    if (reviewResult) {
      window.localStorage.setItem(reviewStorageKey, JSON.stringify(reviewResult));
      return;
    }

    window.localStorage.removeItem(reviewStorageKey);
  }, [reviewResult]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    if (auditTrail.length > 0) {
      window.localStorage.setItem(auditTrailStorageKey, JSON.stringify(auditTrail));
      return;
    }

    window.localStorage.removeItem(auditTrailStorageKey);
  }, [auditTrail]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    window.localStorage.setItem(auditVisibilityStorageKey, JSON.stringify(isAuditVisible));
  }, [isAuditVisible]);

  const updateMedication = (index: number, field: keyof MedicationRow, value: string) => {
    setMedications((current) =>
      current.map((medication, medicationIndex) =>
        medicationIndex === index ? { ...medication, [field]: value } : medication,
      ),
    );
  };

  const addMedication = () => {
    setMedications((current) => [...current, { id: `med-${Date.now()}`, name: '', dose: '' }]);
  };

  const removeMedication = (medicationId: string) => {
    const medication = medications.find((item) => item.id === medicationId);
    const label = medication?.name?.trim() || 'this medication row';
    if (!window.confirm(`Delete ${label}?`)) {
      return;
    }

    setMedications((current) => {
      if (current.length <= 1) {
        return current;
      }
      return current.filter((medication) => medication.id !== medicationId);
    });
  };

  const appendAuditEntry = (action: string, detail: string) => {
    const timestamp = new Date().toISOString();
    setAuditTrail((current) => [
      { id: `${timestamp}-${current.length}`, timestamp, action, detail },
      ...current,
    ]);
  };

  const updatePatient = <K extends keyof PatientDraft>(field: K, value: PatientDraft[K]) => {
    setPatient((current) => ({ ...current, [field]: value }));
  };

  const runInteractionCheck = async () => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const cleanedMedications = medications
        .filter((medication) => medication.name.trim().length > 0)
        .map((medication) => ({
          name_entered: medication.name.trim(),
          dose: medication.dose?.trim() || undefined,
        }));

      const interactionPayload = {
        medications: cleanedMedications,
        patient: {
          age: patient.age.trim() ? Number(patient.age) : undefined,
          pregnancy_status: patient.pregnancy_status,
          egfr: patient.egfr.trim() ? Number(patient.egfr) : undefined,
          liver_impairment: patient.liver_impairment,
          allergies: patient.allergies
            .split(',')
            .map((allergy) => allergy.trim())
            .filter((allergy) => allergy.length > 0),
          conditions: patient.conditions
            .split(',')
            .map((condition) => condition.trim())
            .filter((condition) => condition.length > 0),
        },
      };

      const interactionResponse = await checkInteractions(interactionPayload);
      setInteractionResult(interactionResponse);
      setReviewResult(null);
      const evidenceModes = Array.from(
        new Set(
          interactionResponse.interactions.map((interaction) => sourceTypeLabelMap[interaction.source_type]),
        ),
      );
      appendAuditEntry(
        'Interaction check',
        `Checked ${cleanedMedications.length} medication${cleanedMedications.length === 1 ? '' : 's'} with ${interactionPayload.patient.allergies.length} allergy entr${interactionPayload.patient.allergies.length === 1 ? 'y' : 'ies'} and ${interactionPayload.patient.conditions.length} condition${interactionPayload.patient.conditions.length === 1 ? '' : 's'}; evidence mode: ${evidenceModes.length ? evidenceModes.join(', ') : 'none'}.`,
      );

      if (interactionResponse.interactions.length === 0) {
        setAdviceResult(null);
        appendAuditEntry('Advice skipped', 'No interactions were returned, so clinician advice was not generated.');
        return;
      }

      const adviceResponse = await generateAdvice({
        role,
        interactions: interactionResponse.interactions,
        patient: interactionPayload.patient,
        question: 'Summarize the medication review for clinician sign-off.',
      });
      setAdviceResult(adviceResponse);
      appendAuditEntry('Advice generated', `Generated guidance for role: ${role}.`);
      if (interactionResponse.interactions.some((interaction) => interaction.source_type === 'heuristic')) {
        appendAuditEntry('Provisional evidence', 'Fallback heuristic evidence detected; reviewer rationale is required for approval.');
      }
    } catch (error) {
      setInteractionResult(null);
      setAdviceResult(null);
      appendAuditEntry('Interaction check failed', error instanceof Error ? error.message : 'Unknown error');
      setErrorMessage(error instanceof Error ? error.message : 'Unable to run the interaction check.');
    } finally {
      setIsLoading(false);
    }
  };

  const runSignOff = async (status: 'signed_off' | 'rejected') => {
    if (!interactionResult) {
      setErrorMessage('Run an interaction check before signing off.');
      return;
    }

    if (status === 'signed_off' && usesFallbackEvidence && !reviewNote.trim()) {
      setErrorMessage('Reviewer note is required before approving a case with fallback heuristic evidence.');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const signOffResponse = await submitReviewSignOff({
        case_id: reviewCaseId,
        status,
        role,
        uses_fallback_evidence: usesFallbackEvidence,
        note: reviewNote.trim() || undefined,
      });
      setReviewResult(signOffResponse);
      setReviewNote('');
      appendAuditEntry(
        `Case ${status === 'signed_off' ? 'approved' : 'rejected'}`,
        `Case ${signOffResponse.case_id} recorded at ${new Date(signOffResponse.reviewed_at).toLocaleString()}. Reviewer note ${reviewNote.trim() ? 'captured' : 'not provided'}.`,
      );
    } catch (error) {
      appendAuditEntry('Sign-off failed', error instanceof Error ? error.message : 'Unknown error');
      setErrorMessage(error instanceof Error ? error.message : 'Unable to submit the review sign-off.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="workspace-grid">
      <section className="hero case-hero">
        <div className="eyebrow">Clinical workflow</div>
        <h1>Check medication interactions before generating guidance.</h1>
        <p className="hero-copy">
          This screen is designed for doctor and pharmacist review. It will later connect directly to RxNav, DailyMed,
          RxLabelGuard, and the advice API.
        </p>

        <div className="hero-actions">
          <div className="segmented-control" role="tablist" aria-label="Select review role">
            <button
              className={role === 'pharmacist' ? 'segmented-button active' : 'segmented-button'}
              type="button"
              onClick={() => setRole('pharmacist')}
            >
              Pharmacist
            </button>
            <button
              className={role === 'doctor' ? 'segmented-button active' : 'segmented-button'}
              type="button"
              onClick={() => setRole('doctor')}
            >
              Doctor
            </button>
          </div>

          <button className="primary-button" type="button" onClick={runInteractionCheck} disabled={isLoading}>
            {isLoading ? 'Checking...' : 'Check interactions'}
          </button>
        </div>

        <div className="status-row" aria-label="Key product statuses">
          <span>Role: {role}</span>
          <span>Audit logging ready</span>
          <span>{hasPotentialInteraction ? 'Possible interaction detected' : 'No obvious interaction'}</span>
        </div>
        {errorMessage ? <div className="inline-error">{errorMessage}</div> : null}
      </section>

      <section className="workspace-panel" aria-label="Medication entry form">
        <div className="panel-header">
          <div>
            <p className="panel-label">Medication list</p>
            <h2>Enter the current medications</h2>
          </div>
          <button className="secondary-button compact" type="button" onClick={addMedication}>
            Add medication
          </button>
        </div>

        <div className="medication-list">
          {medications.map((medication, index) => (
            <div className="medication-row" key={medication.id}>
              <label>
                <span>Medication</span>
                <input
                  type="text"
                  value={medication.name}
                  placeholder="e.g. Warfarin"
                  onChange={(event) => updateMedication(index, 'name', event.target.value)}
                />
              </label>
              <label>
                <span>Dose</span>
                <input
                  type="text"
                  value={medication.dose}
                  placeholder="e.g. 5 mg daily"
                  onChange={(event) => updateMedication(index, 'dose', event.target.value)}
                />
              </label>
              <div className="medication-row-actions">
                <button
                  className="secondary-button compact danger-button"
                  type="button"
                  onClick={() => removeMedication(medication.id)}
                  disabled={medications.length <= 1}
                  title={medications.length <= 1 ? 'At least one medication row is required.' : `Remove ${medication.name || 'medication row'}`}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="note-card">
          <strong>Next step</strong>
          <p>Send this structured payload to the backend before any AI-generated advice is shown.</p>
        </div>

        <div className="note-card supported-pairs-card">
          <strong>Supported high-risk fallback pairs</strong>
          <p>These combinations are currently covered by explicit fallback rules if live interaction data is unavailable.</p>
          <ul>
            {supportedFallbackPairs.map((pair) => (
              <li key={pair}>{pair}</li>
            ))}
          </ul>
        </div>
      </section>

      <section className="workspace-panel" aria-label="Patient context form">
        <div className="panel-header">
          <div>
            <p className="panel-label">Patient context</p>
            <h2>Add clinical context for the review</h2>
          </div>
        </div>

        <div className="patient-grid">
          <label>
            <span>Age</span>
            <input
              type="number"
              min="0"
              placeholder="e.g. 67"
              value={patient.age}
              onChange={(event) => updatePatient('age', event.target.value)}
            />
          </label>

          <label>
            <span>eGFR</span>
            <input
              type="number"
              min="0"
              step="0.1"
              placeholder="e.g. 54"
              value={patient.egfr}
              onChange={(event) => updatePatient('egfr', event.target.value)}
            />
          </label>

          <label>
            <span>Pregnancy status</span>
            <select
              value={patient.pregnancy_status}
              onChange={(event) => updatePatient('pregnancy_status', event.target.value as PatientDraft['pregnancy_status'])}
            >
              <option value="unknown">Unknown</option>
              <option value="not_pregnant">Not pregnant</option>
              <option value="pregnant">Pregnant</option>
            </select>
          </label>

          <label>
            <span>Liver impairment</span>
            <select
              value={patient.liver_impairment}
              onChange={(event) => updatePatient('liver_impairment', event.target.value as PatientDraft['liver_impairment'])}
            >
              <option value="unknown">Unknown</option>
              <option value="none">None</option>
              <option value="mild">Mild</option>
              <option value="moderate">Moderate</option>
              <option value="severe">Severe</option>
            </select>
          </label>

          <label className="patient-textarea">
            <span>Allergies</span>
            <textarea
              rows={3}
              placeholder="e.g. penicillin, shellfish"
              value={patient.allergies}
              onChange={(event) => updatePatient('allergies', event.target.value)}
            />
          </label>

          <label className="patient-textarea">
            <span>Conditions / diagnoses</span>
            <textarea
              rows={3}
              placeholder="e.g. diabetes, lung cancer, COPD"
              value={patient.conditions}
              onChange={(event) => updatePatient('conditions', event.target.value)}
            />
          </label>
        </div>

        <div className="note-card patient-note">
          <strong>Why this matters</strong>
          <p>
            Age, kidney function, pregnancy, and liver status can change how the interaction engine grades risk and
            what advice it returns.
          </p>
        </div>
      </section>

      <section className="workspace-panel results-panel" aria-label="Interaction results preview">
        <div className="panel-header">
          <div>
            <p className="panel-label">Results preview</p>
            <h2>Interaction and guidance summary</h2>
          </div>
        </div>

        <div className={hasPotentialInteraction ? 'alert-box alert-high' : 'alert-box alert-low'}>
          <strong>
            {interactionResult?.max_severity && interactionResult.max_severity !== 'none'
              ? `Severity: ${interactionResult.max_severity}`
              : hasPotentialInteraction
                ? 'High-priority review'
                : 'No current high-severity interaction'}
          </strong>
          <p>
            {interactionResult?.interactions.length
              ? interactionResult.interactions[0]?.recommendation ?? 'Review returned interaction data.'
              : hasPotentialInteraction
                ? 'Warfarin and ibuprofen should be reviewed for bleeding risk before any recommendation is finalized.'
                : 'The current list does not show a clear high-severity interaction in this preview state.'}
          </p>
        </div>

        {usesFallbackEvidence ? (
          <div className="provisional-alert" role="status" aria-live="polite">
            <strong>Provisional evidence state</strong>
            <p>
              This result includes fallback heuristic evidence. Add a reviewer rationale before approving the case.
            </p>
          </div>
        ) : null}

        <div className="interaction-table-shell">
          <div className="table-header-row">
            <div>Drug pair</div>
            <div>Severity</div>
            <div>Recommendation</div>
            <div>Source</div>
          </div>

          {displayedInteractions.length ? (
            displayedInteractions.map((interaction) => (
              <div className="table-data-row" key={`${interaction.drug_a}-${interaction.drug_b}`}>
                <div>
                  <strong>{interaction.drug_a}</strong>
                  <span className="table-secondary">with {interaction.drug_b}</span>
                </div>
                <div>
                  <span className={`severity-pill severity-${interaction.severity}`}>
                    {severityLabelMap[interaction.severity] ?? interaction.severity}
                  </span>
                </div>
                <div>
                  <div className="table-primary">{interaction.recommendation}</div>
                  <div className="table-secondary">{interaction.clinical_effect}</div>
                </div>
                <div>
                  <div
                    className={sourceTypeClassMap[interaction.source_type]}
                  >
                    {sourceTypeLabelMap[interaction.source_type]}
                  </div>
                  <div className="table-secondary">{interaction.source}</div>
                </div>
              </div>
            ))
          ) : (
            <div className="table-empty-state">
              <strong>No interactions returned yet</strong>
              <p>Run the check to populate this table with interaction details and evidence.</p>
              <ul>
                {evidenceBullets.map((bullet) => (
                  <li key={bullet}>{bullet}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="summary-list">
          <div className="summary-item">
            Backend review completed with {interactionResult?.interactions.length ?? 0} interaction
            {(interactionResult?.interactions.length ?? 0) === 1 ? '' : 's'} flagged.
          </div>
          {adviceResult ? (
            <>
              <div className="summary-item">Advice summary: {adviceResult.summary}</div>
              <div className="summary-item">Citations: {adviceResult.citations.join(', ')}</div>
            </>
          ) : null}
        </div>

        <div className="advice-panel">
          <div className="advice-header">
            <p className="panel-label">Advice preview</p>
            <h3>{adviceResult ? 'Generated clinician guidance' : 'Awaiting generated guidance'}</h3>
          </div>

          {adviceResult ? (
            <>
              <p className="advice-summary">{adviceResult.summary}</p>

              <div className="advice-columns">
                <div>
                  <h4>Action plan</h4>
                  <ul>
                    {adviceResult.action_plan.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h4>Red flags</h4>
                  <ul>
                    {adviceResult.red_flags.length ? (
                      adviceResult.red_flags.map((item) => <li key={item}>{item}</li>)
                    ) : (
                      <li>No urgent red flags returned.</li>
                    )}
                  </ul>
                </div>
              </div>

              {adviceResult.alternatives.length ? (
                <div className="advice-subpanel">
                  <h4>Alternatives</h4>
                  <ul>
                    {adviceResult.alternatives.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div className="advice-citations">
                <strong>Citations</strong>
                <span>{adviceResult.citations.join(', ')}</span>
              </div>
            </>
          ) : (
            <p className="advice-placeholder">
              Run the interaction check to generate a clinician-ready summary and sign-off guidance.
            </p>
          )}
        </div>

        <div className="signoff-panel">
          <div className="panel-header">
            <div>
              <p className="panel-label">Review sign-off</p>
              <h2>Approve or reject the case review</h2>
            </div>
          </div>

          <label className="signoff-note">
            <span>Reviewer note</span>
            <textarea
              rows={3}
              placeholder="Add a brief clinical note or sign-off rationale"
              value={reviewNote}
              onChange={(event) => setReviewNote(event.target.value)}
            />
          </label>

          <div className="signoff-actions">
            <button
              className="primary-button"
              type="button"
              onClick={() => runSignOff('signed_off')}
              disabled={isLoading || (usesFallbackEvidence && !reviewNote.trim())}
              title={usesFallbackEvidence && !reviewNote.trim() ? 'Reviewer note required for fallback evidence approvals.' : undefined}
            >
              {isLoading ? 'Submitting...' : 'Approve case'}
            </button>
            <button className="secondary-button" type="button" onClick={() => runSignOff('rejected')} disabled={isLoading}>
              Reject case
            </button>
          </div>

          {reviewResult ? (
            <div className="signoff-status">
              <strong>Sign-off status: {reviewResult.status.replace('_', ' ')}</strong>
              <p>Case ID: {reviewResult.case_id}</p>
              <p>Reviewed at: {new Date(reviewResult.reviewed_at).toLocaleString()}</p>
            </div>
          ) : null}
        </div>

        <div className="audit-panel">
          <div className="panel-header">
            <div>
              <p className="panel-label">Audit trail</p>
              <h2>Review activity log</h2>
            </div>
            <button
              className="secondary-button compact"
              type="button"
              onClick={() => setIsAuditVisible((current) => !current)}
              aria-expanded={isAuditVisible}
              aria-controls="audit-log-content"
              aria-label={isAuditVisible ? 'Collapse audit log' : 'Expand audit log'}
            >
              {isAuditVisible ? '▲ Hide log' : '▼ Show log'}
            </button>
          </div>

          {isAuditVisible ? (
            <div id="audit-log-content">
              {auditTrail.length ? (
                <ol className="audit-list">
                  {auditTrail.map((entry) => (
                    <li key={entry.id} className="audit-item">
                      <div className="audit-item-top">
                        <strong>{entry.action}</strong>
                        <span>{new Date(entry.timestamp).toLocaleString()}</span>
                      </div>
                      <p>{entry.detail}</p>
                    </li>
                  ))}
                </ol>
              ) : (
                <div className="table-empty-state">
                  <strong>No audit entries yet</strong>
                  <p>Run an interaction check or submit a sign-off to populate the activity log.</p>
                </div>
              )}
            </div>
          ) : (
            <div className="table-empty-state">
              <strong>Audit log hidden</strong>
              <p>Click Show log to view review activity entries.</p>
            </div>
          )}
        </div>

        <button className="secondary-button results-button" type="button" onClick={runInteractionCheck} disabled={isLoading}>
          {isLoading ? 'Refreshing...' : 'Generate clinician advice'}
        </button>
      </section>
    </div>
  );
}