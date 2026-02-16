import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import type { CreateWorkOrderFormData, Machine, Planning } from '../types';

interface CreateOrderModalProps {
  open: boolean;
  onClose: () => void;
  formData: CreateWorkOrderFormData;
  setFormData: (data: CreateWorkOrderFormData) => void;
  machines: Machine[];
  plannings: Planning[];
  attachments: File[];
  setAttachments: (files: File[]) => void;
  onSubmit: (e: React.FormEvent) => void;
}

export const CreateOrderModal: React.FC<CreateOrderModalProps> = ({
  open,
  onClose,
  formData,
  setFormData,
  machines,
  plannings,
  attachments,
  setAttachments,
  onSubmit,
}) => {
  if (!open) return null;

  const selectedPlanning = formData.planning_id
    ? plannings.find((p) => p.id === formData.planning_id)
    : null;

  const planningTechnicians = selectedPlanning
    ? selectedPlanning.assigned_users.filter((u) => u.role === 'TECHNICIEN')
    : [];

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
                <Label>Machines *</Label>
                <div className="border rounded-md p-3 max-h-48 overflow-y-auto space-y-2 bg-gray-50">
                  {machines.length === 0 ? (
                    <p className="text-sm text-gray-500">Aucune machine disponible</p>
                  ) : (
                    machines.map((m) => (
                      <div key={m.id} className="flex items-center space-x-2 p-2 hover:bg-white rounded">
                        <Checkbox
                          id={`machine-${m.id}`}
                          checked={formData.machine_ids.includes(m.id)}
                          onCheckedChange={() =>
                            setFormData({
                              ...formData,
                              machine_ids: formData.machine_ids.includes(m.id)
                                ? formData.machine_ids.filter((id) => id !== m.id)
                                : [...formData.machine_ids, m.id],
                            })
                          }
                        />
                        <label htmlFor={`machine-${m.id}`} className="text-sm font-medium cursor-pointer flex-1">
                          {m.nom} {m.identifiant_machine ? `(${m.identifiant_machine})` : ''}
                        </label>
                      </div>
                    ))
                  )}
                </div>
                <p className="text-xs text-gray-500">Selected: {formData.machine_ids.length} machine(s)</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label>Due Date</Label>
                <Input
                  type="date"
                  value={formData.date_echeance}
                  onChange={(e) => setFormData({ ...formData, date_echeance: e.target.value })}
                />
              </div>
              <div className="grid gap-2">
                <Label>Status</Label>
                <Select
                  value={formData.statut}
                  onValueChange={(value) => setFormData({ ...formData, statut: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EN_ATTENTE">EN_ATTENTE</SelectItem>
                    <SelectItem value="ASSIGNÉ">ASSIGNÉ</SelectItem>
                    <SelectItem value="EN_COURS">EN_COURS</SelectItem>
                    <SelectItem value="TERMINÉ">TERMINÉ</SelectItem>
                    <SelectItem value="BLOQUÉ">BLOQUÉ</SelectItem>
                    <SelectItem value="ANNULÉ">ANNULÉ</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid gap-2">
              <Label>Planning</Label>
              <Select
                value={formData.planning_id?.toString() || ''}
                onValueChange={(value) => {
                  const pid = value ? parseInt(value) : null;
                  const p = pid ? plannings.find((x) => x.id === pid) : null;
                  const chefTechFromPlanning = (p?.assigned_users || []).find((u) => u.role === 'CHEFTECH')?.id || null;
                  setFormData({
                    ...formData,
                    planning_id: pid,
                    chef_technique_id: chefTechFromPlanning,
                    technicien_ids: [],
                  });
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionner un planning" />
                </SelectTrigger>
                <SelectContent>
                  {plannings.map((p) => (
                    <SelectItem key={p.id} value={p.id.toString()}>
                      {p.identifiant_planning}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {selectedPlanning && (
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label>ChefTech (superviseur)</Label>
                  <Input value={formData.chef_technique_id?.toString() || ''} disabled />
                </div>
                <div className="grid gap-2">
                  <Label>Techniciens (du planning)</Label>
                  <div className="border rounded-md p-3 max-h-48 overflow-y-auto space-y-2 bg-gray-50">
                    {planningTechnicians.length === 0 ? (
                      <p className="text-sm text-gray-500">Aucun technicien dans ce planning</p>
                    ) : (
                      planningTechnicians.map((t) => (
                        <div key={t.id} className="flex items-center space-x-2 p-2 hover:bg-white rounded">
                          <Checkbox
                            id={`tech-${t.id}`}
                            checked={formData.technicien_ids.includes(t.id)}
                            onCheckedChange={() =>
                              setFormData({
                                ...formData,
                                technicien_ids: formData.technicien_ids.includes(t.id)
                                  ? formData.technicien_ids.filter((id) => id !== t.id)
                                  : [...formData.technicien_ids, t.id],
                              })
                            }
                          />
                          <label htmlFor={`tech-${t.id}`} className="text-sm font-medium cursor-pointer flex-1">
                            {t.nom} - {t.email}
                          </label>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            )}

            <div className="grid gap-2">
              <Label>Attachments</Label>
              <Input
                type="file"
                multiple
                onChange={(e) => setAttachments(Array.from(e.target.files || []))}
              />
              <p className="text-xs text-gray-500">Selected: {attachments.length} file(s)</p>
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
