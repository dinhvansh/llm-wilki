import { useCallback, useState } from 'react';
import type { ImportCategory } from '@/components/command-bar/importDetection';

const STORAGE_KEY = 'flowmind_recent_imports';
const MAX_PER_CATEGORY = 5;

export interface RecentImport {
  id: string;
  category: ImportCategory;
  source: string; // filename or first line of content
  preview: string; // first 200 chars of content
  timestamp: number;
}

function loadAll(): RecentImport[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]') as RecentImport[];
  } catch {
    return [];
  }
}

function saveAll(items: RecentImport[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

export function useRecentImports(category: ImportCategory): {
  recents: RecentImport[];
  addRecent: (source: string, content: string) => void;
  removeRecent: (id: string) => void;
} {
  const [all, setAll] = useState<RecentImport[]>(loadAll);

  const recents = all.filter((r) => r.category === category);

  const addRecent = useCallback(
    (source: string, content: string) => {
      if (!content.trim()) return;
      setAll((prev) => {
        const deduped = prev.filter((r) => !(r.category === category && r.source === source));
        const entry: RecentImport = {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          category,
          source,
          preview: content.slice(0, 200),
          timestamp: Date.now(),
        };
        const forCategory = [entry, ...deduped.filter((r) => r.category === category)].slice(
          0,
          MAX_PER_CATEGORY
        );
        const others = deduped.filter((r) => r.category !== category);
        const next = [...forCategory, ...others];
        saveAll(next);
        return next;
      });
    },
    [category]
  );

  const removeRecent = useCallback((id: string) => {
    setAll((prev) => {
      const next = prev.filter((r) => r.id !== id);
      saveAll(next);
      return next;
    });
  }, []);

  return { recents, addRecent, removeRecent };
}
