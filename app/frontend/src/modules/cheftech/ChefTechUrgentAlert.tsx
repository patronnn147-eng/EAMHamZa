import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { AlertTriangle, ArrowLeft, Send } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

export default function ChefTechUrgentAlert() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    categorie: '',
    description: '',
    machine_id: '',
  });

  const handleSubmit = async () => {
    try {
      if (!formData.categorie || !formData.description.trim()) {
        toast({
          title: 'Erreur de Validation',
          description: 'Veuillez remplir tous les champs requis',
          variant: 'destructive',
        });
        return;
      }

      setLoading(true);

      const user = await client.auth.me();
      if (!user.data) {
        throw new Error('User not authenticated');
      }

      const submitData = {
        utilisateur_id: Number.parseInt(user.data.id),
        categorie: formData.categorie,
        description: formData.description,
        machine_id: formData.machine_id ? Number.parseInt(formData.machine_id) : null,
        statut: 'EN_ATTENTE',
      };

      await client.entities.alertes_urgentes.create({
        data: submitData,
      });

      toast({
        title: 'Alerte Envoyée',
        description: 'Votre alerte urgente a été transmise aux responsables',
      });

      navigate('/cheftech/dashboard');
    } catch (error: unknown) {
      const detail =
        (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data
          ?.detail ||
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (error as { message?: string }).message;
      toast({
        title: 'Erreur',
        description: detail || 'Échec de l\'envoi de l\'alerte',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => navigate('/cheftech/dashboard')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Retour
        </Button>
        <div className="flex-1">
          <h2 className="text-3xl font-bold text-red-600 flex items-center gap-2">
            <AlertTriangle className="h-8 w-8" />
            Alerte Urgente
          </h2>
          <p className="mt-1 text-sm text-blue-300">Signalez un problème critique nécessitant une intervention immédiate</p>
        </div>
      </div>

      <Card className="border-red-200 bg-red-50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3 text-red-800">
            <AlertTriangle className="h-5 w-5 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-semibold">Attention</p>
              <p className="text-sm mt-1">
                Cette fonction est réservée aux situations critiques nécessitant une intervention immédiate
                (sécurité, panne majeure, problème de qualité). Une notification sera envoyée instantanément
                aux responsables.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Détails de l'Alerte</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="categorie">Catégorie *</Label>
            <Select value={formData.categorie} onValueChange={(value) => setFormData({ ...formData, categorie: value })}>
              <SelectTrigger>
                <SelectValue placeholder="Sélectionner une catégorie" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="SECURITE">🚨 Sécurité</SelectItem>
                <SelectItem value="PANNE_CRITIQUE">⚠️ Panne Critique</SelectItem>
                <SelectItem value="QUALITE">📋 Problème de Qualité</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="description">Description du Problème *</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Décrivez la situation en détail : nature du problème, localisation, risques potentiels..."
              rows={8}
              className="resize-none"
            />
            <p className="text-xs text-blue-300">{formData.description.length} caractères</p>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="machine_id">Machine Concernée (optionnel)</Label>
            <Input
              id="machine_id"
              type="number"
              value={formData.machine_id}
              onChange={(e) => setFormData({ ...formData, machine_id: e.target.value })}
              placeholder="ID de la machine"
            />
          </div>

          <div className="flex gap-3 pt-4">
            <Button variant="outline" className="flex-1" onClick={() => navigate('/cheftech/dashboard')}>
              Annuler
            </Button>
            <Button
              className="flex-1 bg-red-600 hover:bg-red-700"
              onClick={handleSubmit}
              disabled={loading}
            >
              <Send className="mr-2 h-4 w-4" />
              {loading ? 'Envoi...' : 'Envoyer Alerte Urgente'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}



