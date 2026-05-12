"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

import { createWalletSession, syncPortfolio } from "@/lib/api/dashboard-client";

type WalletContextValue = {
  walletAddress: string | null;
  isConnecting: boolean;
  connectDemoWallet: () => Promise<void>;
  disconnectWallet: () => void;
};

const WalletContext = createContext<WalletContextValue | null>(null);
const WALLET_STORAGE_KEY = "stakemind.walletAddress";
const WALLET_STORAGE_EVENT = "stakemind:wallet-storage";

const DEMO_WALLET =
  process.env.NEXT_PUBLIC_DEMO_WALLET ?? "5GKh6cqk9RFUcL4oHfNrBYa5C43ioDfrw561dTefqzy8QTWC";

function subscribeToWalletStorage(listener: () => void) {
  window.addEventListener("storage", listener);
  window.addEventListener(WALLET_STORAGE_EVENT, listener);
  return () => {
    window.removeEventListener("storage", listener);
    window.removeEventListener(WALLET_STORAGE_EVENT, listener);
  };
}

function getWalletSnapshot() {
  return sessionStorage.getItem(WALLET_STORAGE_KEY);
}

function getServerWalletSnapshot() {
  return null;
}

function setStoredWallet(address: string | null) {
  if (address) {
    sessionStorage.setItem(WALLET_STORAGE_KEY, address);
  } else {
    sessionStorage.removeItem(WALLET_STORAGE_KEY);
  }
  window.dispatchEvent(new Event(WALLET_STORAGE_EVENT));
}

export function WalletProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const walletAddress = useSyncExternalStore(
    subscribeToWalletStorage,
    getWalletSnapshot,
    getServerWalletSnapshot,
  );
  const [isConnecting, setIsConnecting] = useState(false);

  const connectDemoWallet = useCallback(async () => {
    setIsConnecting(true);
    try {
      await createWalletSession(DEMO_WALLET);
      await syncPortfolio(DEMO_WALLET);
      setStoredWallet(DEMO_WALLET);
      await queryClient.invalidateQueries();
    } finally {
      setIsConnecting(false);
    }
  }, [queryClient]);

  const disconnectWallet = useCallback(() => {
    setStoredWallet(null);
    void queryClient.removeQueries({ queryKey: ["staking"] });
    void queryClient.removeQueries({ queryKey: ["rewards-summary"] });
    void queryClient.removeQueries({ queryKey: ["rewards-history"] });
  }, [queryClient]);

  const value = useMemo(
    () => ({
      walletAddress,
      isConnecting,
      connectDemoWallet,
      disconnectWallet,
    }),
    [walletAddress, isConnecting, connectDemoWallet, disconnectWallet],
  );

  return <WalletContext.Provider value={value}>{children}</WalletContext.Provider>;
}

export function useWallet() {
  const context = useContext(WalletContext);
  if (!context) {
    throw new Error("useWallet must be used within WalletProvider");
  }
  return context;
}
