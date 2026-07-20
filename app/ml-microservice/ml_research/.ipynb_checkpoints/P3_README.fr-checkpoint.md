# P3 — Prédiction de la Durée de Vie Restante

---

## Imaginez ceci

Vous gérez un atelier avec des dizaines de machines qui tournent 24h/24. Chacune finira par tomber en panne — la question, c'est *quand*. Aujourd'hui, vous avez deux options : attendre la panne (réparation d'urgence coûteuse, arrêt de production) ou remplacer les pièces selon un calendrier fixe (gaspillage — vous remplacez souvent des pièces qui ont encore plusieurs mois de vie devant elles).

Ce modèle change la donne. Il surveille les données des capteurs de chaque machine et répond à une seule question : **« Combien de cycles de production reste-t-il à cette machine avant qu'elle ait besoin d'une intervention ? »**

---

## Le problème métier qu'il résout

Sans ce modèle :
- La maintenance est réactive (la machine tombe en panne → panique → coût)
- Ou la maintenance est calendaire (remplacement tous les 3 mois → gaspillage)
- Impossible de prioriser : *quelle* machine a besoin d'attention *en premier* ?

Avec ce modèle :
- Vous obtenez une durée de vie restante prédite pour chaque machine
- Vous pouvez classer les machines par urgence : la machine A a 8 cycles restants, la machine B en a 45 — réparez A en premier
- Vous planifiez les fenêtres de maintenance selon le besoin réel, pas à l'aveugle

---

## Ce que fait concrètement le modèle

Le modèle lit 5 valeurs de capteurs sur chaque machine — température, vitesse, couple, usure de l'outil et pression. Mais au lieu de ne regarder que la mesure actuelle (comme une photo), il observe les **20 derniers cycles** d'historique et apprend *comment la machine évolue dans le temps*. Une machine qui chauffe progressivement depuis 10 cycles est plus à risque qu'une machine qui a eu un pic ponctuel.

C'est comme un médecin qui consulte vos 20 dernières analyses de sang plutôt que juste celle d'aujourd'hui — il peut voir une tendance que vous ne voyez pas.

---

## Comment lire les résultats

Quand le notebook se termine, vous verrez trois chiffres pour chaque modèle. Voici ce qu'ils signifient réellement :

**Erreur de prédiction (MAE) — actuellement 14,95 cycles**
En moyenne, la prédiction du modèle est décalée d'environ 15 cycles. S'il dit qu'une machine a 50 cycles restants, la vraie réponse se situe quelque part entre 35 et 65. C'est comme une météo — ce ne sera pas exact, mais c'est dans la bonne direction et bien mieux que rien.
→ Plus c'est bas, mieux c'est. L'ancien modèle se trompait de 16,25 cycles. Celui-ci fait mieux.

**Précision de classement (C-index) — actuellement 62%**
Sur 100 paires de machines prises au hasard, le modèle identifie correctement laquelle tombera en panne en premier 62 fois. L'ancien modèle avait raison seulement 59 fois sur 100.
→ 50% = pile ou face (inutile). 62% = significativement mieux que le hasard. Pour la planification, c'est le chiffre qui compte le plus — vous devez savoir *qui tombe en panne en premier*, pas la date exacte.

**Score d'ajustement (R²) — actuellement proche de 0**
Mesure à quel point le modèle prédit les cycles exacts. Ce n'est intentionnellement pas la priorité — pour la planification de la maintenance, classer correctement les machines compte plus que viser le chiffre exact.

---

## Le feu tricolore

| | Erreur de prédiction (MAE) | Précision de classement (C-index) |
|---|---|---|
| 🟢 Bon | < 15 cycles | > 62% |
| 🟡 Acceptable | 15–20 cycles | 58–62% |
| 🔴 Insuffisant | > 20 cycles | < 58% |

*Modèle actuel : MAE = 14,95 🟢 · C-index = 62% 🟢*

---

## Ce que « diplômé » signifie pour les opérations

**Quand un modèle est diplômé :**
Le nouveau modèle a passé les deux tests — il classe les machines plus précisément que la version précédente ET son erreur de prédiction reste dans la plage acceptable. Le système remplace automatiquement l'ancien modèle. Aucune action requise de la part des opérations.

**Quand un modèle n'est PAS diplômé :**
Le nouveau modèle n'était pas assez performant. Le modèle de production existant reste en place — rien ne change pour les opérations. L'équipe data science va investiguer et réentraîner.

**Ce qui change dans le système quand un nouveau modèle est diplômé :**
Les prédictions affichées dans le tableau de bord de maintenance seront mises à jour. Des machines classées 3ème en urgence pourraient passer en 1ère position. C'est normal — le nouveau modèle a appris quelque chose que l'ancien n'avait pas vu.

---

## FAQ

**Q : Fonctionne-t-il sur tous les types de machines ?**
Actuellement entraîné sur les données de notre jeu de données AI4I représentant 100 machines dans diverses conditions de fonctionnement. Il se généralise bien pour les machines avec le même profil de capteurs. Si un nouveau type de machine avec des capteurs différents est ajouté, le modèle devra être réentraîné sur ces données.

**Q : Et si la prédiction est fausse ?**
Le modèle donne une fourchette, pas une garantie. Une prédiction de « 50 cycles restants » signifie « probablement entre 35 et 65 ». Utilisez-le pour prioriser — ne le traitez pas comme une échéance stricte. Combinez-le toujours avec le jugement du technicien.

**Q : À quelle fréquence se réentraîne-t-il ?**
Le réentraînement est déclenché manuellement ou selon un calendrier par l'équipe ingénierie. Chaque réentraînement produit un nouveau modèle candidat qui passe le même test de diplomation avant de remplacer le modèle actuel.

**Q : Pourquoi 20 cycles d'historique ?**
Les tests ont montré que regarder 20 cycles en arrière capture les tendances de dégradation significatives sans être trop bruité. Moins de cycles = patterns manqués. Plus de cycles = trop lent à réagir aux changements soudains.

**Q : Quels capteurs utilise-t-il ?**
Température de l'air, température du processus, vitesse de rotation, couple et usure de l'outil. Ce sont les cinq indicateurs clés du stress mécanique et de la dégradation.
