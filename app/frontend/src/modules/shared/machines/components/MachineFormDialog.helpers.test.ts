import { describe, expect, it } from 'vitest';
import {
  generateMachineName,
  getOrdreTemplates,
  shortMachineName,
} from './MachineFormDialog';

describe('shortMachineName', () => {
  it('strips parenthetical suffixes', () => {
    expect(shortMachineName('Dépileur (Card Loader)')).toBe('Dépileur');
  });

  it('drops filler words like "de" and picks the remaining word', () => {
    expect(shortMachineName('Machine de Sérigraphie (DEK/MPM)')).toBe('Sérigraphie');
  });

  it('joins a short (<=2 char) leading word with the next word', () => {
    expect(shortMachineName('PC avec Logiciels de Test')).toBe('PC Logiciels');
  });

  it('falls back to the whole cleaned string when every word is a filler word', () => {
    expect(shortMachineName('DE LA MACHINE')).toBe('DE LA MACHINE');
  });
});

describe('generateMachineName', () => {
  it('returns an empty string when any required field is missing', () => {
    const templates = getOrdreTemplates(
      'ZONE CMS1 - COMPONENT SURFACE MOUNTING',
      'CMS LINE 1 (e.g., BBS - Broadband Products)'
    );
    expect(generateMachineName('', 'sub', '1', templates)).toBe('');
    expect(generateMachineName('zone', '', '1', templates)).toBe('');
    expect(generateMachineName('zone', 'sub', '', templates)).toBe('');
  });

  it('builds a CMS1 line-1 machine name with the short subzone code', () => {
    const zone = 'ZONE CMS1 - COMPONENT SURFACE MOUNTING';
    const subzone = 'CMS LINE 1 (e.g., BBS - Broadband Products)';
    const templates = getOrdreTemplates(zone, subzone);
    expect(generateMachineName(zone, subzone, '1', templates)).toBe('CMS1-L1-DEPILEUR');
  });

  it('strips accents when building the order-name segment', () => {
    const zone = 'ZONE CMS1 - COMPONENT SURFACE MOUNTING';
    const subzone = 'CMS LINE 1 (e.g., BBS - Broadband Products)';
    const templates = getOrdreTemplates(zone, subzone);
    expect(generateMachineName(zone, subzone, '2', templates)).toBe('CMS1-L1-SERIGRAPHIE');
  });

  it('builds a CMS2 test-zone machine name', () => {
    const zone = 'ZONE CMS2 - TEST ZONE (Résumé des Machines Essentielles)';
    const subzone = 'TEST IN-SITU (Test des Composants)';
    const templates = getOrdreTemplates(zone, subzone);
    expect(generateMachineName(zone, subzone, '1', templates)).toBe('CMS2-ISITU-INTERFACE');
  });

  it('falls back to a derived subzone key when no SUBZONE_SHORT entry exists', () => {
    const result = generateMachineName('ZONE CMS1 - X', 'Unknown Subzone Area', '1', []);
    expect(result).toBe('CMS1-UNKNOWN-');
  });

  it('leaves the order segment empty when no template matches the ordre', () => {
    const zone = 'ZONE CMS1 - COMPONENT SURFACE MOUNTING';
    const subzone = 'CMS LINE 1 (e.g., BBS - Broadband Products)';
    const templates = getOrdreTemplates(zone, subzone);
    expect(generateMachineName(zone, subzone, '999', templates)).toBe('CMS1-L1-');
  });

  it('leaves cmsNumber empty when the zone matches neither CMS1 nor CMS2', () => {
    const result = generateMachineName('ZONE OTHER', 'Unknown Subzone', '1', []);
    expect(result).toBe('CMS-UNKNOWN-');
  });
});

describe('getOrdreTemplates', () => {
  it('returns an empty array when zone or subzone is missing', () => {
    expect(getOrdreTemplates('', 'sub')).toEqual([]);
    expect(getOrdreTemplates('zone', '')).toEqual([]);
  });

  it('returns an empty array for an unknown zone/subzone combination', () => {
    expect(getOrdreTemplates('NOT_A_ZONE', 'NOT_A_SUBZONE')).toEqual([]);
  });

  it('returns the real templates for a known zone/subzone', () => {
    const templates = getOrdreTemplates(
      'ZONE CMS2 - TEST ZONE (Résumé des Machines Essentielles)',
      'TEST FONCTIONNEL (Test de Fonctionnement)'
    );
    expect(templates).toHaveLength(4);
    expect(templates[0]).toEqual({ ordre: 1, nom: 'Banc TF' });
  });
});
