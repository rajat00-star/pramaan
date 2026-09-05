import React, { PropsWithChildren, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { ExtractedFieldOut, RuleEvaluationOut, ScanOut } from '../types/api';
import { FIELD_LABELS } from '../types/api';
import { AuthenticatedImage } from './AuthenticatedImage';
import { Card } from './Card';
import { StatusBadge } from './StatusBadge';
import { VerdictBanner } from './VerdictBanner';
import { colors, radius, spacing } from '../theme/colors';

/** Shared rendering of one scan's evidence — used by the citizen result
 * screen, the citizen scan-detail screen, and the inspector case screen, so
 * all three surfaces show the exact same real evidence the same way. */
export function ScanDetailView({ scan, children }: PropsWithChildren<{ scan: ScanOut }>) {
  return (
    <View style={styles.container}>
      <AuthenticatedImage scanId={scan.id} style={styles.image} />

      {scan.overall_verdict && <VerdictBanner verdict={scan.overall_verdict} confidence={scan.overall_confidence} />}

      {scan.overall_verdict === 'REVIEW' && (
        <View style={styles.reviewNotice}>
          <Text style={styles.reviewNoticeText}>
            PraMaan could not establish a reliable result from the available evidence. Human review is required.
            This is not an error — it means the system is being honest about what it could and could not verify.
          </Text>
        </View>
      )}

      <Card title="Extracted Declarations">
        {scan.fields.filter((f) => f.found).length === 0 ? (
          <Text style={styles.muted}>No declarations could be read from this image.</Text>
        ) : (
          scan.fields
            .filter((f) => f.found)
            .map((f) => <FieldRow key={f.field_id} field={f} />)
        )}
      </Card>

      <Card title="Legal Evaluation">
        {scan.evaluations.map((e) => (
          <EvaluationRow key={e.field_id} evaluation={e} />
        ))}
      </Card>

      <Card title="OCR Evidence">
        <View style={styles.metaRow}>
          <Text style={styles.metaLabel}>Engine</Text>
          <Text style={styles.metaValue}>{scan.ocr_engine ?? '—'}</Text>
        </View>
        <View style={styles.metaRow}>
          <Text style={styles.metaLabel}>Language</Text>
          <Text style={styles.metaValue}>{scan.ocr_lang ?? '—'}</Text>
        </View>
        <View style={styles.metaRow}>
          <Text style={styles.metaLabel}>Mean OCR confidence</Text>
          <Text style={styles.metaValue}>
            {scan.ocr_mean_confidence !== null ? `${scan.ocr_mean_confidence.toFixed(1)}%` : '—'}
          </Text>
        </View>
        <RawOcrText text={scan.raw_ocr_text} />
      </Card>

      <Card title="Scan Details">
        <View style={styles.metaRow}>
          <Text style={styles.metaLabel}>Scan ID</Text>
          <Text style={styles.metaValueMono}>{scan.id}</Text>
        </View>
        <View style={styles.metaRow}>
          <Text style={styles.metaLabel}>Rule pack</Text>
          <Text style={styles.metaValueMono}>
            v{scan.rule_pack_version} ({(scan.rule_pack_hash ?? '').slice(0, 12)}…)
          </Text>
        </View>
        <View style={styles.metaRow}>
          <Text style={styles.metaLabel}>Scanned</Text>
          <Text style={styles.metaValue}>{new Date(scan.created_at).toLocaleString()}</Text>
        </View>
      </Card>

      {scan.reviews.length > 0 && (
        <Card title="Correction History">
          {scan.reviews.map((r, i) => (
            <View key={`${r.field_id}-${i}`} style={styles.reviewRow}>
              <Text style={styles.reviewField}>{FIELD_LABELS[r.field_id] ?? r.field_id}</Text>
              <Text style={styles.reviewDetail}>
                "{r.original_value ?? '(not found)'}" → "{r.corrected_value}"
              </Text>
              <Text style={styles.reviewMeta}>
                by {r.reviewer} · {new Date(r.created_at).toLocaleString()}
                {r.previous_verdict !== r.resulting_verdict
                  ? ` · verdict ${r.previous_verdict} → ${r.resulting_verdict}`
                  : ''}
              </Text>
            </View>
          ))}
        </Card>
      )}

      {children}
    </View>
  );
}

function FieldRow({ field }: { field: ExtractedFieldOut }) {
  const lowConfidence = field.confidence !== null && field.confidence < 60;
  return (
    <View style={styles.fieldRow}>
      <Text style={styles.fieldLabel}>{FIELD_LABELS[field.field_id] ?? field.field_id}</Text>
      <Text style={styles.fieldValue}>{field.raw_value}</Text>
      {field.confidence !== null && (
        <Text style={[styles.fieldConfidence, lowConfidence && styles.fieldConfidenceLow]}>
          Confidence: {field.confidence.toFixed(1)}% {field.source === 'human_review' ? '(human-verified)' : ''}
        </Text>
      )}
    </View>
  );
}

function EvaluationRow({ evaluation }: { evaluation: RuleEvaluationOut }) {
  return (
    <View style={styles.evalRow}>
      <View style={styles.evalHeader}>
        <StatusBadge status={evaluation.status} />
        <Text style={styles.evalField}>{FIELD_LABELS[evaluation.field_id] ?? evaluation.field_id}</Text>
      </View>
      <Text style={styles.evalReason}>{evaluation.reason}</Text>
      <Text style={styles.evalClause}>{evaluation.legal_reference}</Text>
    </View>
  );
}

function RawOcrText({ text }: { text: string | null }) {
  const [expanded, setExpanded] = useState(false);
  if (!text) return <Text style={[styles.muted, { marginTop: spacing.sm }]}>(no text detected)</Text>;
  const preview = text.length > 220 && !expanded ? `${text.slice(0, 220)}…` : text;
  return (
    <View style={styles.ocrBox}>
      <Text style={styles.ocrText}>{preview}</Text>
      {text.length > 220 && (
        <Text style={styles.expandLink} onPress={() => setExpanded((e) => !e)}>
          {expanded ? 'Show less' : 'Show full text'}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: spacing.md },
  image: { height: 260, borderRadius: radius.lg, backgroundColor: colors.surfaceMuted },
  reviewNotice: { backgroundColor: colors.reviewBg, borderRadius: radius.md, padding: spacing.md },
  reviewNoticeText: { color: colors.review, fontSize: 13, lineHeight: 19 },
  muted: { color: colors.textMuted, fontSize: 13 },
  fieldRow: { paddingVertical: spacing.sm, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border, gap: 2 },
  fieldLabel: { fontSize: 12, color: colors.textMuted, textTransform: 'uppercase', letterSpacing: 0.3 },
  fieldValue: { fontSize: 15, color: colors.text, fontWeight: '600' },
  fieldConfidence: { fontSize: 11, color: colors.textMuted },
  fieldConfidenceLow: { color: colors.review, fontWeight: '600' },
  evalRow: { paddingVertical: spacing.sm, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border, gap: 4 },
  evalHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  evalField: { fontSize: 14, fontWeight: '600', color: colors.text },
  evalReason: { fontSize: 13, color: colors.text, lineHeight: 18 },
  evalClause: { fontSize: 11, color: colors.textMuted },
  metaRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 },
  metaLabel: { fontSize: 13, color: colors.textMuted },
  metaValue: { fontSize: 13, color: colors.text, fontWeight: '500' },
  metaValueMono: { fontSize: 12, color: colors.text, fontFamily: 'Courier' },
  ocrBox: { backgroundColor: '#0f1720', borderRadius: radius.sm, padding: spacing.sm, marginTop: spacing.sm },
  ocrText: { color: '#d9e2ec', fontSize: 12, fontFamily: 'Courier' },
  expandLink: { color: colors.accent, fontSize: 12, marginTop: spacing.xs },
  reviewRow: { paddingVertical: spacing.sm, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border, gap: 2 },
  reviewField: { fontSize: 13, fontWeight: '600', color: colors.text },
  reviewDetail: { fontSize: 13, color: colors.text },
  reviewMeta: { fontSize: 11, color: colors.textMuted },
});
