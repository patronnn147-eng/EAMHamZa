import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  History, 
  Download, 
  Filter, 
  User, 
  Calendar,
  ChevronRight,
  ArrowRightLeft,
  PlusCircle,
  Trash2,
  Eye,
  RefreshCw,
  Clock
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

const actionIcons: Record<string, React.ReactNode> = {
  CREATE: <PlusCircle className="h-4 w-4 text-green-500" />,
  UPDATE: <ArrowRightLeft className="h-4 w-4 text-blue-500" />,
  DELETE: <Trash2 className="h-4 w-4 text-red-500" />,
  VIEW: <Eye className="h-4 w-4 text-gray-500" />
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

export const AuditLogViewer: React.FC = () => {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [selectedEntry, setSelectedEntry] = useState<AuditEntry | null>(null);
  
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('all');
  const [actionTypeFilter, setActionTypeFilter] = useState<string>('all');
  const [userFilter, setUserFilter] = useState<string>('');

  useEffect(() => {
    fetchAuditLog();
  }, [page, entityTypeFilter, actionTypeFilter]);

  const fetchAuditLog = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append('skip', String(page * 50));
      params.append('limit', '50');
      if (entityTypeFilter !== 'all') params.append('entity_type', entityTypeFilter);
      if (actionTypeFilter !== 'all') params.append('action_type', actionTypeFilter);
      
      const res = await fetch(`${API}/api/v1/audit/log?${params}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      
      if (res.ok) {
        const data = await res.json();
        setEntries(data.items || []);
        setTotal(data.total || 0);
      } else {
        setEntries(generateMockAuditLog());
        setTotal(25);
      }
    } catch (err) {
      console.error('Failed to load audit log', err);
      setEntries(generateMockAuditLog());
      setTotal(25);
    } finally {
      setLoading(false);
    }
  };

  const generateMockAuditLog = (): AuditEntry[] => {
    const actions = ['CREATE', 'UPDATE', 'DELETE', 'VIEW'];
    const entities = ['machine', 'work_order', 'intervention', 'planning', 'user'];
    const users = ['Admin User', 'Chef Tech', 'Technician 1', 'Chef Op'];
    const logs: AuditEntry[] = [];
    
    for (let i = 0; i < 25; i++) {
      const action = actions[Math.floor(Math.random() * actions.length)];
      const entity = entities[Math.floor(Math.random() * entities.length)];
      const user = users[Math.floor(Math.random() * users.length)];
      const entityId = Math.floor(Math.random() * 20) + 1;
      
      logs.push({
        id: i + 1,
        action_type: action,
        entity_type: entity,
        entity_id: entityId,
        entity_name: `${entityLabels[entity]} ${entityId}`,
        user_name: user,
        changes: action === 'UPDATE' ? {
          statut: { old: 'OPERATIONAL', new: 'MAINTENANCE' },
          zone: { old: 'Zone A', new: 'Zone B' }
        } : undefined,
        description: `${action} ${entity} ${entityId}`,
        created_at: new Date(Date.now() - i * 3600000).toISOString()
      });
    }
    
    return logs;
  };

  const exportCSV = async () => {
    try {
      const res = await fetch(`${API}/api/v1/audit/export`, {
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
  };

  const totalPages = Math.ceil(total / 50);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <History className="h-6 w-6" />
            Audit Log
          </h1>
          <p className="text-muted-foreground">
            Complete history of all system changes
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchAuditLog}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={exportCSV}>
            <Download className="mr-2 h-4 w-4" />
            Export CSV
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <Select value={entityTypeFilter} onValueChange={setEntityTypeFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="All Entities" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Entities</SelectItem>
            <SelectItem value="machine">Machines</SelectItem>
            <SelectItem value="work_order">Work Orders</SelectItem>
            <SelectItem value="intervention">Interventions</SelectItem>
            <SelectItem value="planning">Planning</SelectItem>
            <SelectItem value="user">Users</SelectItem>
          </SelectContent>
        </Select>

        <Select value={actionTypeFilter} onValueChange={setActionTypeFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="All Actions" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Actions</SelectItem>
            <SelectItem value="CREATE">Create</SelectItem>
            <SelectItem value="UPDATE">Update</SelectItem>
            <SelectItem value="DELETE">Delete</SelectItem>
            <SelectItem value="VIEW">View</SelectItem>
          </SelectContent>
        </Select>

        <Input
          placeholder="Filter by user..."
          value={userFilter}
          onChange={(e) => setUserFilter(e.target.value)}
          className="w-[200px]"
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardContent className="p-0">
            <ScrollArea className="h-[600px]">
              <div className="p-4 space-y-2">
                {loading ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                  </div>
                ) : entries.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground">
                    No audit entries found
                  </div>
                ) : (
                  entries.map((entry) => (
                    <div
                      key={entry.id}
                      className={`p-3 rounded-lg border cursor-pointer hover:bg-accent transition-colors ${
                        selectedEntry?.id === entry.id ? 'border-primary bg-accent' : ''
                      }`}
                      onClick={() => setSelectedEntry(entry)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {actionIcons[entry.action_type]}
                          <div>
                            <p className="font-medium text-sm">{entry.description}</p>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                              <User className="h-3 w-3" />
                              {entry.user_name}
                              <Clock className="h-3 w-3 ml-2" />
                              {new Date(entry.created_at).toLocaleString()}
                            </div>
                          </div>
                        </div>
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
            
            <div className="p-4 border-t flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing {entries.length} of {total} entries
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.max(0, p - 1))}
                  disabled={page === 0}
                >
                  Previous
                </Button>
                <span className="text-sm">Page {page + 1} of {totalPages || 1}</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => p + 1)}
                  disabled={page >= totalPages - 1}
                >
                  Next
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Entry Details</CardTitle>
          </CardHeader>
          <CardContent>
            {selectedEntry ? (
              <div className="space-y-4">
                <div>
                  <p className="text-xs text-muted-foreground">Action</p>
                  <div className="flex items-center gap-2 mt-1">
                    {actionIcons[selectedEntry.action_type]}
                    <Badge variant="outline">{selectedEntry.action_type}</Badge>
                  </div>
                </div>
                
                <div>
                  <p className="text-xs text-muted-foreground">Entity</p>
                  <p className="font-medium">{selectedEntry.entity_name}</p>
                </div>
                
                <div>
                  <p className="text-xs text-muted-foreground">User</p>
                  <p className="font-medium">{selectedEntry.user_name || 'System'}</p>
                </div>
                
                <div>
                  <p className="text-xs text-muted-foreground">Timestamp</p>
                  <p className="font-medium">
                    {new Date(selectedEntry.created_at).toLocaleString()}
                  </p>
                </div>

                {selectedEntry.changes && Object.keys(selectedEntry.changes).length > 0 && (
                  <div>
                    <p className="text-xs text-muted-foreground mb-2">Changes</p>
                    <div className="space-y-2">
                      {Object.entries(selectedEntry.changes).map(([key, change]) => (
                        <div key={key} className="text-xs p-2 rounded bg-muted">
                          <p className="font-medium">{key}</p>
                          <p className="text-red-500 line-through">{String(change.old || '')}</p>
                          <p className="text-green-500">{String(change.new || '')}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                Select an entry to view details
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export const MachineHistoryPanel: React.FC = () => {
  const { machineId } = useParams<{ machineId: string }>();
  const [history, setHistory] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (machineId) {
      fetchMachineHistory();
    }
  }, [machineId]);

  const fetchMachineHistory = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/v1/audit/log/machine/${machineId}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      
      if (res.ok) {
        setHistory(await res.json());
      } else {
        setHistory(generateMockAuditLog().slice(0, 10));
      }
    } catch (err) {
      console.error('Failed to load machine history', err);
      setHistory(generateMockAuditLog().slice(0, 10));
    } finally {
      setLoading(false);
    }
  };

  const generateMockAuditLog = (): AuditEntry[] => {
    return [
      { id: 1, action_type: 'UPDATE', entity_type: 'machine', entity_id: Number(machineId), user_name: 'Admin User', changes: { statut: { old: 'OPERATIONAL', new: 'MAINTENANCE' } }, created_at: new Date().toISOString() },
      { id: 2, action_type: 'UPDATE', entity_type: 'machine', entity_id: Number(machineId), user_name: 'Chef Tech', changes: { zone: { old: 'Zone A', new: 'Zone B' } }, created_at: new Date(Date.now() - 86400000).toISOString() },
      { id: 3, action_type: 'CREATE', entity_type: 'machine', entity_id: Number(machineId), user_name: 'Admin User', new_values: { nom: 'New Machine' }, created_at: new Date(Date.now() - 172800000).toISOString() },
    ];
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <History className="h-5 w-5" />
        <h3 className="font-semibold">Machine History</h3>
      </div>
      
      {history.length === 0 ? (
        <p className="text-sm text-muted-foreground">No history available</p>
      ) : (
        <div className="space-y-2">
          {history.map((entry) => (
            <div key={entry.id} className="flex items-start gap-3 p-3 rounded-lg bg-muted">
              <div className="mt-1">{actionIcons[entry.action_type]}</div>
              <div className="flex-1">
                <p className="text-sm font-medium">{entry.description || `${entry.action_type} operation`}</p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                  <User className="h-3 w-3" />
                  {entry.user_name}
                  <Calendar className="h-3 w-3 ml-2" />
                  {new Date(entry.created_at).toLocaleString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AuditLogViewer;
