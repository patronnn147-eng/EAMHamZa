import { describe, expect, it } from 'vitest';
import { sensorLabel, failureLabel, kToC, confidenceWords, NO_JARGON } from './plainLanguage';

describe('plainLanguage', () => {
  it('maps sensor keys to plain French', () => {
    expect(sensorLabel('process_temperature')).toBe('température du procédé');
    expect(sensorLabel('tool_wear')).toBe("usure de l'outil");
  });
  it('maps failure codes to plain words', () => {
    expect(failureLabel('TWF')).toBe("usure de l'outil");
    expect(failureLabel('HDF')).toBe('surchauffe');
  });
  it('converts Kelvin to Celsius rounded', () => {
    expect(kToC(318.15)).toBe(45);
  });
  it('turns model agreement into words (low conflict = high confidence)', () => {
    expect(confidenceWords(0.1).level).toBe('Élevée');
    expect(confidenceWords(0.5).level).toBe('Moyenne');
    expect(confidenceWords(0.9).level).toBe('Faible');
  });
  it('NO_JARGON matches banned terms', () => {
    expect(NO_JARGON.test('this uses SHAP')).toBe(true);
    expect(NO_JARGON.test('valeur en Kelvin')).toBe(true);
    expect(NO_JARGON.test('trop chaud')).toBe(false);
  });
});
