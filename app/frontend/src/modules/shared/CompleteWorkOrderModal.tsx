import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Upload, X, CheckSquare, Info, AlertTriangle, Settings, RefreshCw, Activity } from 'lucide-react';
import { client } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { useAuth } from '@/contexts/AuthContext';
import { MachineMetricsForm, TelemetryFormData } from '@/components/technicien/MachineMetricsForm';

interface CompleteWorkOrderModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workOrderId: number;
  onSuccess: () => void;
}

export function CompleteWorkOrderModal({ open, onOpenChange, workOrderId, onSuccess }: CompleteWorkOrderModalProps) {
  const { user } = useAuth();
  const [formData, setFormData] = useState({
    rapport: '',
    intervention_type: 'CURATIVE',
    root_cause_category: 'MECANIQUE',
    root_cause_description: '',
    actions_performed: '',
    parts_replaced: '',
    tools_used: '',
    machine_status_after: 'EN_MARCHE',
    plan_hypothesis: '',
    check_resolved: true,
    check_verification_method: '',
    act_preventive_actions: '',
    act_recommendations: '',
  });
  const [attachments, setAttachments] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();
  const apiBase = import.meta.env.VITE_API_BASE_URL || '';
  
  // Machine telemetry data
  const [telemetryData, setTelemetryData] = useState<TelemetryFormData>({});

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setAttachments((prev) => [...prev, ...Array.from(e.target.files!)]);
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!formData.rapport.trim()) {
      toast({
        title: 'Erreur',
        description: 'Veuillez saisir un rapport d\'intervention.',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      if (!token) throw new Error('Non authentifié');

      // Check localStorage first for user role (more reliable)
      const storedUser = localStorage.getItem('user');
      const userData = storedUser ? JSON.parse(storedUser) : null;
      const userRole = userData?.role || user?.role || '';
      
      // Use correct endpoint based on user role - check both uppercase and lowercase
      let endpoint = 'chetop';
      if (userRole.toUpperCase() === 'TECHNICIEN' || userRole.toLowerCase() === 'technicien') {
        endpoint = 'technicien';
      }

      // 1. Complete work order
      const res = await fetch(`${apiBase}/api/v1/${endpoint}/work-orders/${workOrderId}/complete`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          // Include telemetry data
          air_temperature: telemetryData.air_temperature,
          process_temperature: telemetryData.process_temperature,
          rotational_speed: telemetryData.rotational_speed,
          torque: telemetryData.torque,
          tool_wear: telemetryData.tool_wear,
          telemetry_notes: telemetryData.notes,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Erreur lors de la clôture');
      }

      // 2. Upload attachments
      for (const file of attachments) {
        const objectKey = `${workOrderId}/completion_${Date.now()}_${file.name}`;
        
        try {
          const uploadUrlResp = await client.apiCall.invoke({
            url: '/api/v1/storage/upload-url',
            method: 'POST',
            data: {
              bucket_name: 'attachments',
              object_key: objectKey,
            },
          });

          const uploadUrl = (uploadUrlResp as { data?: { upload_url?: string } }).data?.upload_url;
          if (uploadUrl) {
            const putRes = await fetch(uploadUrl, {
              method: 'PUT',
              body: file,
            });
            
            if (putRes.ok) {
              await client.entities.archives.create({
                data: {
                  identifiant_archive: `ARCH-C-${Date.now()}`,
                  nom: file.name,
                  date_archivage: new Date().toISOString(),
                  type: file.type.startsWith('video/') ? 'VIDEO' : 'DOCUMENT',
                  object_key: objectKey,
                  ordre_travail_id: workOrderId,
                  created_at: new Date().toISOString(),
                },
              });
            }
          }
        } catch (uploadErr) {
          console.error('File upload failed', uploadErr);
        }
      }

      toast({
        title: 'Succès',
        description: 'L\'ordre de travail a été clôturé avec succès.',
      });
      onSuccess();
      onOpenChange(false);
      setFormData({
        rapport: '',
        intervention_type: 'CURATIVE',
        root_cause_category: 'MECANIQUE',
        root_cause_description: '',
        actions_performed: '',
        parts_replaced: '',
        tools_used: '',
        machine_status_after: 'EN_MARCHE',
        plan_hypothesis: '',
        check_resolved: true,
        check_verification_method: '',
        act_preventive_actions: '',
        act_recommendations: '',
      });
      setAttachments([]);
      setTelemetryData({});
    } catch (error: unknown) {
      toast({
        title: 'Erreur',
        description: error instanceof Error ? error.message : 'Erreur inconnue',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckSquare className="h-5 w-5 text-emerald-600" />
            Clôture de l'Intervention & Rapport PDCA
          </DialogTitle>
          <DialogDescription>
            Remplissez les informations techniques et les étapes du cycle PDCA pour validation.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="pr-4 max-h-[70vh]">
          <div className="space-y-8 pt-4">
            {/* --- Section: Général & Type --- */}
            <div className="space-y-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                <Info className="h-4 w-4" /> Détails de l'Intervention
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="itv_type">Type d'intervention</Label>
                  <Select 
                    value={formData.intervention_type} 
                    onValueChange={(val) => setFormData({...formData, intervention_type: val})}
                  >
                    <SelectTrigger id="itv_type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="CURATIVE">Curative (Dépannage)</SelectItem>
                      <SelectItem value="PREVENTIVE">Préventive (Systématique)</SelectItem>
                      <SelectItem value="PREDICTIVE">Prédictive (Basée état)</SelectItem>
                      <SelectItem value="AMELIORATIVE">Améliorative (Modif)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="m_status">État machine final</Label>
                  <Select 
                    value={formData.machine_status_after} 
                    onValueChange={(val) => setFormData({...formData, machine_status_after: val})}
                  >
                    <SelectTrigger id="m_status">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="EN_MARCHE">En marche (Fonctionnel)</SelectItem>
                      <SelectItem value="ARRETEE">Arrêtée (En attente/HS)</SelectItem>
                      <SelectItem value="FONCTIONNEMENT_RESTREINT">Fonctionnement restreint</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>

            <Separator />

            {/* --- Section: PLAN (Hypothèse) --- */}
            <div className="space-y-4 bg-blue-50/30 p-4 rounded-lg border border-blue-100 italic">
              <h3 className="text-sm font-bold uppercase tracking-wider text-blue-700 flex items-center gap-2">
                <RefreshCw className="h-4 w-4" /> 1. PLAN - Hypothèse de départ
              </h3>
              <div className="space-y-2">
                <Label htmlFor="plan">Quel était le problème supposé ?</Label>
                <Textarea
                  id="plan"
                  placeholder="ex: Je pensais que le capteur était défectueux..."
                  className="min-h-[60px]"
                  value={formData.plan_hypothesis}
                  onChange={(e) => setFormData({...formData, plan_hypothesis: e.target.value})}
                />
              </div>
            </div>

            {/* --- Section: DO (Actions) --- */}
            <div className="space-y-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-emerald-700 flex items-center gap-2">
                <Settings className="h-4 w-4" /> 2. DO - Actions Réalisées
              </h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="rc_cat">Catégorie Cause Racine</Label>
                  <Select 
                    value={formData.root_cause_category} 
                    onValueChange={(val) => setFormData({...formData, root_cause_category: val})}
                  >
                    <SelectTrigger id="rc_cat">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="MECANIQUE">Mécanique</SelectItem>
                      <SelectItem value="ELECTRIQUE">Électrique</SelectItem>
                      <SelectItem value="AUTOMATISME">Automatisme / Soft</SelectItem>
                      <SelectItem value="HUMAIN">Erreur Humaine</SelectItem>
                      <SelectItem value="AUTRE">Autre</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="rc_desc">Description de la Cause Racine</Label>
                <Textarea
                  id="rc_desc"
                  placeholder="Pourquoi la panne est arrivée ?"
                  className="min-h-[80px]"
                  value={formData.root_cause_description}
                  onChange={(e) => setFormData({...formData, root_cause_description: e.target.value})}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="rapport" className="font-semibold text-blue-100">Rapport d'intervention détaillé (Obligatoire)</Label>
                <Textarea
                  id="rapport"
                  placeholder="Décrivez les actions réalisées étape par étape..."
                  className="min-h-[120px]"
                  value={formData.rapport}
                  onChange={(e) => setFormData({...formData, rapport: e.target.value})}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="parts">Pièces remplacées</Label>
                  <Textarea
                    id="parts"
                    placeholder="ex: Roulement 6204, Courroie..."
                    className="min-h-[60px]"
                    value={formData.parts_replaced}
                    onChange={(e) => setFormData({...formData, parts_replaced: e.target.value})}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tools">Outils utilisés</Label>
                  <Textarea
                    id="tools"
                    placeholder="ex: Clé dynamométrique, Multimètre..."
                    className="min-h-[60px]"
                    value={formData.tools_used}
                    onChange={(e) => setFormData({...formData, tools_used: e.target.value})}
                  />
                </div>
              </div>
            </div>

            {/* --- Section: CHECK (Vérification) --- */}
            <div className="space-y-4 bg-orange-50/30 p-4 rounded-lg border border-orange-100">
              <h3 className="text-sm font-bold uppercase tracking-wider text-orange-700 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" /> 3. CHECK - Vérification
              </h3>
              <div className="flex items-center space-x-2">
                <Checkbox 
                  id="resolved" 
                  checked={formData.check_resolved}
                  onCheckedChange={(checked) => setFormData({...formData, check_resolved: !!checked})}
                />
                <label htmlFor="resolved" className="text-sm font-medium leading-none cursor-pointer">
                  Le problème est-il définitivement résolu ?
                </label>
              </div>
              <div className="space-y-2">
                <Label htmlFor="check_method">Méthode de vérification</Label>
                <Textarea
                  id="check_method"
                  placeholder="ex: Test de fonctionnement sur 10 cycles, mesures OK..."
                  className="min-h-[60px]"
                  value={formData.check_verification_method}
                  onChange={(e) => setFormData({...formData, check_verification_method: e.target.value})}
                />
              </div>
            </div>

            <Separator />

            {/* --- Section: ACT (Prévention) --- */}
            <div className="space-y-4 bg-purple-50/30 p-4 rounded-lg border border-purple-100">
              <h3 className="text-sm font-bold uppercase tracking-wider text-purple-700 flex items-center gap-2">
                <Activity className="h-4 w-4" /> 4. ACT - Amélioration Continue
              </h3>
              <div className="space-y-2">
                <Label htmlFor="preventive">Actions préventives suggérées</Label>
                <Textarea
                  id="preventive"
                  placeholder="Que faire pour que ça ne recommence plus ?"
                  className="min-h-[60px]"
                  value={formData.act_preventive_actions}
                  onChange={(e) => setFormData({...formData, act_preventive_actions: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="reco">Recommandations</Label>
                <Textarea
                  id="reco"
                  placeholder="ex: Prévoir une révision complète du moteur..."
                  className="min-h-[60px]"
                  value={formData.act_recommendations}
                  onChange={(e) => setFormData({...formData, act_recommendations: e.target.value})}
                />
              </div>
            </div>

            {/* --- Section: Machine Telemetry --- */}
            <MachineMetricsForm formData={telemetryData} onChange={setTelemetryData} />

            <Separator />

            {/* --- Section: Pièces Jointes --- */}
            <div className="grid gap-2 pb-4">
              <Label className="font-semibold text-blue-100">Pièces jointes (Preuves visuelles)</Label>
              <div className="flex items-center gap-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => document.getElementById('file-upload')?.click()}
                  className="w-full h-24 border-dashed bg-slate-800/50 hover:bg-blue-800/40 flex flex-col items-center justify-center gap-2"
                >
                  <Upload className="h-6 w-6 text-blue-400" />
                  <span className="text-sm text-blue-300">Ajouter des photos / vidéos</span>
                </Button>
                <Input
                  id="file-upload"
                  type="file"
                  multiple
                  accept="image/*,video/*"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </div>

              {attachments.length > 0 && (
                <div className="mt-4 space-y-2 max-h-40 overflow-auto pr-2">
                  {attachments.map((file, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 text-sm border rounded bg-slate-800 shadow-sm">
                      <span className="truncate flex-1 max-w-[250px]">{file.name}</span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeAttachment(idx)}
                        className="text-red-500 hover:text-red-700"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </ScrollArea>

        <DialogFooter className="mt-6 border-t pt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Annuler
          </Button>
          <Button onClick={handleSubmit} disabled={loading} className="bg-emerald-600 hover:bg-emerald-700">
            {loading ? 'Enregistrement...' : 'Valider et Clôturer'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
