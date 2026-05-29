# Nyaya — Guide d'utilisation

Nyaya est un backend IA appelé par le backend principal d'un réseau social. Il fait deux choses :

1. **Évaluer chaque message** dès qu'il est posté, en lui attribuant une note sur plusieurs critères de qualité communicationnelle.
2. **Générer une review mensuelle** pour chaque utilisateur actif : un feedback personnalisé rédigé par l'IA et des totems (badges de classement) attribués selon la position dans le classement global et par critère.

---

## Authentification

Toutes les routes exigent un header `X-API-Key` contenant la clé partagée configurée dans `API_KEY`. C'est le backend appelant qui gère cette clé — les utilisateurs finaux du réseau social n'interagissent jamais directement avec Nyaya.

---

## Les routes

### 1. Soumettre un message — `POST /api/v1/messages/`

Le backend principal appelle cette route à chaque fois qu'un utilisateur publie un message (post, commentaire, réponse…).

Nyaya enregistre le message, crée le profil utilisateur s'il n'existe pas encore, puis lance en arrière-plan l'évaluation IA. La réponse est immédiate : seul l'identifiant interne du message est retourné — l'évaluation arrive quelques secondes plus tard de manière asynchrone.

**Ce qu'il faut envoyer :**

- L'identifiant du message dans le réseau social (`content_id`)
- Le type de contenu (`content_type` : post, commentaire…)
- Le texte du message
- La date de publication
- L'identifiant de l'auteur dans le réseau social (`author_id`)

Si le même `content_id` est envoyé deux fois, la route renvoie une erreur `409` — pas de double évaluation.

---

### 2. Récupérer l'évaluation d'un message — `GET /api/v1/evaluations/{content_id}`

Permet de consulter le résultat de l'évaluation IA pour un message donné.

La réponse contient la note globale du message (sur 100) ainsi que le détail par critère : clarté des idées, exactitude, pertinence, logique, absence de sophismes, ouverture d'esprit, volonté de comprendre, contribution utile, respect. Voir la section [Critères d'évaluation](#critères-dévaluation) pour le détail.

---

### 3. Lister tous les totems disponibles — `GET /api/v1/totems/`

Retourne la liste complète des totems existants dans le système, avec leur code, nom, description et catégorie. Utile pour initialiser l'affichage côté frontend ou pour synchroniser un catalogue de badges.

---

### 4. Totems d'un utilisateur pour un mois donné — `GET /api/v1/users/{user_id}/{year_month}/totems`

Retourne les totems qu'un utilisateur a obtenus lors d'un mois précis.

Le paramètre `year_month` est au format `YYYY-MM` (exemple : `2025-04`). Les totems sont générés une fois par mois par la review mensuelle — cette route ne retourne donc des données que pour les mois déjà traités.

---

### 5. Historique des totems d'un utilisateur — `GET /api/v1/users/{user_id}/totems`

Retourne les totems obtenus par un utilisateur sur plusieurs mois, du plus récent au plus ancien.

Deux paramètres optionnels permettent de paginer les résultats : `limit` (nombre de résultats, 1–24, défaut 6) et `offset` (décalage).

---

### 6. Feedback mensuel d'un utilisateur — `GET /api/v1/users/{user_id}/{year_month}/feedback`

Retourne le feedback IA généré pour un utilisateur lors d'un mois donné.

Le feedback est un texte rédigé par le LLM qui analyse les points faibles de l'utilisateur dans ses échanges du mois. Il identifie les catégories où les scores sont les plus bas et cite des exemples de messages pour illustrer les axes d'amélioration. Ce feedback n'est généré que si l'utilisateur a posté suffisamment de messages dans le mois (seuil configurable via `REVIEW_MIN_MESSAGES`).

---

### 7. Historique des feedbacks d'un utilisateur — `GET /api/v1/users/{user_id}/feedbacks`

Retourne les feedbacks mensuels d'un utilisateur sur plusieurs mois.

Mêmes paramètres de pagination que pour l'historique des totems (`limit` et `offset`).

---

## La review mensuelle

La review est une tâche planifiée qui s'exécute automatiquement une fois par mois (en début de mois, sur le mois précédent). Elle n'est pas déclenchée par une route HTTP.

**Déroulement :**

1. **Éligibilité** — Seuls les utilisateurs ayant posté au moins `REVIEW_MIN_MESSAGES` messages le mois précédent sont traités.
2. **Feedback IA** — Pour chaque utilisateur éligible, le LLM reçoit les messages les plus mal notés dans les catégories les plus faibles, et génère un feedback personnalisé en texte libre.
3. **Classements** — Les utilisateurs sont classés globalement (note moyenne toutes catégories) et par critère individuel.
4. **Attribution des totems** — Chaque utilisateur reçoit le totem correspondant à son meilleur palier dans chaque classement où il figure dans le top 50 %.

La review est **idempotente** : si elle est lancée deux fois pour le même mois, les feedbacks et totems déjà générés ne sont pas recréés.

---

## Critères d'évaluation

L'IA note chaque message sur une échelle de 1 à 5 pour chacun des critères suivants, puis calcule une note globale pondérée sur 100.

| Critère | Poids | Ce qui est évalué |
| --- | --- | --- |
| Clarté des idées | 10 % | L'idée centrale est identifiable, les phrases sont sans ambiguïté |
| Exactitude et vérifiabilité | 15 % | Distinction fait/opinion, affirmations nuancées ou sourcées |
| Pertinence | 10 % | La réponse est ancrée dans le sujet ou la question précédente |
| Logique et cohérence | 15 % | Enchaînement logique, absence de contradiction interne |
| Absence de sophismes | 15 % | Pas d'ad hominem, faux dilemme, généralisation abusive… |
| Ouverture d'esprit | 10 % | Nuance exprimée, limites de sa position reconnues |
| Volonté de comprendre | 8 % | Reformulation, question ouverte vers l'interlocuteur |
| Contribution utile | 12 % | Information nouvelle, solution, reformulation clarifiante |
| Respect et collaboration | 4 % | Ton neutre ou constructif, absence d'attaque personnelle |
| Likes (popularité) | 1 % | Nombre de likes normalisé — fourni par le réseau social |

---

## Les totems

Un totem est un badge de classement attribué en fin de mois. Il existe un totem par critère et un totem global, chacun décliné en paliers selon la position dans le classement.

| Palier | Signification |
| --- | --- |
| `top_1_absolu` | Premier absolu (rang #1) |
| `top_1_pct` | Top 1 % des utilisateurs |
| `top_5_pct` | Top 5 % |
| `top_10_pct` | Top 10 % |
| `top_25_pct` | Top 25 % |
| `top_50_pct` | Top 50 % |

Les utilisateurs hors top 50 % ne reçoivent aucun totem. Un utilisateur peut recevoir jusqu'à 10 totems par mois (un par critère + un global), chacun correspondant au meilleur palier atteint dans ce classement.

Exemples de codes : `clarte_des_idees_top_10_pct`, `absence_de_sophismes_top_1_absolu`, `global_top_25_pct`.
