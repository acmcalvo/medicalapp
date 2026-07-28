export type Severity = 'contraindicated' | 'major' | 'moderate' | 'minor' | 'none';
export type Role = 'doctor' | 'pharmacist';

export type MedicationInput = {
  name_entered: string;
  dose?: string;
  route?: string;
  frequency?: string;
};

export type PatientContext = {
  age?: number;
  pregnancy_status: 'pregnant' | 'not_pregnant' | 'unknown';
  egfr?: number;
  liver_impairment: 'none' | 'mild' | 'moderate' | 'severe' | 'unknown';
};

export type InteractionItem = {
  drug_a: string;
  drug_b: string;
  severity: Severity;
  source_type: 'live_rxcui' | 'heuristic';
  mechanism: string;
  clinical_effect: string;
  recommendation: string;
  monitoring: string[];
  source: string;
};

export type InteractionCheckRequest = {
  medications: MedicationInput[];
  patient: PatientContext;
};

export type InteractionCheckResponse = {
  max_severity: Severity;
  interactions: InteractionItem[];
  requires_clinician_review: boolean;
};

export type AdviceRequest = {
  role: Role;
  interactions: InteractionItem[];
  patient: PatientContext;
  question?: string;
};

export type AdviceResponse = {
  summary: string;
  action_plan: string[];
  alternatives: string[];
  red_flags: string[];
  citations: string[];
  disclaimer: string;
};

export type ReviewSignOffRequest = {
  case_id: string;
  status: 'signed_off' | 'rejected';
  role: Role;
  uses_fallback_evidence?: boolean;
  note?: string;
};

export type ReviewSignOffResponse = {
  status: 'signed_off' | 'rejected';
  case_id: string;
  reviewed_at: string;
  payload: ReviewSignOffRequest;
};

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export function checkInteractions(payload: InteractionCheckRequest) {
  return requestJson<InteractionCheckResponse>('/interactions/check', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function generateAdvice(payload: AdviceRequest) {
  return requestJson<AdviceResponse>('/advice/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function submitReviewSignOff(payload: ReviewSignOffRequest) {
  return requestJson<ReviewSignOffResponse>('/cases/review-signoff', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}