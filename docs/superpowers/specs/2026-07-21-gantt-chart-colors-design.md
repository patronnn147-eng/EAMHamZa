# Diagramme de Gantt — Couleurs et chevauchement — Design

Date: 2026-07-21
Fichier concerné : `rapport/chapters/chap1_contexte.tex`, section 1.6 "Planning du stage"

## Problème

Le diagramme de Gantt (pgfgantt) introduit précédemment est en gris uniforme et montre 6 phases strictement séquentielles (mois entiers, sans chevauchement), ce qui ne reflète pas le déroulement réel du stage.

## Décisions

**Couleurs** : dégradé de bleu à 6 teintes, une par phase, du plus foncé (phase 1) au plus clair (phase 6) :
`#274472`, `#3a5f8a`, `#5c85ad`, `#84a9c9`, `#a9c3dc`, `#cfe0ec`.
Chaque `\ganttbar` reçoit `bar/.style={fill=<couleur>}` individuellement (remplace le style global unique `fill=black!60`).

**Chevauchement** : les bornes de chaque barre passent de valeurs entières à des valeurs fractionnaires (`\ganttbar{...}{début}{fin}`), pgfgantt les supportant nativement sans package additionnel :

| Phase | Début | Fin |
|---|---|---|
| Analyse des besoins, architecture | 1.0 | 1.5 |
| Backend & frontend | 1.3 | 2.7 |
| Modèles ML P1 à P6 | 2.3 | 3.7 |
| Service RAG, pont ML-RAG | 3.3 | 4.5 |
| Module P7, dashboards | 4.2 | 5.3 |
| Tests, rédaction rapport | 5.0 | 6.0 |

## Hors périmètre

- Pas de sous-tâches par phase, pas de jalons/livrables, pas de granularité hebdomadaire (options écartées lors du brainstorming).
- Mise en page (largeur pleine page via `\makebox[\textwidth][c]`, `x unit=2.2cm`, etc.) déjà réglée précédemment — inchangée.

## Vérification

Compiler `rapport/main.tex` avec `pdflatex`, confirmer absence d'erreur, et inspecter visuellement la page contenant "Planning du stage (mois)" (rendu PNG via PyMuPDF) pour confirmer couleurs distinctes et chevauchement visible entre barres consécutives.
