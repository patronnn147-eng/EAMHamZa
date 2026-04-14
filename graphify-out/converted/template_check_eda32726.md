<!-- converted from template_check.xlsx -->

## Sheet: Machines
| nom (laisser vide pour auto-génération) | type | emplacement | zone | sous_zone | ordre | statut |
| --- | --- | --- | --- | --- | --- | --- |
|  | CMS | Atelier 1 | ZONE CMS1 - COMPONENT SURFACE MOUNTING | CMS LINE 1 (e.g., BBS - Broadband Products) | 1 | OPERATIONNELLE |
## Sheet: Guide des Règles
| Règle | Description |
| --- | --- |
| Champ 'nom' | Optionnel. Sera généré automatiquement (ex: ZONE_CMS1_CMS_LINE_1_DEPILEUR) si la zone, sous_zone et ordre sont valides. |
| Champ 'zone' | Obligatoire. Doit correspondre EXACTEMENT à une des valeurs autorisées. |
| Champ 'sous_zone' | Obligatoire. Doit correspondre EXACTEMENT à une sous-zone liée à la zone choisie. |
| Champ 'ordre' | Obligatoire. Un chiffre correspondant à l'ordre de la machine (ex: 1, 2, 3). |
| Zones Autorisées | ZONE CMS1 - COMPONENT SURFACE MOUNTING | ZONE CMS2 - TEST ZONE (Résumé des Machines Essentielles) | ZONE TEST FONCTIONNEL | ZONE TEST WiFi | ZONE ASSEMBLAGE | ZONE EMBALLAGE | ZONE QUALITÉ | ZONE MAINTENANCE |
| Sous-zones pour: ZONE CMS1 - COMPONENT SURFACE MOUNTING | CMS LINE 1 (e.g., BBS - Broadband Products) | CMS LINE 2 (e.g., AVS - Audio Video Products) |
| Sous-zones pour: ZONE CMS2 - TEST ZONE (Résumé des Machines Essentielles) | TEST IN-SITU (Test des Composants) | TEST FONCTIONNEL (Test de Fonctionnement) | TEST WiFi (Test Sans Fil) |
| Ordres pour: CMS LINE 1 (e.g., BBS - Broadband Products) | 1=Dépileur (Card Loader) | 2=Machine de Sérigraphie (DEK/MPM) | 3=Machine de Pose (Pick & Place) | 4=Machine SPI (Solder Paste Inspection) | 5=Machine 2D Scanner (Component Inspection) | 6=Machine AOI 3D (Final Inspection) | 7=Four de Refusions (Reflow Oven) | 8=Poste Insertion Manuelle (Manual THT) | 9=Machine de Brassage à la Vague (Wave Soldering) |
| Ordres pour: CMS LINE 2 (e.g., AVS - Audio Video Products) | 1=Dépileur | 2=Machine de Sérigraphie | 3=Machine de Pose | 4=Machine SPI | 5=Machine 2D Scanner | 6=Machine AOI 3D | 7=Four de Refusions | 8=Poste Insertion Manuelle | 9=Machine de Brassage à la Vague |
| Ordres pour: TEST IN-SITU (Test des Composants) | 1=Interface de Test (Bed of Nails) | 2=Testeur Marconi 4220 |
| Ordres pour: TEST FONCTIONNEL (Test de Fonctionnement) | 1=Banc TF | 2=BFE (Banc Front End) | 3=BAV (Banc Audio Video) | 4=Routeur |
| Ordres pour: TEST WiFi (Test Sans Fil) | 1=PC avec Logiciels de Test | 2=Caisson Faraday (Shielding Box) | 3=IQflex Analyzer | 4=Routeur | 5=Switch | 6=Atténuateurs (30dB, 6dB, 3dB) | 7=Power Splitter |