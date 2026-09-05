/**
 * TypeScript types mirroring the actual backend Pydantic schemas
 * (backend/app/schemas.py) verbatim. These are read from the real API
 * response shapes — nothing here is guessed.
 */

export type Role = 'citizen' | 'inspector' | 'department_admin';

export type Verdict = 'COMPLIANT' | 'NON_COMPLIANT' | 'REVIEW';

export type FieldStatus = 'PASS' | 'FAIL' | 'REVIEW' | 'NOT_APPLICABLE';

export type ScanStatus = 'PROCESSING' | 'DONE' | 'ERROR';

export interface TokenOut {
  access_token: string;
  token_type: string;
  username: string;
  role: Role;
}

export interface UserOut {
  id: string;
  username: string;
  role: Role;
  created_at: string;
}

export interface BoundingBox {
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface ExtractedFieldOut {
  field_id: string;
  found: boolean;
  raw_value: string | null;
  confidence: number | null;
  bbox: BoundingBox | null;
  source: 'ocr' | 'human_review';
}

export interface RuleEvaluationOut {
  field_id: string;
  clause: string;
  legal_reference: string;
  status: FieldStatus;
  reason: string;
  evidence: Record<string, unknown> | null;
  rule_pack_version: string;
}

export interface ReviewCorrectionOut {
  field_id: string;
  original_value: string | null;
  corrected_value: string;
  reviewer: string;
  note: string | null;
  previous_verdict: Verdict | null;
  resulting_verdict: Verdict | null;
  created_at: string;
}

export interface ScanOut {
  id: string;
  owner_user_id: string | null;
  image_path: string;
  status: ScanStatus;
  error_message: string | null;

  detector_method: string | null;
  ocr_engine: string | null;
  ocr_lang: string | null;
  raw_ocr_text: string | null;
  ocr_mean_confidence: number | null;

  rule_pack_version: string | null;
  rule_pack_hash: string | null;

  overall_verdict: Verdict | null;
  overall_confidence: number | null;

  created_at: string;
  updated_at: string;

  fields: ExtractedFieldOut[];
  evaluations: RuleEvaluationOut[];
  reviews: ReviewCorrectionOut[];
}

export interface ScanSummaryOut {
  id: string;
  owner_user_id: string | null;
  status: ScanStatus;
  overall_verdict: Verdict | null;
  overall_confidence: number | null;
  created_at: string;
}

export interface ReviewCorrectionIn {
  field_id: string;
  corrected_value: string;
  note?: string;
}

export interface RulePackFieldOut {
  field_id: string;
  clause: string;
  title: string;
  legal_reference: string;
}

export interface RulePackOut {
  rule_pack_version: string;
  effective_date: string;
  sha256_hash: string;
  scope: string;
  fields: RulePackFieldOut[];
}

export interface AuditLogOut {
  id: number;
  event_type: string;
  actor_user_id: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
}

export interface ReplayOut {
  scan_id: string;
  original_rule_pack_version: string | null;
  original_rule_pack_hash: string | null;
  original_overall_verdict: Verdict | null;
  replayed_rule_pack_version: string | null;
  replayed_rule_pack_hash: string | null;
  replayed_overall_verdict: Verdict | null;
  reproduced: boolean;
  evaluations: RuleEvaluationOut[];
}

export interface InspectorActivityOut {
  reviewer: string;
  review_count: number;
  last_review_at: string;
}

export interface RulePackSummaryOut {
  rule_pack_version: string;
  effective_date: string;
  sha256_hash: string;
  field_count: number;
}

export interface DashboardSummaryOut {
  total_scans: number;
  compliant: number;
  non_compliant: number;
  review: number;
  error: number;
  pending_review_count: number;
  mean_confidence: number | null;
  violation_frequency: Record<string, number>;
  recent_scans: ScanSummaryOut[];
  inspector_activity: InspectorActivityOut[];
  reviews_today: number;
  rule_pack: RulePackSummaryOut;
}

/** Human-readable labels for the 7 rule-pack field ids, for UI display only —
 * the backend remains the sole source of which fields exist and what they mean. */
export const FIELD_LABELS: Record<string, string> = {
  manufacturer_packer_importer: 'Manufacturer / Packer / Importer',
  country_of_origin: 'Country of Origin',
  common_generic_name: 'Generic / Common Name',
  net_quantity: 'Net Quantity',
  date_of_manufacture: 'Date of Manufacture',
  retail_sale_price: 'MRP (Retail Sale Price)',
  consumer_care_details: 'Consumer Care Details',
};
