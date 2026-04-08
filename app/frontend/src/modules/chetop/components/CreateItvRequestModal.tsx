import React, { useEffect, useState } from 'react';
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
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Paperclip, Loader2, AlertCircle, Zap, Activity, History } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface Machine {
  id: number;
  nom: string;
}

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export const CreateItvRequestModal: React.FC<Props> = ({
  open,
  onOpenChange,
  onSuccess,
}) => {
  const { toast } = useToast();
  const [machines, setMachines] = useState<Machine[]>([]);
  const [loadingMachines, setLoadingMachines] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [uploadingField, setUploadingField] = useState<'description' | 'required_materials' | null>(null);

  const [formData, setFormData] = useState({
    machine_id: '',
    description: '',
    priority: 'MOYENNE',
    estimated_duration_minutes: '',
    required_materials: '',
    // Enhanced Fields
    machine_category: 'Non-critique',
    symptoms: [] as string[],
    problem_start_time: '',
    frequency: 'Première fois',
    operating_state: 'En marche',
    temperature: '',
    impact: 'Aucun impact pour le moment',
    estimated_loss: '',
    similar_issue_before: false,
  });

  const fetchMachines = async () => {
    setLoadingMachines(true);
    try {
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${apiBase}/api/v1/chetop/machines`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setMachines(data);
      }
    } catch (error) {
      console.error('Error fetching machines:', error);
    } finally {
      setLoadingMachines(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchMachines();
      setFormData({
        machine_id: '',
        description: '',
        priority: 'MOYENNE',
        estimated_duration_minutes: '',
        required_materials: '',
        machine_category: 'Non-critique',
        symptoms: [],
        problem_start_time: '',
        frequency: 'Première fois',
        operating_state: 'En marche',
        temperature: '',
        impact: 'Aucun impact pour le moment',
        estimated_loss: '',
        similar_issue_before: false,
      });
    }
  }, [open]);

  const handleFileUpload = async (field: 'description' | 'required_materials') => {
    const input = document.createElement('input');
    input.type = 'file';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      setUploadingField(field);
      try {
        const token = localStorage.getItem('access_token');
        const apiBase = import.meta.env.VITE_API_BASE_URL || '';

        const fileName = `${Date.now()}_${file.name}`;
        const uploadRes = await fetch(`${apiBase}/api/v1/storage/upload-url`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            bucket_name: 'interventions',
            object_key: fileName
          })
        });

        if (!uploadRes.ok) throw new Error('Failed to get upload URL');
        const { upload_url } = await uploadRes.json();

        await fetch(upload_url, {
          method: 'PUT',
          body: file
        });

        const fileMarker = `\n[FILE:${fileName}|${file.name}]`;
        setFormData(prev => ({
          ...prev,
          [field]: prev[field] ? `${prev[field]}${fileMarker}` : fileMarker
        }));

        toast({ title: 'Fichier joint', description: file.name });
      } catch (err) {
        console.error('Upload error:', err);
        toast({ title: 'Erreur upload', variant: 'destructive' });
      } finally {
        setUploadingField(null);
      }
    };
    input.click();
  };

  const handleSubmit = async () => {
    if (!formData.machine_id || !formData.description) {
      toast({ title: 'Erreur', description: 'Veuillez remplir les champs obligatoires (Machine et Description)', variant: 'destructive' });
      return;
    }

    setSubmitting(true);
    try {
      const token = localStorage.getItem('access_token');
      const apiBase = import.meta.env.VITE_API_BASE_URL || '';
      
      const payload = {
        machine_id: parseInt(formData.machine_id),
        description: formData.description,
        priorite: formData.priority,

        // Enhanced Fields
        machine_category: formData.machine_category,
        symptoms: formData.symptoms.join(', '),
        problem_start_time: formData.problem_start_time ? new Date(formData.problem_start_time).toISOString() : null,
        frequency: formData.frequency,
        operating_state: formData.operating_state,
        temperature: formData.temperature,
        impact: formData.impact,
        estimated_loss: formData.estimated_loss,
        similar_issue_before: formData.similar_issue_before,
      };

      const response = await fetch(`${apiBase}/api/v1/chetop/intervention-requests`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (response.ok || response.status === 201) {
        onSuccess();
        onOpenChange(false);
        toast({ title: 'Succès', description: 'Demande créée avec succès' });
      } else {
        try {
          const error = await response.json();
          toast({ title: 'Erreur', description: error.detail || 'Échec de la demande', variant: 'destructive' });
        } catch {
          toast({ title: 'Erreur', description: 'Une erreur est survenue', variant: 'destructive' });
        }
      }
    } catch (error) {
      console.error('Error submitting request:', error);
      toast({ title: 'Erreur', description: 'Une erreur est survenue', variant: 'destructive' });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] bg-white dark:bg-gray-900 border-none shadow-2xl rounded-3xl overflow-hidden">
        <DialogHeader className="px-6 pt-6">
          <DialogTitle className="text-2xl font-black tracking-tight flex items-center gap-2">
             <AlertCircle className="h-6 w-6 text-primary" />
             Nouvelle Demande d'Intervention (DI)
          </DialogTitle>
          <DialogDescription className="text-gray-500 font-medium">
            Standard Officiel - ChefOp
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="px-6 max-h-[70vh]">
           <div className="space-y-6 py-4">
              {/* --- Section 1: Informations de Base --- */}
              <div className="space-y-4">
                <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <Zap className="h-4 w-4" /> Informations de Base
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="font-bold text-sm ml-1">Machine</Label>
                    <Select value={formData.machine_id} onValueChange={(v) => setFormData({...formData, machine_id: v})} disabled={loadingMachines}>
                      <SelectTrigger className="rounded-xl border-gray-200 py-6">
                         <SelectValue placeholder={loadingMachines ? "Chargement..." : "Choisir une machine"} />
                      </SelectTrigger>
                      <SelectContent className="rounded-xl border-gray-200">
                        {machines.map(m => (
                          <SelectItem key={m.id} value={m.id.toString()} className="rounded-lg mb-1">
                             {m.nom}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="font-bold text-sm ml-1">Catégorie Machine</Label>
                    <Select onValueChange={(val) => setFormData({...formData, machine_category: val})} value={formData.machine_category}>
                      <SelectTrigger className="rounded-xl border-gray-200 py-6">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="rounded-xl border-gray-200">
                        <SelectItem value="Critique" className="rounded-lg">Critique</SelectItem>
                        <SelectItem value="Non-critique" className="rounded-lg">Non-critique</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <Separator />

              {/* --- Section 2: Description & Symptômes --- */}
              <div className="space-y-4">
                <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" /> Analyse du Problème
                </h3>
                <div className="space-y-2">
                  <div className="flex items-center justify-between ml-1">
                    <Label className="font-bold text-sm">Description détaillée</Label>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => handleFileUpload('description')}
                      disabled={!!uploadingField}
                      className="text-violet-600 hover:text-violet-700 font-bold gap-1"
                    >
                      {uploadingField === 'description' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Paperclip className="w-4 h-4" />}
                      Joindre
                    </Button>
                  </div>
                  <Textarea 
                    placeholder="Expliquez ce qu'il se passe..." 
                    value={formData.description}
                    onChange={(e) => setFormData({...formData, description: e.target.value})}
                    className="rounded-2xl border-gray-200 min-h-[80px] bg-gray-50/50"
                  />
                </div>

                <div className="space-y-3">
                  <Label className="font-bold text-sm ml-1">Symptômes observés</Label>
                  <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 bg-muted/30 p-4 rounded-2xl border border-gray-100">
                    {['Bruit anormal', 'Vibrations', 'Surchauffe', 'Fuite', 'Panne électrique', 'Baisse de performance'].map((symptom) => (
                      <div key={symptom} className="flex items-center space-x-2">
                        <Checkbox 
                          id={`symptom-${symptom}`} 
                          checked={formData.symptoms.includes(symptom)}
                          onCheckedChange={(checked) => {
                            if (checked) {
                              setFormData({...formData, symptoms: [...formData.symptoms, symptom]});
                            } else {
                              setFormData({...formData, symptoms: formData.symptoms.filter(s => s !== symptom)});
                            }
                          }}
                        />
                        <label htmlFor={`symptom-${symptom}`} className="text-sm font-medium leading-none cursor-pointer">
                          {symptom}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="font-bold text-sm ml-1">Début de l'incident</Label>
                    <Input 
                      type="datetime-local" 
                      value={formData.problem_start_time}
                      onChange={(e) => setFormData({...formData, problem_start_time: e.target.value})}
                      className="rounded-xl border-gray-200 py-6"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="font-bold text-sm ml-1">Fréquence du problème</Label>
                    <Select onValueChange={(val) => setFormData({...formData, frequency: val})} value={formData.frequency}>
                      <SelectTrigger className="rounded-xl border-gray-200 py-6">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="rounded-xl border-gray-200">
                        <SelectItem value="Première fois">Première fois</SelectItem>
                        <SelectItem value="Occasionnel">Occasionnel</SelectItem>
                        <SelectItem value="Récurrent">Récurrent</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <Separator />

              {/* --- Section 3: État Machine --- */}
              <div className="space-y-4">
                <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <Activity className="h-4 w-4" /> État de la Machine
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="font-bold text-sm ml-1">État opérationnel</Label>
                    <Select onValueChange={(val) => setFormData({...formData, operating_state: val})} value={formData.operating_state}>
                      <SelectTrigger className="rounded-xl border-gray-200 py-6">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="rounded-xl border-gray-200">
                        <SelectItem value="En marche">En marche</SelectItem>
                        <SelectItem value="Au repos (Idle)">Au repos (Idle)</SelectItem>
                        <SelectItem value="Démarrage">Démarrage</SelectItem>
                        <SelectItem value="Arrêt">Arrêt</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="font-bold text-sm ml-1">Température (si connue)</Label>
                    <Input 
                      placeholder="ex: 45°C"
                      value={formData.temperature}
                      onChange={(e) => setFormData({...formData, temperature: e.target.value})}
                      className="rounded-xl border-gray-200 py-6"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                   <div className="space-y-2">
                      <Label className="font-bold text-sm ml-1">Durée Estimée (min)</Label>
                      <Input
                        type="number"
                        placeholder="ex: 60"
                        value={formData.estimated_duration_minutes}
                        onChange={(e) => setFormData(prev => ({ ...prev, estimated_duration_minutes: e.target.value }))}
                        className="rounded-xl border-gray-200 py-6"
                      />
                   </div>
                </div>
              </div>

              <Separator />

              {/* --- Section 4: Priorité & Impact --- */}
              <div className="space-y-4">
                <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-orange-500" /> Priorité & Impact Production
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="font-bold text-sm ml-1">Priorité d'intervention</Label>
                    <Select onValueChange={(val) => setFormData({...formData, priority: val})} value={formData.priority}>
                      <SelectTrigger className="rounded-xl border-gray-200 py-6">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="rounded-xl border-gray-200">
                        <SelectItem value="BASSE">BASSE</SelectItem>
                        <SelectItem value="MOYENNE">MOYENNE</SelectItem>
                        <SelectItem value="ÉLEVÉE">ÉLEVÉE</SelectItem>
                        <SelectItem value="URGENTE" className="text-red-600 font-bold">URGENTE</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label className="font-bold text-sm ml-1">Impact sur la production</Label>
                    <Select onValueChange={(val) => setFormData({...formData, impact: val})} value={formData.impact}>
                      <SelectTrigger className="rounded-xl border-gray-200 py-6">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="rounded-xl border-gray-200">
                        <SelectItem value="Arrêt de production">Arrêt de production</SelectItem>
                        <SelectItem value="Performance réduite">Performance réduite</SelectItem>
                        <SelectItem value="Aucun impact pour le moment">Aucun impact pour le moment</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <Separator />

              {/* --- Section 5: Historique --- */}
              <div className="space-y-4">
                <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <History className="h-4 w-4" /> Historique
                </h3>
                <div className="flex items-center space-x-2 bg-blue-50/50 p-4 rounded-2xl border border-blue-100">
                  <Checkbox 
                    id="similar" 
                    checked={formData.similar_issue_before}
                    onCheckedChange={(checked) => setFormData({...formData, similar_issue_before: !!checked})}
                  />
                  <label htmlFor="similar" className="text-sm font-bold leading-none cursor-pointer text-blue-700">
                    Problème déjà rencontré auparavant ?
                  </label>
                </div>
              </div>

              <div className="p-4 bg-emerald-50 border border-emerald-100 rounded-2xl space-y-2 shadow-inner">
                <div className="flex items-center gap-2 text-emerald-700 font-bold text-sm">
                  <Zap className="h-4 w-4" /> IA - Aide au diagnostic automatique
                </div>
                <p className="text-xs text-emerald-600 italic">
                  L'IA analysera vos symptômes après la soumission pour suggérer une cause racine à l'équipe maintenance.
                </p>
              </div>
           </div>
        </ScrollArea>

        <DialogFooter className="px-6 py-4 bg-gray-50/80 mt-auto border-t">
          <Button variant="ghost" onClick={() => onOpenChange(false)} className="rounded-xl font-bold px-6">
            Annuler
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={submitting || !formData.machine_id || !formData.description}
            className="bg-gradient-premium hover:opacity-90 rounded-xl font-bold px-8 shadow-lg shadow-violet-500/25 min-w-[160px]"
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
            Envoyer la Demande
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
