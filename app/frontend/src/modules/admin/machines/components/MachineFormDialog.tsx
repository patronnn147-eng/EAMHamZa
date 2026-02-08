import React from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { Machine } from '@/lib/types';

const ZONE_OPTIONS = ['ZONE CMS1 - COMPONENT SURFACE MOUNTING', 'ZONE CMS2 - TEST ZONE (Résumé des Machines Essentielles)'];
const SOUS_ZONE_OPTIONS_BY_ZONE: Record<string, string[]> = {
  'ZONE CMS1 - COMPONENT SURFACE MOUNTING': [
    'CMS LINE 1 (e.g., BBS - Broadband Products)',
    'CMS LINE 2 (e.g., AVS - Audio Video Products)',
  ],
  'ZONE CMS2 - TEST ZONE (Résumé des Machines Essentielles)': [
    'TEST IN-SITU (Test des Composants)',
    'TEST FONCTIONNEL (Test de Fonctionnement)',
    'TEST WiFi (Test Sans Fil)',
  ],
};

type OrdreTemplate = { ordre: number; nom: string; fonction?: string };

const ORDRE_TEMPLATES: Record<string, Record<string, OrdreTemplate[]>> = {
  'ZONE CMS1 - COMPONENT SURFACE MOUNTING': {
    'CMS LINE 1 (e.g., BBS - Broadband Products)': [
      { ordre: 1, nom: 'Dépileur (Card Loader)' },
      { ordre: 2, nom: 'Machine de Sérigraphie (DEK/MPM)' },
      { ordre: 3, nom: 'Machine de Pose (Pick & Place)' },
      { ordre: 4, nom: 'Machine SPI (Solder Paste Inspection)' },
      { ordre: 5, nom: 'Machine 2D Scanner (Component Inspection)' },
      { ordre: 6, nom: 'Machine AOI 3D (Final Inspection)' },
      { ordre: 7, nom: 'Four de Refusions (Reflow Oven)' },
      { ordre: 8, nom: 'Poste Insertion Manuelle (Manual THT)' },
      { ordre: 9, nom: 'Machine de Brassage à la Vague (Wave Soldering)' },
    ],
    'CMS LINE 2 (e.g., AVS - Audio Video Products)': [
      { ordre: 1, nom: 'Dépileur' },
      { ordre: 2, nom: 'Machine de Sérigraphie' },
      { ordre: 3, nom: 'Machine de Pose' },
      { ordre: 4, nom: 'Machine SPI' },
      { ordre: 5, nom: 'Machine 2D Scanner' },
      { ordre: 6, nom: 'Machine AOI 3D' },
      { ordre: 7, nom: 'Four de Refusions' },
      { ordre: 8, nom: 'Poste Insertion Manuelle' },
      { ordre: 9, nom: 'Machine de Brassage à la Vague' },
    ],
  },
  'ZONE CMS2 - TEST ZONE (Résumé des Machines Essentielles)': {
    'TEST IN-SITU (Test des Composants)': [
      { ordre: 1, nom: 'Interface de Test (Bed of Nails)', fonction: 'Interface avec sondes pour accéder aux composants' },
      { ordre: 2, nom: 'Testeur Marconi 4220', fonction: 'Testeur principal qui effectue tous les tests électroniques' },
    ],
    'TEST FONCTIONNEL (Test de Fonctionnement)': [
      { ordre: 1, nom: 'Banc TF' },
      { ordre: 2, nom: 'BFE (Banc Front End)' },
      { ordre: 3, nom: 'BAV (Banc Audio Video)' },
      { ordre: 4, nom: 'Routeur' },
    ],
    'TEST WiFi (Test Sans Fil)': [
      { ordre: 1, nom: 'PC avec Logiciels de Test' },
      { ordre: 2, nom: 'Caisson Faraday (Shielding Box)' },
      { ordre: 3, nom: 'IQflex Analyzer' },
      { ordre: 4, nom: 'Routeur' },
      { ordre: 5, nom: 'Switch' },
      { ordre: 6, nom: 'Atténuateurs (30dB, 6dB, 3dB)' },
      { ordre: 7, nom: 'Power Splitter' },
    ],
  },
};

const generateMachineName = (zone: string, sous_zone: string, ordre: string, ordreTemplates: OrdreTemplate[]): string => {
  if (!zone || !sous_zone || !ordre) return '';
  
  let cmsNumber = '';
  if (zone.includes('CMS1')) {
    cmsNumber = '1';
  } else if (zone.includes('CMS2')) {
    cmsNumber = '2';
  }
  
  const subzoneKey = sous_zone.replace(/[^A-Z0-9]/g, '_').toUpperCase();
  const selectedTemplate = ordreTemplates.find(t => t.ordre.toString() === ordre);
  const orderName = selectedTemplate ? selectedTemplate.nom.replace(/[^A-Z0-9]/g, '_').toUpperCase() : '';
  
  return `ZONE_CMS${cmsNumber}_${subzoneKey}_${orderName}`;
};

const getOrdreTemplates = (zone: string, sous_zone: string): OrdreTemplate[] => {
  if (!zone || !sous_zone) return [];
  return ORDRE_TEMPLATES[zone]?.[sous_zone] || [];
};

interface MachineFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  editingMachine: Machine | null;
  formData: {
    nom: string;
    zone: string;
    sous_zone: string;
    ordre: string;
    date_derniere_maintenance: string;
    date_prochaine_maintenance: string;
    image_url: string;
  };
  setFormData: React.Dispatch<React.SetStateAction<any>>;
  onSubmit: () => void;
}

export const MachineFormDialog: React.FC<MachineFormDialogProps> = ({
  open,
  onOpenChange,
  editingMachine,
  formData,
  setFormData,
  onSubmit,
}) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{editingMachine ? 'Edit Machine' : 'Add New Machine'}</DialogTitle>
          <DialogDescription>
            {editingMachine ? 'Update machine information' : 'Enter the details for the new machine'}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="nom">Machine Name (Auto-generated)</Label>
            <Input
              id="nom"
              value={formData.nom}
              readOnly
              placeholder="Generated automatically based on selections"
              className="bg-gray-50"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="zone">Zone</Label>
            <Select
              value={formData.zone}
              onValueChange={(value) => setFormData({ ...formData, zone: value, sous_zone: '', ordre: '' })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a zone" />
              </SelectTrigger>
              <SelectContent>
                {ZONE_OPTIONS.map((z) => (
                  <SelectItem key={z} value={z}>
                    {z}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="sous_zone">Sub-Zone / Line / Test Step</Label>
            <Select
              value={formData.sous_zone}
              onValueChange={(value) => setFormData({ ...formData, sous_zone: value, ordre: '' })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a sub-zone" />
              </SelectTrigger>
              <SelectContent>
                {(
                  (formData.zone &&
                  SOUS_ZONE_OPTIONS_BY_ZONE[formData.zone]
                    ? SOUS_ZONE_OPTIONS_BY_ZONE[formData.zone]
                    : Object.values(SOUS_ZONE_OPTIONS_BY_ZONE).flat()) ||
                  []
                ).map((sz) => (
                  <SelectItem key={sz} value={sz}>
                    {sz}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="ordre">Order</Label>
            <Select
              value={formData.ordre}
              onValueChange={(value) => {
                const templates = getOrdreTemplates(formData.zone, formData.sous_zone);
                const selected = templates.find((t) => t.ordre.toString() === value);
                const generatedName = generateMachineName(formData.zone, formData.sous_zone, value, templates);
                setFormData({
                  ...formData,
                  ordre: value,
                  nom: generatedName || selected?.nom || formData.nom,
                });
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select order" />
              </SelectTrigger>
              <SelectContent>
                {getOrdreTemplates(formData.zone, formData.sous_zone).map((t) => (
                  <SelectItem key={t.ordre} value={t.ordre.toString()}>
                    {t.ordre} - {t.nom}{t.fonction ? ` — ${t.fonction}` : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="date_derniere_maintenance">Last Maintenance Date</Label>
            <Input
              id="date_derniere_maintenance"
              type="date"
              value={formData.date_derniere_maintenance}
              onChange={(e) => setFormData({ ...formData, date_derniere_maintenance: e.target.value })}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="date_prochaine_maintenance">Next Maintenance Date</Label>
            <Input
              id="date_prochaine_maintenance"
              type="date"
              value={formData.date_prochaine_maintenance}
              onChange={(e) => setFormData({ ...formData, date_prochaine_maintenance: e.target.value })}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="image_url">Image URL</Label>
            <Input
              id="image_url"
              value={formData.image_url}
              onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
              placeholder="Enter image URL (optional)"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={onSubmit}>{editingMachine ? 'Update' : 'Create'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
