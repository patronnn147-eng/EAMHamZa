# PFE Rapport — Design

Date: 2026-07-02
Norme: ESPRIT ("Rapport de stage — Note pédagogique", AZ2021)

## Objectif

Rédiger le rapport de Projet de Fin d'Études (PFE) couvrant le stage de 6 mois réalisé chez SagemCom sur le projet EAM (plateforme de gestion et de maintenance prédictive d'actifs industriels). Le rapport doit respecter la norme ESPRIT : ~40 pages hors annexes, Times New Roman 12pt, interligne 1.15, marges 2,5cm, titres numérotés (1, 1.1, ...), pas de code dans le corps du texte (renvoyé en annexe), figures numérotées et légendées, bibliographie/netographie en fin de document.

## Périmètre

Le rapport couvre l'ensemble de la plateforme EAM telle que construite durant le stage :
- Backend FastAPI + SQLAlchemy + PostgreSQL
- Frontend Next.js (dashboards Admin / ChefTech / Technicien)
- Microservice ML (Flask) : modèles P1-P6 (probabilité de panne, classification, RUL, anomalie, priorité, planification) + modèles Wave 2 (fusion DST) + P7 (coordination des pièces)
- Service RAG (ingestion documentaire + assistant conversationnel, pont ML↔RAG)
- Infrastructure Docker (MinIO, Postgres, microservices)

Problématique retenue : comment unifier, au sein d'une seule plateforme, la gestion classique des actifs industriels (utilisateurs, machines, ordres de travail/intervention) avec des capacités de maintenance prédictive par ML et un accompagnement terrain intelligent (alertes, explicabilité, assistant conversationnel) ?

## Structure du rapport

### Pages liminaires
- Page de garde (modèle ESPRIT)
- Remerciements
- Sommaire, liste des figures, liste des tableaux, liste des abréviations

### Introduction générale (~1-2p)
Présente le sujet, pose la problématique sans anticiper les résultats, annonce brièvement le contenu de chaque chapitre.

### Chapitre 1 — Contexte général du projet (~5-6p)
- Présentation de l'entreprise SagemCom (placeholder — à compléter par l'étudiant)
- Présentation du service d'accueil et de l'encadrement (placeholder)
- Contexte : enjeux de la maintenance industrielle et de la gestion d'actifs (EAM)
- Problématique du stage
- Objectifs du stage
- Méthodologie de travail adoptée (démarche itérative : spécification → plan → implémentation → vérification, telle que pratiquée durant le stage)
- Planning du stage (diagramme, pleine page, en fin de chapitre)

### Chapitre 2 — Analyse et spécification des besoins (~6-8p)
- Identification des acteurs : Administrateur, Chef Technicien (ChefTech), Technicien
- Besoins fonctionnels : gestion des utilisateurs et des machines, gestion des ordres de travail et d'intervention, planification des interventions, remontée d'alertes, tableaux de bord par rôle, prédictions ML (défaillance, RUL, anomalie, priorité), coordination des pièces de rechange, assistant conversationnel documentaire
- Besoins non fonctionnels : performance, sécurité (authentification, contrôle d'accès par rôle), explicabilité des prédictions, disponibilité
- Diagramme de cas d'utilisation par acteur

### Chapitre 3 — Conception (~8-10p)
- Architecture générale du système (schéma : frontend / backend / microservice ML / service RAG / stockage)
- Modèle de données : entités centrales (Utilisateur, Machine, OrdreTravail, OrdreIntervention, Alerte) et leurs relations
- Architecture du pipeline ML : modèles P1-P6, fusion par théorie de Dempster-Shafer (Wave 2), module P7 de coordination des pièces
- Architecture du service RAG et du pont ML↔RAG (contexte ML injecté dans les réponses conversationnelles)
- Choix technologiques et justification (Next.js, FastAPI, Flask, PostgreSQL, Docker, MinIO)

### Chapitre 4 — Réalisation (~10-12p)
- Réalisation du backend (organisation modulaire des routes et services)
- Réalisation du frontend (tableaux de bord par rôle, système de design)
- Réalisation du pipeline ML (de la prédiction à l'alerte et à l'explication "Why ?")
- Réalisation du service RAG et du pont conversationnel
- Captures d'écran des interfaces clés, avec légendes
- Difficultés techniques rencontrées et solutions apportées

### Chapitre 5 — Tests et résultats (~6-8p)
- Stratégie de test (tests unitaires et d'intégration)
- Évaluation des modèles ML (métriques de performance : erreur de prédiction RUL, indice de concordance, aire sous la courbe ROC pour la détection d'anomalies)
- Démonstration des cas d'usage principaux
- Bilan des difficultés rencontrées durant la réalisation

### Conclusion générale (~2p)
- Récapitulation de la démarche
- Réponse à la problématique posée en introduction
- Apports techniques et personnels du stage
- Perspectives d'amélioration

### Bibliographie / Netographie
Références complètes (auteurs, titres, dates, URLs) des sources techniques utilisées.

### Annexes
Extraits de code significatifs, diagrammes détaillés, tables de métriques complètes.

## Contraintes de forme (rappel norme ESPRIT)

- Police Times New Roman 12pt (corps de texte), titre du document 24pt centré
- Marges 2,5cm, interligne 1.15, justification à droite et à gauche
- Alinéa de première ligne 0,50cm pour les paragraphes
- Titres numérotés (1, 1.1, ...) en gras, taille décroissante selon la profondeur
- Figures numérotées par type (Tab. 1, Fig. 1, Graph. 1) avec légende et référence dans le texte
- Exemples en italique, définitions encadrées, éléments essentiels en gras
- Citations courtes entre guillemets français (« »)
- Numérotation des pages en bas à droite
- Pas de lignes de code dans le corps du rapport — tout détail technique en annexe

## Notes de production

- Les sections marquées « placeholder » (nom du service, encadrants, dates précises) seront à compléter par l'étudiant avant finalisation.
- Le contenu technique s'appuie sur le changelog du projet (`CLAUDE.md`) et le graphe de connaissances généré (`graphify-out/`), qui confirment les entités centrales du modèle de données (Utilisateurs, Machines, Ordres_intervention, Ordres_travail comme nœuds les plus connectés).
- Livrable final : document LaTeX (pdflatex, MiKTeX) compilé en PDF respectant strictement la mise en forme ESPRIT ci-dessus. Packages attendus : `inputenc`+`T1`+`lmodern`+`babel`(french)+`geometry`(marges 2,5cm)+`setspace`(interligne 1.15)+`titlesec`(titres numérotés)+`caption`(légendes figures/tableaux)+`fancyhdr`+`hyperref`. Ne pas utiliser xelatex/lualatex/fontspec (indisponibles sur ce système).
