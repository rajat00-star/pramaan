/** Matches the existing web app's palette (frontend/index.html) so the
 * mobile app and website feel like one product, not two. */
export const colors = {
  navy: '#10233f',
  navyLight: '#1c3a63',
  accent: '#4c8dff',

  pass: '#1b8a3d',
  passBg: '#e6f6ea',
  fail: '#c0362c',
  failBg: '#fbe9e7',
  review: '#b7791f',
  reviewBg: '#fef3e0',
  na: '#6b7280',
  naBg: '#f1f1f1',

  background: '#f5f6f8',
  surface: '#ffffff',
  surfaceMuted: '#eef1f5',
  border: '#dde1e6',
  text: '#1c2127',
  textMuted: '#6b7280',
  textInverse: '#ffffff',
  placeholder: '#9aa4b2',
} as const;

export const verdictColor: Record<string, { fg: string; bg: string }> = {
  COMPLIANT: { fg: colors.pass, bg: colors.passBg },
  NON_COMPLIANT: { fg: colors.fail, bg: colors.failBg },
  REVIEW: { fg: colors.review, bg: colors.reviewBg },
};

export const statusColor: Record<string, { fg: string; bg: string }> = {
  PASS: { fg: '#ffffff', bg: colors.pass },
  FAIL: { fg: '#ffffff', bg: colors.fail },
  REVIEW: { fg: '#ffffff', bg: colors.review },
  NOT_APPLICABLE: { fg: '#ffffff', bg: colors.na },
};

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;

export const radius = { sm: 6, md: 8, lg: 12, pill: 999 } as const;
