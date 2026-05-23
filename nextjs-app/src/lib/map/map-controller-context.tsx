'use client';

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

export interface MapFlyToOptions {
  zoom?: number;
  duration?: number;
}

export interface MapController {
  flyTo: (lat: number, lng: number, options?: MapFlyToOptions) => void;
  setSearchPin: (lat: number, lng: number, label?: string) => void;
  clearSearchPin: () => void;
  isReady: boolean;
}

export type MapControllerImpl = {
  flyTo: (lat: number, lng: number, options?: MapFlyToOptions) => void;
  setSearchPin: (lat: number, lng: number, label?: string) => void;
  clearSearchPin: () => void;
};

type PendingAction =
  | { type: 'flyTo'; lat: number; lng: number; options?: MapFlyToOptions }
  | { type: 'setSearchPin'; lat: number; lng: number; label?: string }
  | { type: 'clearSearchPin' };

const MapControllerContext = createContext<MapController | null>(null);

export function MapControllerProvider({ children }: { children: ReactNode }) {
  const implRef = useRef<MapControllerImpl | null>(null);
  const pendingRef = useRef<PendingAction[]>([]);
  const [isReady, setIsReady] = useState(false);

  const flushPending = useCallback(() => {
    const impl = implRef.current;
    if (!impl || pendingRef.current.length === 0) return;
    const batch = pendingRef.current.splice(0, pendingRef.current.length);
    for (const action of batch) {
      if (action.type === 'flyTo') impl.flyTo(action.lat, action.lng, action.options);
      else if (action.type === 'setSearchPin') impl.setSearchPin(action.lat, action.lng, action.label);
      else impl.clearSearchPin();
    }
  }, []);

  const register = useCallback(
    (impl: MapControllerImpl | null) => {
      implRef.current = impl;
      setIsReady(Boolean(impl));
      if (impl) flushPending();
    },
    [flushPending],
  );

  const enqueueOrRun = useCallback((action: PendingAction, run: () => void) => {
    if (implRef.current) {
      run();
      return;
    }
    pendingRef.current.push(action);
  }, []);

  const flyTo = useCallback(
    (lat: number, lng: number, options?: MapFlyToOptions) => {
      enqueueOrRun({ type: 'flyTo', lat, lng, options }, () => {
        implRef.current?.flyTo(lat, lng, options);
      });
    },
    [enqueueOrRun],
  );

  const setSearchPin = useCallback(
    (lat: number, lng: number, label?: string) => {
      enqueueOrRun({ type: 'setSearchPin', lat, lng, label }, () => {
        implRef.current?.setSearchPin(lat, lng, label);
      });
    },
    [enqueueOrRun],
  );

  const clearSearchPin = useCallback(() => {
    enqueueOrRun({ type: 'clearSearchPin' }, () => {
      implRef.current?.clearSearchPin();
    });
  }, [enqueueOrRun]);

  const value = useMemo<MapController>(
    () => ({
      flyTo,
      setSearchPin,
      clearSearchPin,
      isReady,
    }),
    [flyTo, setSearchPin, clearSearchPin, isReady],
  );

  return (
    <MapControllerContext.Provider value={value}>
      <MapControllerRegistrationContext.Provider value={register}>
        {children}
      </MapControllerRegistrationContext.Provider>
    </MapControllerContext.Provider>
  );
}

const MapControllerRegistrationContext = createContext<
  ((impl: MapControllerImpl | null) => void) | null
>(null);

export function useMapController(): MapController | null {
  return useContext(MapControllerContext);
}

export function useMapControllerRegistration():
  | ((impl: MapControllerImpl | null) => void)
  | null {
  return useContext(MapControllerRegistrationContext);
}
