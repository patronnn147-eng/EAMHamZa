import React, { useState, useRef } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Upload, FileDown, CheckCircle2, XCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useDataSync } from '@/contexts/DataSyncContext';

interface MachineImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

interface PreviewItem {
  row_index: number;
  data: any;
  valid: boolean;
  errors: string[];
}

const PREVIEW_PAGE_SIZE = 100;

export const MachineImportDialog: React.FC<MachineImportDialogProps> = ({
  open,
  onOpenChange,
  onSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [previewItems, setPreviewItems] = useState<PreviewItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ total: 0, valid: 0, invalid: 0 });
  const [previewPage, setPreviewPage] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();
  const { notifyChange } = useDataSync();

  const resetState = () => {
    setFile(null);
    setPreviewItems([]);
    setStats({ total: 0, valid: 0, invalid: 0 });
    setPreviewPage(0);
    setLoading(false);
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) resetState();
    onOpenChange(newOpen);
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    await previewFile(selectedFile);
  };

  const previewFile = async (uploadedFile: File) => {
    setLoading(true);
    setPreviewItems([]);
    setPreviewPage(0);
    try {
      const token = localStorage.getItem('access_token');
      const formData = new FormData();
      formData.append('file', uploadedFile);

      const response = await fetch('/api/v1/entities/machines/import/preview', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData,
      });

      if (!response.ok) {
        let msg = 'Erreur lors de la validation du fichier';
        try {
          const errData = await response.json();
          msg = errData.detail || msg;
        } catch {
          // ignore JSON parse error, use fallback message
        }
        throw new Error(msg);
      }

      const data = await response.json();
      setPreviewItems(data.items);
      setStats(data.stats);

    } catch (error: any) {
      toast({
        title: 'Erreur',
        description: error.message || 'Impossible de lire le fichier',
        variant: 'destructive',
      });
      setFile(null);
    } finally {
      setLoading(false);
      // reset file input
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleConfirmImport = async () => {
    const validItems = previewItems.filter(item => item.valid).map(item => item.data);
    
    if (validItems.length === 0) {
      toast({
        title: 'Attention',
        description: 'Aucune machine valide à importer.',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const payload = { items: validItems };

      const response = await fetch('/api/v1/entities/machines/batch', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error("L'import a échoué");
      }

      toast({
        title: 'Succès',
        description: `${validItems.length} machine(s) importée(s) avec succès.`,
      });
      
      notifyChange({ type: 'machine', action: 'create', id: 0 }); // broad channel update
      if (onSuccess) onSuccess();
      handleOpenChange(false);
    } catch (error: any) {
      toast({
        title: 'Erreur',
        description: error.message || "Erreur lors de l'import",
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const downloadTemplate = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/entities/machines/import/template', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) throw new Error('Failed to download template');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'machines_import_template.xlsx';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      toast({
        title: 'Erreur',
        description: 'Impossible de télécharger le modèle',
        variant: 'destructive',
      });
    }
  };

  let importButtonLabel: string;
  if (loading) {
    importButtonLabel = 'Vérification...';
  } else if (file) {
    importButtonLabel = `Nouveau fichier (${file.name})`;
  } else {
    importButtonLabel = 'Sélectionner un fichier CSV/Excel';
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Import en masse des machines</DialogTitle>
          <DialogDescription>
            Importez une liste de machines à partir d'un fichier CSV ou Excel.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 flex-1 overflow-hidden">
          <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-dashed rounded-md">
            <div className="flex-1">
              <p className="text-sm font-medium text-white">Format Requis (Standardisation)</p>
              <p className="text-sm text-blue-300 max-w-md mt-1">
                Utilisez impérativement le modèle fourni (voir feuille &quot;Guide des Règles&quot;). 
                Les colonnes <strong className="text-blue-100">zone, sous_zone et ordre</strong> sont obligatoires et doivent correspondre aux valeurs exactes. 
                Le <strong className="text-blue-100">nom</strong> est généré automatiquement s'il est laissé vide.
              </p>
            </div>
            <Button variant="outline" onClick={downloadTemplate} className="shrink-0 flex gap-2">
              <FileDown size={16} />
              Télécharger Modèle
            </Button>
          </div>

          <div className="flex items-center gap-4">
            <input 
              type="file" 
              accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel" 
              className="hidden" 
              ref={fileInputRef}
              onChange={handleFileChange}
            />
            <Button 
              onClick={() => fileInputRef.current?.click()} 
              disabled={loading}
              className="w-full h-24 flex flex-col gap-2 items-center justify-center border-2 border-dashed border-blue-600/50 bg-slate-800/50 text-blue-200 hover:bg-blue-800/40 hover:border-gray-400"
              variant="outline"
            >
              <Upload size={24} />
              {importButtonLabel}
            </Button>
          </div>

          {previewItems.length > 0 && (() => {
            const totalPages = Math.ceil(previewItems.length / PREVIEW_PAGE_SIZE);
            const pageItems = previewItems.slice(
              previewPage * PREVIEW_PAGE_SIZE,
              (previewPage + 1) * PREVIEW_PAGE_SIZE
            );
            return (
            <div className="flex-1 overflow-hidden flex flex-col gap-2 min-h-64">
              <div className="flex items-center justify-between text-sm py-2 px-1 border-b">
                <div className="font-semibold text-blue-100">Aperçu ({stats.total} lignes)</div>
                <div className="flex gap-4">
                  <span className="flex items-center gap-1 text-green-600"><CheckCircle2 size={16}/> {stats.valid} valides</span>
                  <span className="flex items-center gap-1 text-red-600"><XCircle size={16}/> {stats.invalid} erreurs</span>
                </div>
              </div>
              <div className="overflow-auto flex-1 border rounded min-h-[250px] shadow-inner bg-slate-800/50 p-2">
                <table className="w-full text-sm text-left">
                  <thead className="bg-slate-800 sticky top-0 shadow-sm z-10">
                    <tr>
                      <th className="px-3 py-2">Statut</th>
                      <th className="px-3 py-2">Nom</th>
                      <th className="px-3 py-2">Type</th>
                      <th className="px-3 py-2">Zone</th>
                      <th className="px-3 py-2">Erreurs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pageItems.map((item) => (
                      <tr key={item.row_index} className={`border-b border-blue-800/50 ${item.valid ? 'bg-slate-800' : 'bg-red-50'}`}>
                        <td className="px-3 py-2">
                          {item.valid ? (
                            <CheckCircle2 size={16} className="text-green-500" />
                          ) : (
                            <XCircle size={16} className="text-red-500" />
                          )}
                        </td>
                        <td className="px-3 py-2 font-medium">{item.data?.nom || '-'}</td>
                        <td className="px-3 py-2 text-blue-200">{item.data?.type || '-'}</td>
                        <td className="px-3 py-2 text-blue-200">{item.data?.zone || '-'}</td>
                        <td className="px-3 py-2 text-red-600 font-medium text-xs flex flex-col gap-1">
                          {item.errors.map((err, j) => <span key={j}>• {err}</span>)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {totalPages > 1 && (
                <div className="flex items-center justify-between text-sm px-1">
                  <span className="text-blue-200">
                    Page {previewPage + 1} / {totalPages}
                  </span>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPreviewPage((p) => Math.max(0, p - 1))}
                      disabled={previewPage === 0}
                    >
                      <ChevronLeft size={16} />
                      Précédent
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPreviewPage((p) => Math.min(totalPages - 1, p + 1))}
                      disabled={previewPage >= totalPages - 1}
                    >
                      Suivant
                      <ChevronRight size={16} />
                    </Button>
                  </div>
                </div>
              )}
            </div>
            );
          })()}
        </div>

        <DialogFooter className="mt-4 pt-4 border-t">
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={loading}>
            Annuler
          </Button>
          <Button 
            onClick={handleConfirmImport} 
            disabled={stats.valid === 0 || loading}
          >
            Importer {stats.valid > 0 ? `(${stats.valid})` : ''}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
