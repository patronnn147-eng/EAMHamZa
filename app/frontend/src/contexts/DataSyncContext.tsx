import React, { createContext, useContext, useCallback, useMemo, ReactNode } from 'react';

interface DataChangeEvent {
  type: 'work_order' | 'machine' | 'intervention';
  action: 'create' | 'update' | 'delete';
  id: number | string;
}

interface DataSyncContextType {
  notifyChange: (event: DataChangeEvent) => void;
  subscribe: (callback: (event: DataChangeEvent) => void) => () => void;
}

const DataSyncContext = createContext<DataSyncContextType | null>(null);

export const useDataSync = () => {
  const context = useContext(DataSyncContext);
  if (!context) {
    throw new Error('useDataSync must be used within a DataSyncProvider');
  }
  return context;
};

interface DataSyncProviderProps {
  children: ReactNode;
}

export const DataSyncProvider: React.FC<DataSyncProviderProps> = ({ children }) => {
  const subscribers = useMemo(() => new Set<(event: DataChangeEvent) => void>(), []);

  const notifyChange = useCallback((event: DataChangeEvent) => {
    subscribers.forEach(callback => callback(event));
  }, [subscribers]);

  const subscribe = useCallback((callback: (event: DataChangeEvent) => void) => {
    subscribers.add(callback);
    return () => {
      subscribers.delete(callback);
    };
  }, [subscribers]);

  const value: DataSyncContextType = useMemo(() => ({
    notifyChange,
    subscribe,
  }), [notifyChange, subscribe]);

  return (
    <DataSyncContext.Provider value={value}>
      {children}
    </DataSyncContext.Provider>
  );
};
