# P4 — Détection d'Anomalies

---

## Imaginez ceci

Une machine dans votre atelier se comporte bizarrement. Rien n'est encore cassé. Aucune alarme ne s'est déclenchée. Mais quelque chose cloche — les températures sont légèrement plus élevées qu'habituellement, les patterns de vibration ont changé. Un technicien expérimenté le remarquerait. Mais vous ne pouvez pas avoir un technicien expérimenté qui surveille chaque machine à chaque minute.

Ce modèle surveille à votre place. Il a appris à quoi ressemble le « normal » pour chaque machine, et il lève un drapeau dès que quelque chose cesse d'être normal — **avant que quoi que ce soit ne casse**.

---

## Le problème métier qu'il résout

La surveillance traditionnelle attend qu'un seuil soit franchi : « alerte si la température dépasse 400K. » Mais les machines ne tombent pas toujours en panne de manière évidente. Elles se dégradent progressivement, avec des combinaisons de petits signaux qu'aucun seuil unique ne capte.

Sans ce modèle :
- Vous ne savez que quelque chose va mal qu'après la panne
- Les alertes basées sur des règles ratent les patterns subtils multi-capteurs
- Les nouveaux types de pannes (jamais vus auparavant) passent totalement inaperçus

Avec ce modèle :
- Les comportements inhabituels sont signalés automatiquement, même si aucun capteur individuel n'est dans le rouge
- Détecte les patterns de panne jamais rencontrés auparavant — parce qu'il a appris le « normal », pas les « pannes connues »
- Fonctionne comme un premier filtre : signale les machines suspectes, envoyez un technicien investiguer

---

## Ce que fait concrètement le modèle

Quatre méthodes de détection indépendantes analysent chacune les données des capteurs et votent pour savoir si une machine se comporte anormalement. Leurs votes sont combinés en un score unique — plus le score est élevé, plus la machine est suspecte.

**Les quatre détecteurs :**

**1. Autoencodeur (40% du vote)**
Un réseau de neurones entraîné uniquement sur des machines saines. Il a appris à « reconstruire » à quoi ressemblent des lectures de capteurs normales. Quand on lui montre les lectures d'une machine défaillante, il ne peut pas bien les reconstruire — l'erreur de reconstruction est élevée. Erreur élevée = anomalie.
*Analogie : un francophone natif remarque instantanément une phrase qui sonne faux, même s'il ne peut pas expliquer la règle de grammaire.*

**2. Forêt d'Isolation (30% du vote)**
Regroupe toutes les lectures de machines dans une forêt d'arbres de décision. Les lectures qui s'isolent rapidement — loin du groupe principal — sont signalées comme anomalies.
*Analogie : à une fête, la personne seule dans son coin est plus facile à isoler que quelqu'un au milieu de la foule.*

**3. Z-Score (20% du vote)**
Signale toute lecture de capteur statistiquement éloignée de la moyenne. Simple mais rapide — capte les valeurs aberrantes évidentes.
*Analogie : si tout le monde dans le bureau gagne entre 30K et 80K et que quelqu'un gagne 500K, c'est une valeur aberrante statistique.*

**4. Déviation de Cluster (10% du vote)**
Les machines fonctionnent normalement dans l'un des 3 « états » (ex : faible charge, forte charge, transition). Une machine loin de tous les 3 états est suspecte.
*Analogie : une voiture devrait être soit garée, soit en croisière, soit en accélération. Si elle n'est dans aucun de ces états, quelque chose ne va pas.*

---

## Comment lire les résultats

**Précision de détection (ROC-AUC)**
Ce chiffre répond à : « Sur 100 paires aléatoires — une machine saine, une machine défaillante — combien de fois le modèle identifie-t-il correctement laquelle est laquelle ? »

| Score | Ce que ça signifie |
|-------|-------------------|
| 0,50 | Pile ou face — complètement inutile |
| 0,70 | Correct — capte la plupart des cas évidents |
| **0,83** | **Bon — notre référence actuelle (Forêt d'Isolation seule)** |
| 0,90+ | Excellent |

L'ensemble (les 4 détecteurs combinés) bat la Forêt d'Isolation seule. C'est pourquoi on l'utilise.

---

## Le feu tricolore

| | Précision de détection (ROC-AUC) |
|---|---|
| 🟢 Bon | > 0,83 (bat la référence) |
| 🟡 Acceptable | 0,75–0,83 |
| 🔴 Insuffisant | < 0,75 |

*Ensemble actuel : ROC-AUC = bat la référence 🟢 → diplômé en production*

---

## Ce que « diplômé » signifie pour les opérations

**Quand l'ensemble est diplômé :**
Le modèle combinant les 4 détecteurs est plus précis qu'utiliser la Forêt d'Isolation seule. Il remplace le modèle plus simple en production. Les scores d'anomalie affichés dans le tableau de bord de maintenance reflètent désormais cette détection plus riche — attendez-vous à des classements légèrement différents des machines « suspectes ».

**Quand l'ensemble n'est PAS diplômé :**
La combinaison des 4 détecteurs n'a pas battu le modèle plus simple. La Forêt d'Isolation existante reste en production. Les opérations ne voient aucun changement. L'ingénierie investigate pourquoi l'ensemble a sous-performé.

**Ce qui change dans le système :**
Le « score d'anomalie » attaché à chaque machine dans le tableau de bord est recalculé. Une machine qui avait un score de 0,4 avant pourrait avoir 0,7 maintenant — ce qui signifie que le nouveau modèle la considère comme plus suspecte. Les techniciens devraient revoir les machines signalées par le nouveau modèle qui ne l'étaient pas avant.

---

## FAQ

**Q : Peut-il me dire *pourquoi* une machine est signalée ?**
Pas directement — il signale « quelque chose cloche » sans nommer la cause exacte. Considérez-le comme un premier intervenant : il identifie *qu'il y a* un problème, puis un technicien investigate *quel* est le problème.

**Q : Et s'il signale une machine saine (fausse alarme) ?**
Cela arrivera occasionnellement. Le modèle est calibré pour le taux de pannes de notre jeu de données (~3,4% des lectures proviennent de machines défaillantes). Les fausses alarmes sont un compromis face aux détections manquées — on préfère investiguer une fausse alarme plutôt que manquer une vraie panne.

**Q : Et s'il rate une vraie panne ?**
Aucun modèle n'est parfait. Cela fonctionne mieux comme une couche d'une stratégie de maintenance, pas comme la seule. Combinez avec P3 (prédiction de durée de vie restante) et des rondes régulières de techniciens pour une meilleure couverture.

**Q : A-t-il besoin de savoir à quoi ressemble une panne pour la détecter ?**
Non — et c'est son principal avantage. Il apprend uniquement ce à quoi ressemble le *sain*. Cela signifie qu'il peut détecter des types de pannes entièrement nouveaux jamais vus auparavant, parce que tout ce qui ne ressemble pas au « normal » est signalé.

**Q : En quoi est-ce différent d'une simple alarme de température ?**
Une alarme de température se déclenche quand un capteur franchit un seuil. Ce modèle regarde les 5 capteurs simultanément et leurs combinaisons. Une machine peut avoir une température normale mais un ratio couple/vitesse anormal — ce pattern serait invisible pour des alarmes simples mais visible ici.
