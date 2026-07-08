import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  MessageSquare,
  X,
  Minimize2,
  Maximize2,
  Send,
  Loader2,
  Copy,
  Sparkles,
  Bot,
  User,
  ChevronDown,
  ChevronUp,
  Table,
  AlertTriangle,
  Plus,
  FileText,
  MessagesSquare,
  Trash2,
  Pencil,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';

const API = import.meta.env.VITE_API_BASE_URL || '';
const getToken = () => localStorage.getItem('access_token');

// ─── Types ────────────────────────────────────────────────────────────────────

interface AIMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
  sources?: Source[];
  timestamp: string;
}

interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

interface Source {
  tool: string;
  result: any[];
}

interface ChatSessionSummary {
  id: string;
  title: string;
  message_count: number;
  last_query?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

// ─── Utility: parse markdown tables ─────────────────────────────────────────

function parseTable(content: string): { headers: string[]; rows: string[][] } | null {
  const lines = content.split('\n').map((l) => l.trim()).filter(Boolean);
  const tableLines = lines.filter(
    (l) => l.startsWith('|') && !l.match(/^\|[\s\-:|]+\|$/) && l.includes('|')
  );
  if (tableLines.length < 2) return null;

  const headers = tableLines[0]
    .replace(/^\||\|$/g, '')
    .split('|')
    .map((h) => h.trim());
  const rows = tableLines.slice(1).map((row) =>
    row.replace(/^\||\|$/g, '').split('|').map((c) => c.trim())
  );
  return { headers, rows };
}

// ─── Utility: parse bullet/numbered lists ───────────────────────────────────

function parseLists(content: string): string[] | null {
  const lines = content.split('\n').filter(
    (l) => l.match(/^[-*•]|^(\d+)\.\s/) && l.length > 3
  );
  if (lines.length < 2) return null;
  return lines.map((l) => l.replace(/^[-*•]\s?|^(\d+)\.\s?/, '').trim());
}

// ─── Shared hook: doc upload (used by both ChatWidget and ChatPage) ─────────

function useDocUpload(toast: ReturnType<typeof useToast>['toast']) {
  const [showDocUpload, setShowDocUpload] = useState(false);
  const [docFile, setDocFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<'manual' | 'sop' | 'report'>('manual');
  const [docUploading, setDocUploading] = useState(false);

  const handleDocUpload = async () => {
    if (!docFile) return;
    setDocUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', docFile);
      fd.append('doc_type', docType);
      const res = await fetch(`${API}/api/v1/rag/documents`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        credentials: 'include',
        body: fd,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Erreur ${res.status}`);
      }
      toast({ title: 'Document ajouté à la base documentaire IA' });
      setShowDocUpload(false);
      setDocFile(null);
    } catch (e: any) {
      toast({ title: 'Erreur upload', description: e.message, variant: 'destructive' });
    } finally {
      setDocUploading(false);
    }
  };

  return { showDocUpload, setShowDocUpload, docFile, setDocFile, docType, setDocType, docUploading, handleDocUpload };
}

// ─── Shared hook: suggestions fetcher (used by both ChatWidget and ChatPage) ─

function useSuggestionsFetcher() {
  const [suggestions, setSuggestions] = useState<string[]>([]);

  const fetchSuggestions = async () => {
    try {
      const res = await fetch(`${API}/api/v1/chat/suggestions`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSuggestions(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error('Failed to fetch suggestions', err);
    }
  };

  return { suggestions, fetchSuggestions };
}

// ─── Component: RenderedMessage ──────────────────────────────────────────────

function RenderedMessage({ content, toolCalls, sources }: Readonly<{
  content: string;
  toolCalls?: ToolCall[];
  sources?: Source[];
}>) {
  const [showSources, setShowSources] = useState(false);

  // Try markdown table first
  const tableData = parseTable(content);
  const listItems = parseLists(content);

  return (
    <div className="space-y-3">
      {/* Main content */}
      {(() => {
      if (tableData) {
      return (
        <div className="overflow-x-auto">
          <div className="inline-block min-w-full">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-muted/50">
                  {tableData.headers.map((h, i) => (
                    <th key={i} className="px-3 py-2 text-left font-semibold border border-muted-foreground/20 first:rounded-l-md last:rounded-r-md">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tableData.rows.map((row, i) => (
                  <tr key={i} className="border border-muted-foreground/10 hover:bg-muted/30 transition-colors">
                    {row.map((cell, j) => (
                      <td key={j} className="px-3 py-2 border border-muted-foreground/10 first:last:rounded-l-md last:rounded-r-md">
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      );
      }
      if (listItems) {
      return (
        <ul className="space-y-1.5 pl-4">
          {listItems.map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-sm">
              <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      );
      }
      return (
        <p className="text-sm whitespace-pre-wrap leading-relaxed">{content}</p>
      );
      })()}

      {/* Sources panel */}
      {sources && sources.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setShowSources((v) => !v)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors mb-2"
          >
            {showSources ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {sources.length} database query result{sources.length > 1 ? 's' : ''} used
          </button>

          {showSources && sources.map((src, i) => (
            <div key={i} className="mt-2 border rounded-md overflow-hidden">
              <div className="bg-muted/50 px-3 py-1.5 flex items-center gap-2">
                <Table className="h-3 w-3 text-primary" />
                <span className="text-xs font-medium font-mono">{src.tool}</span>
                <span className="text-xs text-muted-foreground ml-auto">
                  {src.result?.length ?? 0} row{(src.result?.length ?? 0) !== 1 ? 's' : ''}
                </span>
              </div>
              {(src.result?.length ?? 0) > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b bg-muted/30">
                        {Object.keys(src.result[0]).map((k) => (
                          <th key={k} className="px-2 py-1 text-left font-medium text-muted-foreground first:last:rounded-l-md last:rounded-r-md">
                            {k.replace(/_/g, ' ')}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {src.result.slice(0, 5).map((row: any, ri: number) => (
                        <tr key={ri} className="border-b last:border-0 hover:bg-muted/20">
                          {Object.values(row).map((val: any, vi: number) => {
                            let cellContent: React.ReactNode;
                            if (val === null || val === undefined) {
                              cellContent = <span className="text-muted-foreground">—</span>;
                            } else if (typeof val === 'object') {
                              cellContent = JSON.stringify(val).slice(0, 40);
                            } else {
                              cellContent = String(val);
                            }
                            return (
                            <td key={vi} className="px-2 py-1 first:last:rounded-l-md last:rounded-r-md">
                              {cellContent}
                            </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {src.result.length > 5 && (
                    <div className="px-2 py-1 text-xs text-center text-muted-foreground bg-muted/20">
                      + {src.result.length - 5} more rows
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Tool call badges (if no formatted sources) */}
      {!sources && toolCalls && toolCalls.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {toolCalls.map((tc) => (
            <Badge key={tc.id} variant="secondary" className="text-xs font-mono">
              <Sparkles className="h-3 w-3 mr-1" />
              {tc.name}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Component: ChatWidget (floating) ─────────────────────────────────────────

export const ChatWidget: React.FC<{ machineId?: number }> = ({ machineId }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState<AIMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();
  const { suggestions, fetchSuggestions } = useSuggestionsFetcher();

  // Doc upload state
  const {
    showDocUpload,
    setShowDocUpload,
    docFile,
    setDocFile,
    docType,
    setDocType,
    docUploading,
    handleDocUpload,
  } = useDocUpload(toast);

  useEffect(() => {
    if (isOpen && suggestions.length === 0) {
      fetchSuggestions();
    }
  }, [isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (query?: string) => {
    const finalQuery = query || input;
    if (!finalQuery.trim() || loading) return;

    const userMsg: AIMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: finalQuery,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API}/api/v1/chat/ai/chat`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: finalQuery,
          ...(machineId !== undefined && { machine_id: machineId }),
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const aiMsg: AIMessage = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: data.message || data.formatted_message || '',
          toolCalls: data.tool_calls,
          sources: data.sources,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, aiMsg]);
      } else {
        const errText = await res.text();
        const aiMsg: AIMessage = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: `Erreur: ${errText.slice(0, 100)}`,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, aiMsg]);
      }
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de contacter l\'assistant IA',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({ title: 'Copié', description: 'Contenu copié dans le presse-papiers' });
  };

  if (!isOpen) {
    return (
      <Button
        className="fixed bottom-4 right-4 h-14 w-14 rounded-full shadow-2xl z-50 bg-primary hover:bg-primary/90"
        onClick={() => setIsOpen(true)}
        size="icon"
      >
        <Sparkles className="h-6 w-6" />
      </Button>
    );
  }

  return (
    <Card className={`fixed bottom-4 right-4 w-96 shadow-2xl z-50 border-2 ${isMinimized ? 'h-auto' : ''}`}>
      <CardHeader className="pb-2 border-b bg-gradient-to-r from-primary/5 to-transparent">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            Assistant IA
          </CardTitle>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setIsMinimized(!isMinimized)}>
              {isMinimized ? <Maximize2 className="h-4 w-4" /> : <Minimize2 className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setIsOpen(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>

      {!isMinimized && (
        <CardContent className="p-0">
          <ScrollArea className="h-80">
            <div className="p-4 space-y-4">
              {messages.length === 0 && (
                <div className="text-center text-muted-foreground py-10">
                  <Sparkles className="h-10 w-10 mx-auto mb-3 opacity-40" />
                  <p className="text-sm font-medium mb-1">Demandez-moi n'importe quoi !</p>
                  <p className="text-xs">
                    Machines, ordres de travail, alertes, interventions, plannings
                  </p>
                </div>
              )}

              {messages.map((msg) => (
                <div key={msg.id} className="space-y-2">
                  {/* User message */}
                  <div className="flex justify-end">
                    <div className="flex items-end gap-2 max-w-[85%]">
                      <div className="bg-primary text-primary-foreground px-3 py-2 rounded-2xl rounded-br-md text-sm">
                        {msg.content}
                      </div>
                      <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                        <User className="h-4 w-4 text-primary-foreground" />
                      </div>
                    </div>
                  </div>

                  {/* AI response */}
                  <div className="flex items-end gap-2 max-w-[85%]">
                    <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary/20 to-primary/40 flex items-center justify-center flex-shrink-0">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                    <div className="bg-muted/80 backdrop-blur-sm px-4 py-3 rounded-2xl rounded-bl-md border">
                      {msg.role === 'assistant' ? (
                        <RenderedMessage
                          content={msg.content}
                          toolCalls={msg.toolCalls}
                          sources={msg.sources}
                        />
                      ) : null}
                    </div>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex items-center gap-2 text-muted-foreground pl-10">
                  <Bot className="h-4 w-4 text-primary animate-pulse" />
                  <span className="text-sm">L'IA réfléchit...</span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Quick suggestions */}
          {suggestions.length > 0 && messages.length === 0 && (
            <div className="px-4 pb-2">
              <p className="text-xs text-muted-foreground mb-2">Essayez :</p>
              <div className="flex flex-wrap gap-1.5">
                {suggestions.slice(0, 4).map((s, i) => (
                  <Button key={i} variant="outline" size="sm" className="text-xs h-7" onClick={() => handleSubmit(s)}>
                    {s}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="p-4 border-t bg-muted/20">
            <form
              onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
              className="flex gap-2"
            >
              <Button
                type="button"
                size="icon"
                variant="outline"
                onClick={() => setShowDocUpload(true)}
                title="Importer un document dans la base RAG"
              >
                <Plus className="h-4 w-4" />
              </Button>
              <Input
                placeholder="Ask about machines, alerts..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
              />
              <Button type="submit" size="icon" disabled={loading || !input.trim()}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </form>
          </div>

          {/* Doc upload dialog */}
          <Dialog open={showDocUpload} onOpenChange={setShowDocUpload}>
            <DialogContent className="sm:max-w-sm">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-blue-500" />
                  Importer un document
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-3 py-2">
                <div>
                  <label className="text-sm font-medium block mb-1.5">Fichier (PDF ou TXT)</label>
                  <input
                    type="file"
                    accept=".pdf,.txt"
                    className="text-sm w-full"
                    onChange={(e) => setDocFile(e.target.files?.[0] ?? null)}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium block mb-1.5">Type</label>
                  <Select value={docType} onValueChange={(v: any) => setDocType(v)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="manual">Manuel technique</SelectItem>
                      <SelectItem value="sop">SOP</SelectItem>
                      <SelectItem value="report">Rapport d'intervention</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowDocUpload(false)} disabled={docUploading}>
                  Annuler
                </Button>
                <Button onClick={handleDocUpload} disabled={!docFile || docUploading} className="gap-2">
                  {docUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                  Importer
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </CardContent>
      )}
    </Card>
  );
};

// ─── Component: ChatPage (full page) ─────────────────────────────────────────

export const ChatPage: React.FC<{ machineId?: number }> = ({ machineId }) => {
  const [messages, setMessages] = useState<AIMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();
  const { suggestions, fetchSuggestions } = useSuggestionsFetcher();

  // Multi-conversation state
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  // Doc upload state
  const {
    showDocUpload,
    setShowDocUpload,
    docFile,
    setDocFile,
    docType,
    setDocType,
    docUploading,
    handleDocUpload,
  } = useDocUpload(toast);

  useEffect(() => {
    fetchSuggestions();
    bootstrapSessions();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── Multi-conversation session management ──────────────────────────────────

  const fetchSessions = async (): Promise<ChatSessionSummary[]> => {
    try {
      const res = await fetch(`${API}/api/v1/chat/sessions`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) {
        const data = (await res.json()) as ChatSessionSummary[];
        setSessions(Array.isArray(data) ? data : []);
        return Array.isArray(data) ? data : [];
      }
    } catch (err) {
      console.error('Failed to fetch sessions', err);
    }
    return [];
  };

  const fetchSessionHistory = async (sessionId: string | null) => {
    try {
      const url = sessionId
        ? `${API}/api/v1/chat/history?limit=50&session_id=${sessionId}`
        : `${API}/api/v1/chat/history?limit=50`;
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) {
        setMessages([]);
        return;
      }
      const data = await res.json();
      setCurrentSessionId(data.session_id ?? sessionId ?? null);
      const historyMessages: AIMessage[] = (data.history || [])
        .filter((h: any) => h && (h.role === 'user' || h.role === 'assistant') && h.content)
        .map((h: any, i: number) => ({
          id: `history-${i}-${Date.now()}`,
          role: h.role as 'user' | 'assistant',
          content: String(h.content),
          timestamp: h.timestamp || new Date().toISOString(),
        }));
      setMessages(historyMessages);
    } catch (err) {
      console.error('Failed to fetch session history', err);
      setMessages([]);
    }
  };

  const bootstrapSessions = async () => {
    const list = await fetchSessions();
    if (list.length === 0) {
      // No sessions yet — create one
      await createNewSession({ select: true, silent: true });
    } else {
      // Load most recent (already first in the list)
      await fetchSessionHistory(list[0].id);
    }
  };

  const createNewSession = async (opts: { select?: boolean; silent?: boolean } = {}) => {
    try {
      const res = await fetch(`${API}/api/v1/chat/sessions`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const s = (await res.json()) as ChatSessionSummary;
      setSessions((prev) => [s, ...prev]);
      if (opts.select !== false) {
        setCurrentSessionId(s.id);
        setMessages([]);
      }
      if (!opts.silent) toast({ title: 'Nouvelle conversation' });
    } catch {
      toast({
        title: 'Erreur',
        description: "Impossible de créer la conversation",
        variant: 'destructive',
      });
    }
  };

  const selectSession = async (id: string) => {
    if (id === currentSessionId) return;
    setCurrentSessionId(id);
    await fetchSessionHistory(id);
  };

  const deleteSession = async (id: string) => {
    if (!confirm('Supprimer cette conversation ?')) return;
    try {
      const res = await fetch(`${API}/api/v1/chat/sessions/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok && res.status !== 204) throw new Error(`HTTP ${res.status}`);
      const remaining = sessions.filter((s) => s.id !== id);
      setSessions(remaining);
      if (id === currentSessionId) {
        if (remaining.length > 0) {
          await selectSession(remaining[0].id);
        } else {
          await createNewSession({ select: true, silent: true });
        }
      }
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de supprimer',
        variant: 'destructive',
      });
    }
  };

  const renameSession = async (id: string) => {
    const current = sessions.find((s) => s.id === id);
    const next = prompt('Nouveau titre :', current?.title ?? '');
    if (!next || !next.trim()) return;
    try {
      const res = await fetch(`${API}/api/v1/chat/sessions/${id}`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ title: next.trim() }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const updated = (await res.json()) as ChatSessionSummary;
      setSessions((prev) => prev.map((s) => (s.id === id ? updated : s)));
    } catch {
      toast({
        title: 'Erreur',
        description: 'Renommage impossible',
        variant: 'destructive',
      });
    }
  };

  const handleSubmit = async (query?: string) => {
    const finalQuery = query || input;
    if (!finalQuery.trim() || loading) return;

    const userMsg: AIMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: finalQuery,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API}/api/v1/chat/ai/chat`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${getToken()}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: finalQuery,
          session_id: currentSessionId,
          ...(machineId !== undefined && { machine_id: machineId }),
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const aiMsg: AIMessage = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: data.message || '',
          toolCalls: data.tool_calls,
          sources: data.sources,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, aiMsg]);

        // Sync sidebar with server-side session state (auto-title + ordering)
        if (data.session_id) {
          setCurrentSessionId(data.session_id);
          await fetchSessions();
        }
      } else {
        const errText = await res.text();
        toast({ title: 'Erreur', description: `Erreur: ${errText.slice(0, 100)}`, variant: 'destructive' });
      }
    } catch {
      toast({ title: 'Erreur', description: 'Impossible de contacter l\'assistant IA', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            Assistant IA
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Powered by Groq — interrogez vos machines, ordres de travail, alertes et plannings
          </p>
        </div>
        <Badge variant="outline" className="text-xs">
          <Bot className="h-3 w-3 mr-1" />
          Groq LLM
        </Badge>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Conversations sidebar */}
        <Card className="lg:col-span-1 h-fit sticky top-4 border-2">
          <CardHeader className="pb-3 flex flex-row items-center justify-between gap-2 space-y-0">
            <CardTitle className="text-base flex items-center gap-2">
              <MessagesSquare className="h-4 w-4 text-primary" />
              Conversations
            </CardTitle>
            <Button
              size="sm"
              variant="outline"
              className="h-8 gap-1"
              onClick={() => createNewSession({ select: true })}
              title="Nouvelle conversation"
            >
              <Plus className="h-3.5 w-3.5" />
              Nouveau
            </Button>
          </CardHeader>
          <CardContent className="p-2 pt-0">
            <ScrollArea className="h-[500px]">
              <div className="space-y-1 pr-2">
                {sessions.length === 0 && (
                  <p className="text-xs text-muted-foreground text-center py-6">
                    Aucune conversation.
                  </p>
                )}
                {sessions.map((s) => {
                  const active = s.id === currentSessionId;
                  return (
                    <div
                      key={s.id}
                      className={`group flex items-center gap-1 rounded-md px-2 py-2 text-sm cursor-pointer transition-colors ${
                        active
                          ? 'bg-primary/10 text-foreground border border-primary/30'
                          : 'hover:bg-muted/60'
                      }`}
                      role="button"
                      tabIndex={0}
                      onClick={() => selectSession(s.id)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          selectSession(s.id);
                        }
                      }}
                    >
                      <MessageSquare className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="truncate text-sm font-medium">
                          {s.title || 'Nouvelle conversation'}
                        </div>
                        <div className="truncate text-xs text-muted-foreground">
                          {s.message_count} message{s.message_count > 1 ? 's' : ''}
                        </div>
                      </div>
                      <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-0.5 flex-shrink-0">
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-6 w-6"
                          onClick={(e) => {
                            e.stopPropagation();
                            renameSession(s.id);
                          }}
                          title="Renommer"
                        >
                          <Pencil className="h-3 w-3" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-6 w-6 hover:text-destructive"
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteSession(s.id);
                          }}
                          title="Supprimer"
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Chat area */}
        <Card className="lg:col-span-3 border-2">
          <CardContent className="p-0">
            <ScrollArea className="h-[550px]">
              <div className="p-6 space-y-6">
                {messages.length === 0 && (
                  <div className="text-center text-muted-foreground py-16">
                    <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 mb-4">
                      <Sparkles className="h-8 w-8 text-primary" />
                    </div>
                    <h3 className="text-lg font-semibold mb-2">Commencez une conversation</h3>
                    <p className="text-sm mb-6 max-w-md mx-auto">
                      Demandez en langage naturel — "Quelles sont les machines en panne ?", "Ordr es de travail en attente", "Alertes critiques"
                    </p>
                    <div className="flex flex-wrap justify-center gap-2">
                      {suggestions.slice(0, 6).map((s, i) => (
                        <Button key={i} variant="outline" size="sm" onClick={() => handleSubmit(s)}>
                          {s}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map((msg) => (
                  <div key={msg.id} className="space-y-3">
                    {msg.role === 'user' ? (
                      <div className="flex justify-end">
                        <div className="flex items-end gap-2 max-w-[75%]">
                          <div className="bg-primary text-primary-foreground px-4 py-3 rounded-2xl rounded-br-md text-sm">
                            {msg.content}
                          </div>
                          <div className="h-9 w-9 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                            <User className="h-4 w-4 text-primary-foreground" />
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-end gap-3">
                        <div className="h-10 w-10 rounded-full bg-gradient-to-br from-primary/20 to-primary/40 flex items-center justify-center flex-shrink-0">
                          <Bot className="h-5 w-5 text-primary" />
                        </div>
                        <div className="flex-1 bg-muted/60 backdrop-blur-sm px-5 py-4 rounded-2xl rounded-bl-md border min-w-0">
                          <div className="flex items-center gap-2 mb-3">
                            <Badge variant="secondary" className="text-xs font-medium">
                              <Sparkles className="h-3 w-3 mr-1" />
                              Assistant IA
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {new Date(msg.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                          <RenderedMessage
                            content={msg.content}
                            toolCalls={msg.toolCalls}
                            sources={msg.sources}
                          />
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 flex-shrink-0 self-start"
                          onClick={() => handleCopy(msg.content)}
                        >
                          <Copy className="h-3 w-3" />
                        </Button>
                      </div>
                    )}
                  </div>
                ))}

                {loading && (
                  <div className="flex items-center gap-3 pl-13">
                    <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center">
                      <Bot className="h-5 w-5 text-muted-foreground animate-pulse" />
                    </div>
                    <div className="bg-muted/60 px-4 py-3 rounded-2xl rounded-bl-md border">
                      <div className="flex items-center gap-2">
                        <div className="flex gap-1">
                          <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
                          <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '150ms' }} />
                          <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                        <span className="text-sm text-muted-foreground">L'IA réfléchit...</span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* Input bar */}
            <div className="p-4 border-t bg-muted/30">
              <form
                onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
                className="flex gap-3"
              >
                <Button
                  type="button"
                  size="icon"
                  variant="outline"
                  className="h-12 w-12 flex-shrink-0"
                  onClick={() => setShowDocUpload(true)}
                  title="Importer un document dans la base RAG"
                >
                  <Plus className="h-5 w-5" />
                </Button>
                <Input
                  placeholder="Tapez votre question... (ex: Machines en panne dans Zone A)"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={loading}
                  className="text-base h-12"
                />
                <Button
                  type="submit"
                  size="lg"
                  disabled={loading || !input.trim()}
                  className="h-12 px-6"
                >
                  {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
                </Button>
              </form>
            </div>

            {/* Doc upload dialog */}
            <Dialog open={showDocUpload} onOpenChange={setShowDocUpload}>
              <DialogContent className="sm:max-w-sm">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2">
                    <FileText className="h-5 w-5 text-blue-500" />
                    Importer un document
                  </DialogTitle>
                </DialogHeader>
                <div className="space-y-3 py-2">
                  <div>
                    <label className="text-sm font-medium block mb-1.5">Fichier (PDF ou TXT)</label>
                    <input
                      type="file"
                      accept=".pdf,.txt"
                      className="text-sm w-full"
                      onChange={(e) => setDocFile(e.target.files?.[0] ?? null)}
                    />
                  </div>
                  <div>
                    <label className="text-sm font-medium block mb-1.5">Type</label>
                    <Select value={docType} onValueChange={(v: any) => setDocType(v)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="manual">Manuel technique</SelectItem>
                        <SelectItem value="sop">SOP</SelectItem>
                        <SelectItem value="report">Rapport d'intervention</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowDocUpload(false)} disabled={docUploading}>
                    Annuler
                  </Button>
                  <Button onClick={handleDocUpload} disabled={!docFile || docUploading} className="gap-2">
                    {docUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                    Importer
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </CardContent>
        </Card>

        {/* Suggestions sidebar */}
        <Card className="h-fit sticky top-4">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-primary" />
              Exemples de questions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {[
                'Show machines in Zone A',
                'Show critical alerts',
                'Pending work orders',
                'Show me interventions',
                'Show plannings for this week',
                'Machines needing repair',
                'Show high priority alerts',
                'Work orders by CHEFTECH',
              ].map((s, i) => (
                <Button
                  key={i}
                  variant="ghost"
                  className="w-full justify-start text-left h-auto py-2.5 text-sm text-muted-foreground hover:text-foreground"
                  onClick={() => handleSubmit(s)}
                >
                  <Sparkles className="h-3 w-3 mr-2 flex-shrink-0 text-primary/60" />
                  {s}
                </Button>
              ))}
            </div>
            <Separator className="my-4" />
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Domains supported
              </p>
              <div className="flex flex-wrap gap-1.5">
                {['Machines', 'Work Orders', 'Alerts', 'Interventions', 'Plannings'].map((d) => (
                  <Badge key={d} variant="outline" className="text-xs">
                    {d}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ChatWidget;