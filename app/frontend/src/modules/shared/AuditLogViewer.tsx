import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { debounce } from '@/lib/utils';
import { 
  History, 
  Download, 
  User,
  Calendar,
  PlusCircle,
  Trash2,
  Eye,
  ArrowRightLeft,
  Clock,
  Search,
  ChevronLeft,
  ChevronRight,
  X,
  AlertTriangle
} from 'lucide-react';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

interface AuditEntry {
  id: number;
  action_type: string;
  entity_type: string;
  entity_id: number;
  entity_name?: string;
  user_id?: number;
  user_name?: string;
  changes?: Record<string, { old: any; new: any }>;
  old_values?: Record<string, any>;
  new_values?: Record<string, any>;
  description?: string;
  created_at: string;
}

const actionConfig: Record<string, { icon: React.ReactNode; color: string }> = {
  CREATE: { icon: <PlusCircle className="h-4 w-4" />, color: 'text-green-400' },
  UPDATE: { icon: <ArrowRightLeft className="h-4 w-4" />, color: 'text-blue-400' },
  DELETE: { icon: <Trash2 className="h-4 w-4" />, color: 'text-red-400' },
  VIEW: { icon: <Eye className="h-4 w-4" />, color: 'text-gray-400' }
};

const entityLabels: Record<string, string> = {
  machine: "Machine",
  work_order: "Work Order",
  intervention: "Intervention",
  planning: "Planning",
  user: "User",
  alert: "Alert",
  inventory: "Inventory",
  report: "Report"
};

// Date formatting: "Jan 15, 2024 14:32"
const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const month = months[date.getMonth()];
  const day = date.getDate();
  const year = date.getFullYear();
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${month} ${day}, ${year} ${hours}:${minutes}`;
};

export const AuditLogViewer: React.FC = () => {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);
  const [hasError, setHasError] = useState(false);

  // Error boundary: catch unexpected errors
  useEffect(() => {
    const handleError = () => setHasError(true);
    globalThis.addEventListener('error', handleError);
    return () => globalThis.removeEventListener('error', handleError);
  }, []);
  
  // Filter states
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [userSearch, setUserSearch] = useState<string>('');
  
  const limit = 20;
  const totalPages = Math.ceil(total / limit);

  // Memoized fetch function
  const fetchAuditLog = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      params.append('skip', String(page * limit));
      params.append('limit', String(limit));
      
      // Add filters
      if (startDate) params.append('from_date', startDate);
      if (endDate) params.append('to_date', endDate);
      if (userSearch.trim()) params.append('user_search', userSearch.trim());
      
      const res = await fetch(`${API}/api/v1/audit/log?${params}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      
      if (res.ok) {
        const data = await res.json();
        setEntries(data.items || []);
        setTotal(data.total || 0);
      } else {
        let errMsg: string;
        if (res.status === 401) {
          errMsg = "Authentication required. Please log in.";
        } else if (res.status === 403) {
          errMsg = "Access denied. You don't have permission to view audit logs.";
        } else {
          errMsg = `Server error (${res.status})`;
        }
        setError(errMsg);
        setEntries([]);
        setTotal(0);
      }
    } catch (err) {
      const errMessage = err instanceof Error ? err.message : "Failed to load audit logs";
      setError(errMessage);
      setEntries([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, startDate, endDate, userSearch]);

  // Debounced search for user search input
  const debouncedSearch = useMemo(
    () => debounce(() => {
      setPage(0);
      fetchAuditLog();
    }, 400),
    [fetchAuditLog]
  );

  // Handle user search change
  const handleUserSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setUserSearch(value);
    debouncedSearch(value);
  };

  // Clear user search
  const clearUserSearch = () => {
    setUserSearch('');
    setPage(0);
    fetchAuditLog();
  };

  // Cleanup debounce on unmount to prevent memory leak
  useEffect(() => {
    return () => {
      debouncedSearch.cancel();
    };
  }, [debouncedSearch]);

  // Date filter changes trigger refetch
  useEffect(() => {
    setPage(0);
    fetchAuditLog();
  }, [startDate, endDate]);

  // Page change triggers refetch
  useEffect(() => {
    fetchAuditLog();
  }, [page]);

  // Export CSV
  const exportCSV = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (startDate) params.append('from_date', startDate);
      if (endDate) params.append('to_date', endDate);
      if (userSearch.trim()) params.append('user_search', userSearch.trim());
      
      const res = await fetch(`${API}/api/v1/audit/export?${params}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const data = await res.json();
        const blob = new Blob([data.csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `audit_log_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error('Export failed', err);
    }
  }, [startDate, endDate, userSearch]);

  // Go to previous page
  const goToPrevPage = () => {
    if (page > 0) setPage(p => p - 1);
  };

  // Go to next page
  const goToNextPage = () => {
    if (page < totalPages - 1) setPage(p => p + 1);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3 font-heading">
            <History className="h-6 w-6 text-cyan-400" />
            Audit Log
          </h1>
          <p className="text-sm text-orchestrated-glass mt-1 font-body">
            Real-time activity across your organization
          </p>
        </div>
        <button 
          onClick={exportCSV}
          className="btn-cyan px-4 py-2 rounded-lg flex items-center gap-2 font-medium transition-all hover:shadow-[0_0_20px_rgba(0,255,242,0.3)]"
        >
          <Download className="h-4 w-4" />
          Export CSV
        </button>
      </div>

      {/* Filters Bar */}
      <div className="glass-panel p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Date Range Start */}
          <div className="flex flex-col gap-1">
            <label htmlFor="audit-start-date" className="text-xs text-orchestrated-glass font-body">From Date</label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-orchestrated-glass" />
              <input
                id="audit-start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="input-glass w-full pl-10 pr-3 py-2 font-body"
              />
            </div>
          </div>

          {/* Date Range End */}
          <div className="flex flex-col gap-1">
            <label htmlFor="audit-end-date" className="text-xs text-orchestrated-glass font-body">To Date</label>
            <div className="relative">
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-orchestrated-glass" />
              <input
                id="audit-end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="input-glass w-full pl-10 pr-3 py-2 font-body"
              />
            </div>
          </div>

          {/* User Search */}
          <div className="flex flex-col gap-1">
            <label htmlFor="audit-user-search" className="text-xs text-orchestrated-glass font-body">Search Users</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-orchestrated-glass" />
              <input
                id="audit-user-search"
                type="text"
                placeholder="Search users..."
                value={userSearch}
                onChange={handleUserSearchChange}
                className="input-glass w-full pl-10 pr-10 py-2 font-body"
              />
              {userSearch && (
                <button
                  onClick={clearUserSearch}
                  className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-orchestrated-glass hover:text-white transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Results Table */}
      <div className="glass-panel overflow-hidden">
        {/* Table Header */}
        <div className="grid grid-cols-4 gap-4 p-4 border-b border-white/10 text-sm font-medium text-orchestrated-glass font-heading">
          <div>User</div>
          <div>Action</div>
          <div>Entity</div>
          <div>Timestamp</div>
        </div>

        {/* Table Body */}
        <div className="divide-y divide-white/5 max-h-[500px] overflow-y-auto">
          {(() => {
            if (loading) {
              return (
                <div className="flex items-center justify-center py-16">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400" />
                </div>
              );
            }
            if (hasError) {
              return (
                <div className="flex flex-col items-center justify-center py-16 text-red-400">
                  <AlertTriangle className="h-12 w-12 mb-4" />
                  <p className="font-medium">Something went wrong</p>
                  <p className="text-sm text-orchestrated-glass mt-1">Please refresh the page</p>
                </div>
              );
            }
            if (error) {
              return (
                <div className="flex flex-col items-center justify-center py-16 text-red-400">
                  <AlertTriangle className="h-12 w-12 mb-4" />
                  <p className="font-medium">{error}</p>
                  <button
                    onClick={fetchAuditLog}
                    className="mt-4 text-sm text-cyan-400 hover:underline"
                  >
                    Retry
                  </button>
                </div>
              );
            }
            if (entries.length === 0) {
              return (
                <div className="flex items-center justify-center py-16 text-orchestrated-glass font-body">
                  No audit entries found
                </div>
              );
            }
            return entries.map((entry, index) => {
              const actionObj = actionConfig[entry.action_type] || { icon: <Eye className="h-4 w-4" />, color: 'text-gray-400' };
              const isSelected = selectedEntry?.id === entry.id;
              
              return (
                <button
                  key={entry.id}
                  type="button"
                  onClick={() => setSelectedEntry(isSelected ? null : entry)}
                  className={`grid w-full grid-cols-4 gap-4 p-4 cursor-pointer text-left transition-all ${
                    index % 2 === 0 ? 'bg-white/[0.02]' : 'bg-white/[0.01]'
                  } hover:bg-white/[0.06] ${
                    isSelected ? 'bg-white/[0.08] border-l-2 border-cyan-400' : ''
                  }`}
                >
                  <div className="flex items-center gap-2 font-body text-sm">
                    <User className="h-4 w-4 text-orchestrated-glass flex-shrink-0" />
                    <span className="truncate">{entry.user_name || 'System'}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={actionObj.color}>{actionObj.icon}</span>
                    <span className={`text-sm font-medium ${actionObj.color}`}>
                      {entry.action_type}
                    </span>
                  </div>
                  <div className="font-body text-sm">
                    {entry.entity_name || `${entityLabels[entry.entity_type] || entry.entity_type} #${entry.entity_id}`}
                  </div>
                  <div className="flex items-center gap-2 font-body text-sm text-orchestrated-glass">
                    <Clock className="h-4 w-4" />
                    {formatDate(entry.created_at)}
                  </div>
                </button>
              );
            });
          })()}
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between p-4 border-t border-white/10">
          <p className="text-sm text-orchestrated-glass font-body">
            Showing {entries.length > 0 ? page * limit + 1 : 0} - {Math.min((page + 1) * limit, total)} of {total} entries
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={goToPrevPage}
              disabled={page === 0}
              className="p-2 rounded-lg border border-white/10 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-sm font-body px-3">
              Page {total > 0 ? page + 1 : 0} of {totalPages || 1}
            </span>
            <button
              onClick={goToNextPage}
              disabled={page >= totalPages - 1 || totalPages === 0}
              className="p-2 rounded-lg border border-white/10 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Entry Details Panel - appears below table when entry selected */}
      {selectedEntry && (
        <div className="glass-panel-hover p-6 space-y-4">
          <h3 className="text-lg font-heading font-semibold">Entry Details</h3>
          
          <div className="grid grid-cols-2 gap-6">
            <div>
              <p className="text-xs text-orchestrated-glass font-body mb-1">Action</p>
              <div className="flex items-center gap-2">
                <span className={actionConfig[selectedEntry.action_type]?.color || 'text-gray-400'}>
                  {actionConfig[selectedEntry.action_type]?.icon || <Eye className="h-4 w-4" />}
                </span>
                <span className={`font-medium ${actionConfig[selectedEntry.action_type]?.color || 'text-gray-400'}`}>
                  {selectedEntry.action_type}
                </span>
              </div>
            </div>
            
            <div>
              <p className="text-xs text-orchestrated-glass font-body mb-1">Entity</p>
              <p className="font-medium font-body">
                {selectedEntry.entity_name || `${entityLabels[selectedEntry.entity_type] || selectedEntry.entity_type} #${selectedEntry.entity_id}`}
              </p>
            </div>
            
            <div>
              <p className="text-xs text-orchestrated-glass font-body mb-1">User</p>
              <p className="font-medium font-body">{selectedEntry.user_name || 'System'}</p>
            </div>
            
            <div>
              <p className="text-xs text-orchestrated-glass font-body mb-1">Timestamp</p>
              <p className="font-medium font-body">
                {formatDate(selectedEntry.created_at)}
              </p>
            </div>
          </div>

          {selectedEntry.changes && Object.keys(selectedEntry.changes).length > 0 && (
            <div>
              <p className="text-xs text-orchestrated-glass font-body mb-2">Changes</p>
              <div className="space-y-2">
                {Object.entries(selectedEntry.changes).map(([key, change]) => (
                  <div key={key} className="p-3 rounded-lg bg-white/5 font-mono text-sm">
                    <p className="font-medium text-cyan-400 mb-1">{key}</p>
                    <p className="text-red-400 line-through">{String(change.old || '')}</p>
                    <p className="text-green-400">{String(change.new || '')}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// MachineHistoryPanel - kept for machine-specific audit history
export const MachineHistoryPanel: React.FC = () => {
  // For now, redirect to main AuditLogViewer with filter
  // This could be enhanced later with machine-specific endpoint
  return (
    <div className="glass-panel p-6">
      <p className="text-orchestrated-glass font-body">
        Machine-specific history is now integrated into the main Audit Log view.
      </p>
      <p className="text-sm text-orchestrated-glass mt-2 font-body">
        Use the entity filter to view history for specific machines.
      </p>
    </div>
  );
};

export default AuditLogViewer;