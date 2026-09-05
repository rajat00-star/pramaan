import { useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import React, { useState } from 'react';
import { ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { getAuditTrail, submitReview } from '../../api/scans';
import { friendlyErrorMessage } from '../../api/errors';
import { AuthenticatedImage } from '../../components/AuthenticatedImage';
import { Button } from '../../components/Button';
import { Card } from '../../components/Card';
import { StatusBadge } from '../../components/StatusBadge';
import { ErrorState, LoadingState } from '../../components/States';
import { VerdictBanner } from '../../components/VerdictBanner';
import { useScan } from '../../hooks/useScan';
import type { InspectorStackParamList } from '../../navigation/types';
import { colors, radius, spacing } from '../../theme/colors';
import { FIELD_LABELS } from '../../types/api';
import type { AuditLogOut, RuleEvaluationOut } from '../../types/api';

type Rt = RouteProp<InspectorStackParamList, 'CaseDetail'>;

export function CaseDetailScreen() {
  const { params } = useRoute<Rt>();
  const { scan, error, loading, reload } = useScan(params.scanId);
  const [correctingField, setCorrectingField] = useState<string | null>(null);
  const [correctionValue, setCorrectionValue] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [savedNotice, setSavedNotice] = useState(false);
  const [audit, setAudit] = useState<AuditLogOut[] | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);

  if (loading) return <LoadingState label="Loading case…" />;
  if (error || !scan) return <ErrorState message={error ?? 'Case not found.'} onRetry={reload} />;

  const startCorrection = (fieldId: string, currentValue: string | null) => {
    setCorrectingField(fieldId);
    setCorrectionValue(currentValue ?? '');
    setSubmitError(null);
    setSavedNotice(false);
  };

  const submitCorrection = async () => {
    if (!correctingField || !correctionValue.trim()) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await submitReview(scan.id, { field_id: correctingField, corrected_value: correctionValue.trim() });
      setCorrectingField(null);
      setSavedNotice(true);
      await reload();
    } catch (err) {
      setSubmitError(friendlyErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const loadAudit = async () => {
    setAuditError(null);
    try {
      setAudit(await getAuditTrail(scan.id));
    } catch (err) {
      setAuditError(friendlyErrorMessage(err));
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <AuthenticatedImage scanId={scan.id} style={styles.image} />
        {scan.overall_verdict && <VerdictBanner verdict={scan.overall_verdict} confidence={scan.overall_confidence} />}

        {savedNotice && (
          <View style={styles.savedBanner}>
            <Text style={styles.savedBannerText}>✓ Correction saved · audit recorded</Text>
          </View>
        )}

        <Card title="Legal Evaluation — tap REVIEW to correct">
          {scan.evaluations.map((evaluation) => (
            <EvaluationCorrectionRow
              key={evaluation.field_id}
              evaluation={evaluation}
              currentRawValue={scan.fields.find((f) => f.field_id === evaluation.field_id)?.raw_value ?? null}
              isEditing={correctingField === evaluation.field_id}
              onStartEdit={() => startCorrection(evaluation.field_id, scan.fields.find((f) => f.field_id === evaluation.field_id)?.raw_value ?? null)}
              onCancel={() => setCorrectingField(null)}
              value={correctionValue}
              onChangeValue={setCorrectionValue}
              onSubmit={submitCorrection}
              submitting={submitting}
              submitError={correctingField === evaluation.field_id ? submitError : null}
            />
          ))}
        </Card>

        <Card title="OCR Evidence">
          <Text style={styles.metaText}>
            Engine: {scan.ocr_engine ?? '—'} · Confidence:{' '}
            {scan.ocr_mean_confidence !== null ? `${scan.ocr_mean_confidence.toFixed(1)}%` : '—'}
          </Text>
          <View style={styles.ocrBox}>
            <Text style={styles.ocrText}>{scan.raw_ocr_text || '(no text detected)'}</Text>
          </View>
        </Card>

        <Card title="Scan Details">
          <Text style={styles.metaText}>Scan ID: {scan.id}</Text>
          <Text style={styles.metaText}>
            Rule pack: v{scan.rule_pack_version} ({(scan.rule_pack_hash ?? '').slice(0, 16)}…)
          </Text>
          <Text style={styles.metaText}>Timestamp: {new Date(scan.created_at).toLocaleString()}</Text>
        </Card>

        {scan.reviews.length > 0 && (
          <Card title="Correction History">
            {scan.reviews.map((r, i) => (
              <View key={`${r.field_id}-${i}`} style={styles.historyRow}>
                <Text style={styles.historyField}>{FIELD_LABELS[r.field_id] ?? r.field_id}</Text>
                <Text style={styles.historyDetail}>
                  "{r.original_value ?? '(not found)'}" → "{r.corrected_value}" by {r.reviewer}
                </Text>
              </View>
            ))}
          </Card>
        )}

        <Card title="Audit Trail">
          {audit === null ? (
            <Button title="Load Audit Trail" variant="secondary" onPress={loadAudit} />
          ) : auditError ? (
            <Text style={styles.errorText}>{auditError}</Text>
          ) : (
            audit.map((event) => (
              <View key={event.id} style={styles.auditRow}>
                <Text style={styles.auditEvent}>{event.event_type}</Text>
                <Text style={styles.auditMeta}>{new Date(event.created_at).toLocaleString()}</Text>
              </View>
            ))
          )}
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

function EvaluationCorrectionRow({
  evaluation,
  currentRawValue,
  isEditing,
  onStartEdit,
  onCancel,
  value,
  onChangeValue,
  onSubmit,
  submitting,
  submitError,
}: {
  evaluation: RuleEvaluationOut;
  currentRawValue: string | null;
  isEditing: boolean;
  onStartEdit: () => void;
  onCancel: () => void;
  value: string;
  onChangeValue: (v: string) => void;
  onSubmit: () => void;
  submitting: boolean;
  submitError: string | null;
}) {
  const canCorrect = evaluation.status === 'REVIEW';
  return (
    <View style={styles.evalRow}>
      <View style={styles.evalHeader}>
        <StatusBadge status={evaluation.status} />
        <Text style={styles.evalField}>{FIELD_LABELS[evaluation.field_id] ?? evaluation.field_id}</Text>
      </View>
      <Text style={styles.evalReason}>{evaluation.reason}</Text>
      {currentRawValue && <Text style={styles.evalCurrentValue}>Current: "{currentRawValue}"</Text>}

      {canCorrect && !isEditing && (
        <Button title="Correct this field" variant="link" onPress={onStartEdit} style={{ alignSelf: 'flex-start' }} />
      )}

      {isEditing && (
        <View style={styles.correctionForm}>
          <TextInput
            style={styles.correctionInput}
            value={value}
            onChangeText={onChangeValue}
            placeholder="Corrected value from physical label"
            placeholderTextColor={colors.placeholder}
            autoFocus
          />
          {submitError && <Text style={styles.errorText}>{submitError}</Text>}
          <View style={styles.correctionButtons}>
            <Button title="Save Correction" onPress={onSubmit} loading={submitting} disabled={!value.trim()} />
            <Button title="Cancel" variant="secondary" onPress={onCancel} disabled={submitting} />
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  scroll: { padding: spacing.lg, gap: spacing.md },
  image: { height: 240, borderRadius: radius.lg, backgroundColor: colors.surfaceMuted },
  savedBanner: { backgroundColor: colors.passBg, borderRadius: radius.md, padding: spacing.sm },
  savedBannerText: { color: colors.pass, fontWeight: '600', textAlign: 'center' },
  evalRow: { paddingVertical: spacing.sm, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border, gap: 6 },
  evalHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  evalField: { fontSize: 14, fontWeight: '600', color: colors.text },
  evalReason: { fontSize: 13, color: colors.text, lineHeight: 18 },
  evalCurrentValue: { fontSize: 12, color: colors.textMuted, fontStyle: 'italic' },
  correctionForm: { gap: spacing.sm, marginTop: spacing.xs },
  correctionInput: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 12,
    fontSize: 14,
    backgroundColor: colors.surface,
    color: colors.text,
  },
  correctionButtons: { flexDirection: 'row', gap: spacing.sm },
  errorText: { color: colors.fail, fontSize: 12 },
  metaText: { fontSize: 13, color: colors.text, marginBottom: 2 },
  ocrBox: { backgroundColor: '#0f1720', borderRadius: radius.sm, padding: spacing.sm, marginTop: spacing.sm },
  ocrText: { color: '#d9e2ec', fontSize: 12, fontFamily: 'Courier' },
  historyRow: { paddingVertical: spacing.xs },
  historyField: { fontSize: 13, fontWeight: '600', color: colors.text },
  historyDetail: { fontSize: 12, color: colors.textMuted },
  auditRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: spacing.xs, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  auditEvent: { fontSize: 13, fontWeight: '600', color: colors.text },
  auditMeta: { fontSize: 11, color: colors.textMuted },
});
