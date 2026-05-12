import { useEffect, useState } from 'react';
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
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

const DOC_TYPE_CONFIG: Record<string, { label: string; className: string }> = {
  manual: { label: 'Manuel', className: 'bg-blue-100 text-blue-800 border-blue-200' },
  sop: { label: 'SOP', className: 'bg-green-100 text-green-800 border-green-200' },
  report: { label: 'Rapport', className: 'bg-orange-100 text-orange-800 border-orange-200' },
};

// ─── Component ────────────────────────────────────────────────────────────────

export default function RAGDocuments() {
  const { user } = useAuth();
  const { toast } = useToast();
  const isAdmin = user?.role?.toUpperCase() === 'ADMIN';

  // List state
  const [documents, setDocuments] = useState<RagDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [docTypeFilter, setDocTypeFilter] = useState('ALL');

  // Upload modal state
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadDocType, setUploadDocType] = useState<'manual' | 'sop' | 'report'>('manual');
  const [uploadMachineId, setUploadMachineId] = useState('');
  const [uploadDescription, setUploadDescription] = useState('');

  useEffect(() => {
    fetchDocuments();
  }, [docTypeFilter]);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (docTypeFilter !== 'ALL') params.set('doc_type', docTypeFilter);
      const res = await fetch(`${BASE()}/documents?${params.toString()}`, {
        headers: getAuthHeaders(),
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Erreur chargement');
      setDocuments(await res.json());
    } catch (e: any) {
      toast({ title: 'Erreur', description: e.message, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

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
        headers: getAuthHeaders(), // no Content-Type — browser sets multipart boundary
        credentials: 'include',
        body: fd,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Erreur ${res.status}`);
      }

      toast({ title: 'Document importé', description: `${uploadFile.name} ingéré avec succès.` });
      setShowUploadModal(false);
      setUploadFile(null);
      setUploadMachineId('');
      setUploadDescription('');
      setUploadDocType('manual');
      fetchDocuments();
    } catch (e: any) {
      toast({ title: 'Échec import', description: e.message, variant: 'destructive' });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (doc: RagDocument) => {
    if (!window.confirm(`Supprimer "${doc.filename}" et tous ses chunks vectoriels ?`)) return;
    try {
      const res = await fetch(`${BASE()}/documents/${doc.id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
        credentials: 'include',
      });
      if (!res.ok && res.status !== 204) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Erreur ${res.status}`);
      }
      toast({ title: 'Document supprimé', description: doc.filename });
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (e: any) {
      toast({ title: 'Erreur suppression', description: e.message, variant: 'destructive' });
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
            <h1 className="text-2xl font-bold">Base Documentaire RAG</h1>
            <p className="text-sm text-muted-foreground">
              Manuels, SOPs et rapports injectés dans l'IA
            </p>
          </div>
        </div>
        <Button onClick={() => setShowUploadModal(true)} className="gap-2">
          <Upload className="h-4 w-4" />
          Importer un document
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Rechercher par nom de fichier..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={docTypeFilter} onValueChange={setDocTypeFilter}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Type de document" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">Tous les types</SelectItem>
            <SelectItem value="manual">Manuel</SelectItem>
            <SelectItem value="sop">SOP</SelectItem>
            <SelectItem value="report">Rapport</SelectItem>
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
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground gap-3">
              <Database className="h-12 w-12 opacity-20" />
              <p className="text-sm">
                {searchTerm || docTypeFilter !== 'ALL'
                  ? 'Aucun document correspondant.'
                  : 'Aucun document. Importez votre premier fichier.'}
              </p>
              {!searchTerm && docTypeFilter === 'ALL' && (
                <Button variant="outline" onClick={() => setShowUploadModal(true)} className="gap-2 mt-1">
                  <Upload className="h-4 w-4" />
                  Importer
                </Button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground text-xs uppercase tracking-wider">
                    <th className="text-left py-2 px-3 font-medium">Fichier</th>
                    <th className="text-left py-2 px-3 font-medium">Type</th>
                    <th className="text-left py-2 px-3 font-medium">Chunks</th>
                    <th className="text-left py-2 px-3 font-medium">Taille</th>
                    <th className="text-left py-2 px-3 font-medium">Machine</th>
                    {isAdmin && (
                      <>
                        <th className="text-left py-2 px-3 font-medium">Importé par</th>
                        <th className="text-left py-2 px-3 font-medium">Date</th>
                      </>
                    )}
                    <th className="py-2 px-3" />
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
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-destructive hover:text-destructive hover:bg-destructive/10 h-8 w-8 p-0"
                            onClick={() => handleDelete(doc)}
                            title="Supprimer"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upload Modal */}
      <Dialog open={showUploadModal} onOpenChange={setShowUploadModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5 text-blue-500" />
              Importer un document
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* File picker */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Fichier <span className="text-destructive">*</span></label>
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
                        Cliquer pour sélectionner un fichier PDF ou TXT
                      </div>
                    )}
                  </div>
                  <input
                    type="file"
                    accept=".pdf,.txt"
                    className="sr-only"
                    onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                  />
                </label>
              </div>
            </div>

            {/* Doc type */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Type de document <span className="text-destructive">*</span></label>
              <Select value={uploadDocType} onValueChange={(v: any) => setUploadDocType(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="manual">Manuel technique</SelectItem>
                  <SelectItem value="sop">SOP — Procédure opérationnelle</SelectItem>
                  <SelectItem value="report">Rapport d'intervention</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Machine ID */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium">
                ID Machine <span className="text-muted-foreground text-xs">(optionnel)</span>
              </label>
              <Input
                type="number"
                placeholder="ex: 42"
                value={uploadMachineId}
                onChange={(e) => setUploadMachineId(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Lier ce document à une machine pour filtrage ciblé lors de la récupération.
              </p>
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium">
                Description <span className="text-muted-foreground text-xs">(optionnelle)</span>
              </label>
              <Textarea
                placeholder="ex: Manuel de maintenance du compresseur Atlas Copco GA18"
                value={uploadDescription}
                onChange={(e) => setUploadDescription(e.target.value)}
                rows={2}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUploadModal(false)} disabled={uploading}>
              Annuler
            </Button>
            <Button onClick={handleUpload} disabled={!uploadFile || uploading} className="gap-2">
              {uploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Ingestion en cours...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  Importer
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
