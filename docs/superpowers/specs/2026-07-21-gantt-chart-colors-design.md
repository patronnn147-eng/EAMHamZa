# Diagramme de Gantt — Couleurs et chevauchement — Design

Date: 2026-07-21
Fichier concerné : `rapport/chapters/chap1_contexte.tex`, section 1.6 "Planning du stage"

## Problème

Le diagramme de Gantt (pgfgantt) introduit précédemment est en gris uniforme et montre 6 phases strictement séquentielles (mois entiers, sans chevauchement), ce qui ne reflète pas le déroulement réel du stage.

## Décisions

**Couleurs** : dégradé de bleu à 6 teintes, une par phase, du plus foncé (phase 1) au plus clair (phase 6) :
`#274472`, `#3a5f8a`, `#5c85ad`, `#84a9c9`, `#a9c3dc`, `#cfe0ec`.
Chaque `\ganttbar` reçoit `bar/.style={fill=<couleur>}` individuellement (remplace le style global unique `fill=black!60`).

**Chevauchement et découpage** : les bornes de chaque barre passent de valeurs entières à des valeurs fractionnaires (`\ganttbar{...}{début}{fin}`), pgfgantt les supportant nativement sans package additionnel. Les 6 phases initiales sont scindées et complétées avec les travaux ultérieurs (RAG S3, pont ML-RAG, redesign Phase 4) pour un total de 14 phases sur 8 mois :

| # | Phase | Début | Fin |
|---|---|---|---|
| 1 | Analyse des besoins, architecture | 1.0 | 1.5 |
| 2 | Backend — utilisateurs & machines | 1.3 | 2.2 |
| 3 | Backend — ordres de travail/intervention | 1.8 | 2.6 |
| 4 | Frontend — dashboards par rôle | 2.0 | 2.9 |
| 5 | Modèles ML P1 à P3 (panne, classification, RUL) | 2.5 | 3.6 |
| 6 | Modèles ML P4 à P6 (anomalie, priorité, planification) | 3.2 | 4.2 |
| 7 | Fusion DST (Wave 2) | 3.8 | 4.5 |
| 8 | Service RAG — ingestion & stockage S3 | 4.0 | 4.8 |
| 9 | Pont ML-RAG | 4.5 | 5.2 |
| 10 | Module P7 — coordination des pièces | 4.8 | 5.8 |
| 11 | Explicabilité, readiness score, alertes | 5.5 | 6.4 |
| 12 | Phase 4 — redesign des modèles (P3/P4, validation) | 6.2 | 7.3 |
| 13 | Tests, évaluation, corrections | 6.8 | 7.8 |
| 14 | Rédaction du rapport | 7.3 | 8.0 |

L'axe temporel du diagramme passe de 1–6 à 1–8 (mois). Le dégradé de bleu s'étend sur 14 teintes (du plus foncé, phase 1, au plus clair, phase 14).

## Hors périmètre

- Pas de jalons/livrables (marqueurs diamant) — écarté lors du brainstorming.
- Mise en page (largeur pleine page via `\makebox[\textwidth][c]`, `x unit`, etc.) déjà réglée précédemment — réutilisée, ajustée seulement si nécessaire pour la lisibilité des 14 lignes.

## Vérification

Compiler `rapport/main.tex` avec `pdflatex`, confirmer absence d'erreur, et inspecter visuellement la page contenant "Planning du stage (mois)" (rendu PNG via PyMuPDF) pour confirmer couleurs distinctes et chevauchement visible entre barres consécutives.
