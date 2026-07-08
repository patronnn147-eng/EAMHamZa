import { useEffect, useRef, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import {
  FileText,
  Upload,
  Trash2,
  Search,
  Database,
  User,
  Clock,
  Loader2,
  Download,
  RefreshCw,
  FolderUp,
  AlertCircle,
  CheckCircle2,
  CloudDownload,
} from 'lucide-react';
import { getAPIBaseURL } from '@/lib/config';

// ─── Types ────────────────────────────────────────────────────────────────────

interface RagDocument {
  id: string;
  filename: string;
  doc_type: string;
  description?: string;
  machine_id?: number;
  chunk_count: number;
  file_size_bytes?: number;
  uploaded_by?: number;
  uploader_name?: string;
  created_at?: string;
  s3_object_key?: string;
  download_url?: string;
}

interface BulkResult {
  succeeded: RagDocument[];
  failed: { filename: string; error: string }[];
  total: number;
}

// ─── API helpers ──────────────────────────────────────────────────────────────

const getAuthHeaders = (): Record<string, string> => ({
  Authorization: `Bearer ${localStorage.getItem('access_token') ?? ''}`,
});

const BASE = () => `${getAPIBaseURL()}/api/v1/rag`;

// ─── Formatters ───────────────────────────────────────────────────────────────

function formatFileSize(bytes?: number): string {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(iso?: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

const DOC_TYPE_CONFIG: Record<string, { label: string; className: string }> = {
  manual: { label: 'Manuel', className: 'bg-blue-100 text-blue-800 border-blue-200' },
  sop:    { label: 'SOP',    className: 'bg-green-100 text-green-800 border-green-200' },
  report: { label: 'Rapport', className: 'bg-orange-100 text-orange-800 border-orange-200' },
};

// ─── Component ────────────────────────────────────────────────────────────────

export default function RAGDocuments() {
  const { user } = useAuth();
  const { toast } = useToast();
  const isAdmin = (user?.role ?? '').toUpperCase() === 'ADMIN';

  // List state
  const [documents, setDocuments] = useState<RagDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [docTypeFilter, setDocTypeFilter] = useState('ALL');

  // Single upload modal state
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadDocType, setUploadDocType] = useState<'manual' | 'sop' | 'report'>('manual');
  const [uploadMachineId, setUploadMachineId] = useState('');
  const [uploadDescription, setUploadDescription] = useState('');

  // Bulk import modal state
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [bulkFiles, setBulkFiles] = useState<File[]>([]);
  const [bulkDocType, setBulkDocType] = useState<'manual' | 'sop' | 'report'>('manual');
  const [bulkMachineId, setBulkMachineId] = useState('');
  const [bulkUploading, setBulkUploading] = useState(false);
  const [bulkResult, setBulkResult] = useState<BulkResult | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const bulkFileInputRef = useRef<HTMLInputElement>(null);

  // Replace modal state
  const [replaceTarget, setReplaceTarget] = useState<RagDocument | null>(null);
  const [replaceFile, setReplaceFile] = useState<File | null>(null);
  const [replacing, setReplacing] = useState(false);

  // S3 sync state
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    fetchDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docTypeFilter]);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (docTypeFilter !== 'ALL') params.set('doc_type', docTypeFilter);
      // Admins get presigned download URLs in the list response
      if (isAdmin) params.set('include_download_url', 'true');
      const res = await fetch(`${BASE()}/documents?${params.toString()}`, {
        headers: getAuthHeaders(),
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Failed to load documents');
      setDocuments(await res.json());
    } catch (e: any) {
      toast({ title: 'Error', description: e.message, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  // ── Single upload ──
  const handleUpload = async () => {
    if (!uploadFile) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', uploadFile);
      fd.append('doc_type', uploadDocType);
      if (uploadMachineId.trim()) fd.append('machine_id', uploadMachineId.trim());
      if (uploadDescription.trim()) fd.append('description', uploadDescription.trim());

      const res = await fetch(`${BASE()}/documents`, {
        method: 'POST',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: fd,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      toast({
        title: 'Document imported',
        description: `${uploadFile.name} ingested into AI knowledge base.`,
      });
      setShowUploadModal(false);
      setUploadFile(null);
      setUploadMachineId('');
      setUploadDescription('');
      setUploadDocType('manual');
      fetchDocuments();
    } catch (e: any) {
      toast({ title: 'Import failed', description: e.message, variant: 'destructive' });
    } finally {
      setUploading(false);
    }
  };

  // ── Bulk upload ──
  const handleBulkUpload = async () => {
    if (!bulkFiles.length) return;
    setBulkUploading(true);
    setBulkResult(null);
    try {
      const fd = new FormData();
      bulkFiles.forEach((f) => fd.append('files', f));
      fd.append('doc_type', bulkDocType);
      if (bulkMachineId.trim()) fd.append('machine_id', bulkMachineId.trim());

      const res = await fetch(`${BASE()}/documents/bulk`, {
        method: 'POST',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: fd,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      const result: BulkResult = await res.json();
      setBulkResult(result);
      toast({
        title: 'Bulk import complete',
        description: `${result.succeeded.length}/${result.total} ingested. ${result.failed.length} failed.`,
        variant: result.failed.length ? 'destructive' : 'default',
      });
      fetchDocuments();
    } catch (e: any) {
      toast({ title: 'Bulk import failed', description: e.message, variant: 'destructive' });
    } finally {
      setBulkUploading(false);
    }
  };

  const removeBulkFile = (index: number) =>
    setBulkFiles((prev) => prev.filter((_, i) => i !== index));

  const onBulkDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files || []).filter((f) =>
      /\.(pdf|txt)$/i.test(f.name)
    );
    if (files.length === 0) {
      toast({ title: 'No valid files', description: 'Only PDF/TXT allowed.', variant: 'destructive' });
      return;
    }
    setBulkFiles((prev) => [...prev, ...files].slice(0, 50));
  };

  // ── Sync from MinIO/S3 ──
  const handleSyncFromS3 = async () => {
    setSyncing(true);
    try {
      const fd = new FormData();
      fd.append('doc_type', 'manual');
      const res = await fetch(`${BASE()}/documents/sync`, {
        method: 'POST',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: fd,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      const result: BulkResult = await res.json();
      if (result.total === 0) {
        toast({ title: 'Already in sync', description: 'No new files found in S3.' });
      } else {
        toast({
          title: 'S3 sync complete',
          description: `${result.succeeded.length}/${result.total} new files ingested. ${result.failed.length} failed.`,
          variant: result.failed.length ? 'destructive' : 'default',
        });
      }
      fetchDocuments();
    } catch (e: any) {
      toast({ title: 'Sync failed', description: e.message, variant: 'destructive' });
    } finally {
      setSyncing(false);
    }
  };

  // ── Download ──
  const handleDownload = async (doc: RagDocument) => {
    try {
      let url = doc.download_url;
      if (!url) {
        const res = await fetch(`${BASE()}/documents/${doc.id}/download`, {
          headers: getAuthHeaders(),
          credentials: 'include',
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `Error ${res.status}`);
        }
        url = (await res.json()).download_url;
      }
      if (!url) throw new Error('No download URL available.');
      window.open(url, '_blank');
    } catch (e: any) {
      toast({ title: 'Download failed', description: e.message, variant: 'destructive' });
    }
  };

  // ── Replace ──
  const handleReplace = async () => {
    if (!replaceTarget || !replaceFile) return;
    setReplacing(true);
    try {
      const fd = new FormData();
      fd.append('file', replaceFile);
      const res = await fetch(`${BASE()}/documents/${replaceTarget.id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: fd,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      toast({
        title: 'Document replaced',
        description: `${replaceTarget.filename} replaced and re-ingested.`,
      });
      setReplaceTarget(null);
      setReplaceFile(null);
      fetchDocuments();
    } catch (e: any) {
      toast({ title: 'Replace failed', description: e.message, variant: 'destructive' });
    } finally {
      setReplacing(false);
    }
  };

  // ── Delete ──
  const handleDelete = async (doc: RagDocument) => {
    if (!window.confirm(`Delete "${doc.filename}" and all its vector chunks? File will also be removed from S3.`)) return;
    try {
      const res = await fetch(`${BASE()}/documents/${doc.id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
        credentials: 'include',
      });
      if (!res.ok && res.status !== 204) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      toast({ title: 'Document deleted', description: doc.filename });
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (e: any) {
      toast({ title: 'Delete failed', description: e.message, variant: 'destructive' });
    }
  };

  const filtered = documents.filter((d) =>
    d.filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Database className="h-7 w-7 text-blue-500" />
          <div>
            <h1 className="text-2xl font-bold">RAG Knowledge Base</h1>
            <p className="text-sm text-muted-foreground">
              Manuals, SOPs and reports trained into the AI assistant — files stored in S3 bucket <code className="text-xs bg-muted px-1 rounded">rag-docs</code>
            </p>
          </div>
        </div>
        {isAdmin && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleSyncFromS3}
              disabled={syncing}
              className="gap-2"
              title="Scan the rag-docs bucket for files uploaded directly to MinIO and ingest them"
            >
              {syncing ? <Loader2 className="h-4 w-4 animate-spin" /> : <CloudDownload className="h-4 w-4" />}
              Sync from S3
            </Button>
            <Button variant="outline" onClick={() => setShowBulkModal(true)} className="gap-2">
              <FolderUp className="h-4 w-4" />
              Bulk Import
            </Button>
            <Button onClick={() => setShowUploadModal(true)} className="gap-2">
              <Upload className="h-4 w-4" />
              Import Document
            </Button>
          </div>
        )}
      </div>

      {/* Non-admin notice */}
      {!isAdmin && (
        <div className="flex items-center gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-900">
          <AlertCircle className="h-4 w-4" />
          Read-only view. Only ADMIN users can upload, replace, or delete documents.
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by filename…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={docTypeFilter} onValueChange={setDocTypeFilter}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Document type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All types</SelectItem>
            <SelectItem value="manual">Manual</SelectItem>
            <SelectItem value="sop">SOP</SelectItem>
            <SelectItem value="report">Report</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Document list */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base text-muted-foreground">
            {filtered.length} document{filtered.length !== 1 ? 's' : ''}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {(() => {
          if (loading) {
            return (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
            );
          }
          if (filtered.length === 0) {
          return (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground gap-3">
              <Database className="h-12 w-12 opacity-20" />
              <p className="text-sm">
                {searchTerm || docTypeFilter !== 'ALL'
                  ? 'No matching documents.'
                  : 'No documents yet. Import your first file to train the AI.'}
              </p>
              {isAdmin && !searchTerm && docTypeFilter === 'ALL' && (
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setShowUploadModal(true)} className="gap-2 mt-1">
                    <Upload className="h-4 w-4" />
                    Import single
                  </Button>
                  <Button variant="outline" onClick={() => setShowBulkModal(true)} className="gap-2 mt-1">
                    <FolderUp className="h-4 w-4" />
                    Bulk import
                  </Button>
                </div>
              )}
            </div>
          );
          }
          return (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground text-xs uppercase tracking-wider">
                    <th className="text-left py-2 px-3 font-medium">File</th>
                    <th className="text-left py-2 px-3 font-medium">Type</th>
                    <th className="text-left py-2 px-3 font-medium">Chunks</th>
                    <th className="text-left py-2 px-3 font-medium">Size</th>
                    <th className="text-left py-2 px-3 font-medium">Machine</th>
                    {isAdmin && (
                      <>
                        <th className="text-left py-2 px-3 font-medium">Uploaded by</th>
                        <th className="text-left py-2 px-3 font-medium">Date</th>
                      </>
                    )}
                    <th className="py-2 px-3 text-right" />
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((doc) => {
                    const typeConf = DOC_TYPE_CONFIG[doc.doc_type] ?? {
                      label: doc.doc_type,
                      className: 'bg-gray-100 text-gray-800',
                    };
                    return (
                      <tr key={doc.id} className="border-b last:border-0 hover:bg-muted/30 transition-colors">
                        <td className="py-3 px-3">
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-blue-400 flex-shrink-0" />
                            <span className="font-medium truncate max-w-xs" title={doc.filename}>
                              {doc.filename}
                            </span>
                          </div>
                          {doc.description && (
                            <p className="text-xs text-muted-foreground mt-0.5 ml-6 truncate max-w-xs">
                              {doc.description}
                            </p>
                          )}
                          {!doc.s3_object_key && isAdmin && (
                            <p className="text-xs text-orange-600 mt-0.5 ml-6">
                              ⚠ Legacy doc (no S3 backup)
                            </p>
                          )}
                        </td>
                        <td className="py-3 px-3">
                          <Badge variant="outline" className={`text-xs ${typeConf.className}`}>
                            {typeConf.label}
                          </Badge>
                        </td>
                        <td className="py-3 px-3 text-muted-foreground">
                          {doc.chunk_count} chunks
                        </td>
                        <td className="py-3 px-3 text-muted-foreground">
                          {formatFileSize(doc.file_size_bytes)}
                        </td>
                        <td className="py-3 px-3">
                          {doc.machine_id ? (
                            <Badge variant="secondary" className="text-xs">
                              M-{doc.machine_id}
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                        {isAdmin && (
                          <>
                            <td className="py-3 px-3">
                              <div className="flex items-center gap-1.5 text-muted-foreground">
                                <User className="h-3.5 w-3.5" />
                                <span>{doc.uploader_name ?? '—'}</span>
                              </div>
                            </td>
                            <td className="py-3 px-3">
                              <div className="flex items-center gap-1.5 text-muted-foreground">
                                <Clock className="h-3.5 w-3.5" />
                                <span>{formatDate(doc.created_at)}</span>
                              </div>
                            </td>
                          </>
                        )}
                        <td className="py-3 px-3 text-right">
                          <div className="flex items-center gap-1 justify-end">
                            {isAdmin && doc.s3_object_key && (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-8 w-8 p-0 text-blue-600 hover:bg-blue-50"
                                onClick={() => handleDownload(doc)}
                                title="Download original file"
                              >
                                <Download className="h-4 w-4" />
                              </Button>
                            )}
                            {isAdmin && (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-8 w-8 p-0 text-amber-600 hover:bg-amber-50"
                                onClick={() => { setReplaceTarget(doc); setReplaceFile(null); }}
                                title="Replace file (re-ingest)"
                              >
                                <RefreshCw className="h-4 w-4" />
                              </Button>
                            )}
                            {isAdmin && (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-destructive hover:text-destructive hover:bg-destructive/10 h-8 w-8 p-0"
                                onClick={() => handleDelete(doc)}
                                title="Delete document"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
          })()}
        </CardContent>
      </Card>

      {/* ─── Single upload Modal ─── */}
      <Dialog open={showUploadModal} onOpenChange={setShowUploadModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5 text-blue-500" />
              Import a Document
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <label htmlFor="rag-upload-file" className="text-sm font-medium">File <span className="text-destructive">*</span></label>
              <div className="flex items-center gap-2">
                <label className="flex-1 cursor-pointer">
                  <div className="border-2 border-dashed rounded-lg p-4 text-center hover:border-primary/50 transition-colors">
                    {uploadFile ? (
                      <div className="flex items-center justify-center gap-2 text-sm">
                        <FileText className="h-4 w-4 text-blue-500" />
                        <span className="font-medium truncate max-w-xs">{uploadFile.name}</span>
                        <span className="text-muted-foreground">({formatFileSize(uploadFile.size)})</span>
                      </div>
                    ) : (
                      <div className="text-muted-foreground text-sm">
                        <Upload className="h-6 w-6 mx-auto mb-1 opacity-40" />
                        Click to select a PDF or TXT file
                      </div>
                    )}
                  </div>
                  <input
                    id="rag-upload-file"
                    type="file"
                    accept=".pdf,.txt"
                    className="sr-only"
                    onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                  />
                </label>
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="rag-upload-doctype" className="text-sm font-medium">Document type <span className="text-destructive">*</span></label>
              <Select value={uploadDocType} onValueChange={(v: any) => setUploadDocType(v)}>
                <SelectTrigger id="rag-upload-doctype">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="manual">Technical Manual</SelectItem>
                  <SelectItem value="sop">SOP — Standard Operating Procedure</SelectItem>
                  <SelectItem value="report">Intervention Report</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="rag-upload-machine-id" className="text-sm font-medium">
                Machine ID <span className="text-muted-foreground text-xs">(optional)</span>
              </label>
              <Input
                id="rag-upload-machine-id"
                type="number"
                placeholder="e.g. 42"
                value={uploadMachineId}
                onChange={(e) => setUploadMachineId(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Link this document to a specific machine for targeted retrieval.
              </p>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="rag-upload-description" className="text-sm font-medium">
                Description <span className="text-muted-foreground text-xs">(optional)</span>
              </label>
              <Textarea
                id="rag-upload-description"
                placeholder="e.g. Maintenance manual for Atlas Copco GA18 compressor"
                value={uploadDescription}
                onChange={(e) => setUploadDescription(e.target.value)}
                rows={2}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUploadModal(false)} disabled={uploading}>
              Cancel
            </Button>
            <Button onClick={handleUpload} disabled={!uploadFile || uploading} className="gap-2">
              {uploading ? (
                <><Loader2 className="h-4 w-4 animate-spin" />Ingesting…</>
              ) : (
                <><Upload className="h-4 w-4" />Import</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ─── Bulk import Modal ─── */}
      <Dialog open={showBulkModal} onOpenChange={(o) => { setShowBulkModal(o); if (!o) { setBulkFiles([]); setBulkResult(null); } }}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FolderUp className="h-5 w-5 text-blue-500" />
              Bulk Import — Train AI with Multiple Documents
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <p className="text-sm text-muted-foreground">
              Drag-drop or select up to 50 PDF/TXT files. Each will be uploaded to S3 and ingested in parallel.
            </p>

            {/* Drop zone */}
            <div
              className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                dragOver ? 'border-blue-500 bg-blue-50' : 'border-muted hover:border-primary/50'
              }`}
              role="button"
              tabIndex={0}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onBulkDrop}
              onClick={() => bulkFileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  bulkFileInputRef.current?.click();
                }
              }}
            >
              <FolderUp className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
              <p className="text-sm font-medium">Drop files here or click to browse</p>
              <p className="text-xs text-muted-foreground mt-1">PDF / TXT — max 50 files</p>
              <input
                ref={bulkFileInputRef}
                type="file"
                accept=".pdf,.txt"
                multiple
                className="sr-only"
                onChange={(e) => {
                  const files = Array.from(e.target.files || []);
                  setBulkFiles((prev) => [...prev, ...files].slice(0, 50));
                }}
              />
            </div>

            {/* File list */}
            {bulkFiles.length > 0 && (
              <div className="border rounded-lg max-h-40 overflow-y-auto">
                <div className="p-2 border-b bg-muted/50 text-xs font-medium">
                  {bulkFiles.length} file{bulkFiles.length !== 1 ? 's' : ''} ready
                </div>
                <ul className="text-xs divide-y">
                  {bulkFiles.map((f, idx) => (
                    <li key={`${f.name}-${f.size}-${f.lastModified}`} className="flex items-center justify-between p-2">
                      <span className="truncate flex-1">{f.name}</span>
                      <span className="text-muted-foreground ml-2">{formatFileSize(f.size)}</span>
                      <button
                        className="ml-2 text-destructive hover:underline"
                        onClick={() => removeBulkFile(idx)}
                        disabled={bulkUploading}
                      >
                        Remove
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Shared metadata */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label htmlFor="rag-bulk-doctype" className="text-xs font-medium">Default type</label>
                <Select value={bulkDocType} onValueChange={(v: any) => setBulkDocType(v)}>
                  <SelectTrigger id="rag-bulk-doctype"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manual">Manual</SelectItem>
                    <SelectItem value="sop">SOP</SelectItem>
                    <SelectItem value="report">Report</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <label htmlFor="rag-bulk-machine-id" className="text-xs font-medium">Default machine ID</label>
                <Input
                  id="rag-bulk-machine-id"
                  type="number"
                  placeholder="(optional)"
                  value={bulkMachineId}
                  onChange={(e) => setBulkMachineId(e.target.value)}
                />
              </div>
            </div>

            {/* Result */}
            {bulkResult && (
              <div className="border rounded-lg p-3 space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  {bulkResult.succeeded.length} / {bulkResult.total} succeeded
                </div>
                {bulkResult.failed.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 text-sm font-medium text-destructive">
                      <AlertCircle className="h-4 w-4" />
                      {bulkResult.failed.length} failed
                    </div>
                    <ul className="text-xs mt-1 ml-6 list-disc text-muted-foreground">
                      {bulkResult.failed.map((f, i) => (
                        <li key={i}>{f.filename}: {f.error}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBulkModal(false)} disabled={bulkUploading}>
              Close
            </Button>
            <Button onClick={handleBulkUpload} disabled={!bulkFiles.length || bulkUploading} className="gap-2">
              {bulkUploading ? (
                <><Loader2 className="h-4 w-4 animate-spin" />Importing {bulkFiles.length} files…</>
              ) : (
                <><FolderUp className="h-4 w-4" />Import {bulkFiles.length} file{bulkFiles.length !== 1 ? 's' : ''}</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ─── Replace Modal ─── */}
      <Dialog open={!!replaceTarget} onOpenChange={(o) => { if (!o) { setReplaceTarget(null); setReplaceFile(null); } }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5 text-amber-500" />
              Replace Document
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <p className="text-sm text-muted-foreground">
              Replace <strong>{replaceTarget?.filename}</strong>. All existing chunks will be deleted
              and the new file will be re-ingested. The document ID stays the same.
            </p>
            <label className="cursor-pointer">
              <div className="border-2 border-dashed rounded-lg p-4 text-center hover:border-primary/50 transition-colors">
                {replaceFile ? (
                  <div className="flex items-center justify-center gap-2 text-sm">
                    <FileText className="h-4 w-4 text-blue-500" />
                    <span className="font-medium truncate max-w-xs">{replaceFile.name}</span>
                    <span className="text-muted-foreground">({formatFileSize(replaceFile.size)})</span>
                  </div>
                ) : (
                  <div className="text-muted-foreground text-sm">
                    <Upload className="h-6 w-6 mx-auto mb-1 opacity-40" />
                    Select replacement PDF / TXT file
                  </div>
                )}
              </div>
              <input
                type="file"
                accept=".pdf,.txt"
                className="sr-only"
                onChange={(e) => setReplaceFile(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setReplaceTarget(null); setReplaceFile(null); }} disabled={replacing}>
              Cancel
            </Button>
            <Button onClick={handleReplace} disabled={!replaceFile || replacing} className="gap-2 bg-amber-600 hover:bg-amber-700">
              {replacing ? (
                <><Loader2 className="h-4 w-4 animate-spin" />Replacing…</>
              ) : (
                <><RefreshCw className="h-4 w-4" />Replace & Re-ingest</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
