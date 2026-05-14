"use client";

import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

type CompareHotkeysContextValue = {
  compareHotkeys: string[];
  toggleCompareHotkey: (hotkey: string) => void;
  clearCompareHotkeys: () => void;
};

const CompareHotkeysContext = createContext<CompareHotkeysContextValue | null>(null);

export function CompareHotkeysProvider({ children }: { children: ReactNode }) {
  const [compareHotkeys, setCompareHotkeys] = useState<string[]>([]);

  const value = useMemo(
    () => ({
      compareHotkeys,
      toggleCompareHotkey: (hotkey: string) => {
        setCompareHotkeys((current) => {
          if (current.includes(hotkey)) {
            return current.filter((item) => item !== hotkey);
          }
          if (current.length >= 3) {
            return [...current.slice(1), hotkey];
          }
          return [...current, hotkey];
        });
      },
      clearCompareHotkeys: () => setCompareHotkeys([]),
    }),
    [compareHotkeys],
  );

  return <CompareHotkeysContext.Provider value={value}>{children}</CompareHotkeysContext.Provider>;
}

export function useCompareHotkeys() {
  const context = useContext(CompareHotkeysContext);
  if (!context) {
    throw new Error("useCompareHotkeys must be used within CompareHotkeysProvider");
  }
  return context;
}
