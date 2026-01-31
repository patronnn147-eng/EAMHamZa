import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import type { CreateWorkOrderFormData, Machine } from '../types';

interface CreateOrderModalProps {
  open: boolean;
  onClose: () => void;
  formData: CreateWorkOrderFormData;
  setFormData: (data: CreateWorkOrderFormData) => void;
  machines: Machine[];
  onSubmit: (e: React.FormEvent) => void;
}

export const CreateOrderModal: React.FC<CreateOrderModalProps> = ({
  open,
  onClose,
  formData,
  setFormData,
  machines,
  onSubmit,
}) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <CardHeader>
          <CardTitle>Nouvel Ordre de Travail</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <Label htmlFor="titre">Titre *</Label>
              <Input
                id="titre"
                value={formData.titre}
                onChange={(e) => setFormData({ ...formData, titre: e.target.value })}
                placeholder="Titre de l'ordre de travail"
                required
              />
            </div>

            <div>
              <Label htmlFor="description">Description *</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Description détaillée du travail à effectuer"
                rows={4}
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="priorite">Priorité</Label>
                <Select
                  value={formData.priorite}
                  onValueChange={(value) => setFormData({ ...formData, priorite: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="BASSE">Basse</SelectItem>
                    <SelectItem value="MOYENNE">Moyenne</SelectItem>
                    <SelectItem value="ÉLEVÉE">Élevée</SelectItem>
                    <SelectItem value="URGENTE">Urgente</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="machine">Machine *</Label>
                <Select
                  value={formData.machine_id.toString()}
                  onValueChange={(value) => setFormData({ ...formData, machine_id: parseInt(value) })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner une machine" />
                  </SelectTrigger>
                  <SelectContent>
                    {machines.map((machine) => (
                      <SelectItem key={machine.id} value={machine.id.toString()}>
                        {machine.nom}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="outline" onClick={onClose}>
                Annuler
              </Button>
              <Button type="submit">Créer l'Ordre</Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};
