import { useCallback, useEffect, useState } from 'react';

import { getScan } from '../api/scans';
import { friendlyErrorMessage } from '../api/errors';
import type { ScanOut } from '../types/api';

export function useScan(scanId: string) {
  const [scan, setScan] = useState<ScanOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getScan(scanId);
      setScan(result);
    } catch (err) {
      setError(friendlyErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [scanId]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { scan, error, loading, reload };
}
