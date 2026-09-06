<p align="right"><a href="README.md">🇬🇧 English</a> · <strong>🇫🇷 Français</strong></p>

# ZEvent Dataviz

![Python](https://img.shields.io/badge/python-3.14-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/streamlit-app-FF4B4B?logo=streamlit&logoColor=white)
![uv](https://img.shields.io/badge/g%C3%A9r%C3%A9%20avec-uv-DE5FE9)
![Ruff](https://img.shields.io/badge/lint%20%2B%20format-ruff-D7FF64)
![ty](https://img.shields.io/badge/v%C3%A9rification%20de%20types-ty-1E90FF)
![PostgreSQL](https://img.shields.io/badge/base%20de%20donn%C3%A9es-PostgreSQL-4169E1?logo=postgresql&logoColor=white)

Tableaux de bord de modélisation de données pour le marathon caritatif de jeu
vidéo ZEvent — dons, streamers, jeux, chat et communauté, chacun sur sa
propre page Streamlit, alimentés par une connexion PostgreSQL mutualisée (via
PgBouncer) avec un jeu de données factices en secours pour le développement
local. Un ensemble de filtres présents dans la barre latérale (plage de
dates, streamers, chatteurs, recherche d'entité, langue EN/FR) s'applique de
façon cohérente sur toutes les pages — voir
[Filtres globaux](#filtres-globaux).

## Sommaire

- [Vue d'ensemble](#vue-densemble)
- [Architecture](#architecture)
- [Structure du projet](#structure-du-projet)
- [Démarrage](#démarrage)
- [Configuration](#configuration)
- [Pages](#pages)
- [Filtres globaux](#filtres-globaux)
- [Développement](#développement)
- [Sécurité](#sécurité)
- [Données et méthodologie](#données-et-méthodologie)
- [Philosophie de code](#philosophie-de-code)

## Vue d'ensemble

L'application est un petit ensemble de pages Streamlit ciblées, une par
thématique de modélisation de données, lisant une base PostgreSQL partagée
via une couche de dépôt (repository) typée. Tant que les identifiants réels
de la base ne sont pas fournis, chaque page fonctionne de bout en bout avec
des données d'exemple déterministes, ce qui permet de développer, relire et
présenter l'application hors ligne.

## Architecture

```mermaid
flowchart LR
    Browser["Navigateur (visiteur)"] -- HTTPS / WSS --> Proxy["Reverse proxy\n(terminaison TLS, au déploiement)"]
    Proxy --> App["Serveur Streamlit\napp/🏠_Home.py + app/pages/*"]
    App --> Repo["app/data/repository.py\n(API d'accès aux données typée)"]
    Repo -- sans identifiants BDD --> Mock["app/data/mock.py\n(données d'exemple déterministes)"]
    Repo -- identifiants BDD configurés --> DB[("PostgreSQL\n(connexions mutualisées)")]
    App --> Config["app/core/config.py\n(.env / variables d'environnement)"]
    App --> Logging["app/core/logging_config.py\n(colorlog, id par session)"]
```

La couche de dépôt (repository) est la seule chose qui change lorsque la
vraie base de données est branchée — les pages ne parlent jamais directement
à la base de données ni aux données factices.

## Structure du projet

```
zevent-dataviz/
├── app/
│   ├── 🏠_Home.py                 # Point d'entrée Streamlit : filtres/recherche/langue rendus ici
│   ├── pages/                     # Une page par thématique de modélisation (voir Pages ci-dessous)
│   │   ├── 1_📈_Donations.py
│   │   ├── 2_🎙️_Streamers.py
│   │   ├── 3_🎮_Games.py
│   │   ├── 4_🎯_Donation_Goals.py
│   │   ├── 5_💬_Live_Chat.py
│   │   ├── 6_👥_Community.py
│   │   ├── 7_🏆_Donation_Tracker.py
│   │   ├── 8_🗣️_Chatters.py
│   │   ├── 9_📺_Activity.py
│   │   ├── 10_ℹ️_About.py
│   │   ├── 11_🔎_Chat_Messages.py
│   │   ├── 12_🥇_Leaderboard.py
│   │   ├── 13_🧠_Chat_Intelligence.py
│   │   └── 14_🔬_Chat_ML_Lab.py
│   ├── core/
│   │   ├── config.py             # Réglages : variables d'env / .env, jamais de secret en dur
│   │   ├── logging_config.py     # Configuration pilotée par logging.yml, id de session
│   │   ├── db.py                 # Moteur SQLAlchemy mutualisé (st.cache_resource)
│   │   ├── tz.py                 # Utilitaires fuseau Europe/Paris (convention datetime naïf)
│   │   ├── i18n.py               # Sélecteur de langue EN/FR (t(), language_selector())
│   │   └── translations.py       # Le catalogue de chaînes EN/FR
│   ├── data/
│   │   ├── mock.py               # Données d'exemple déterministes
│   │   ├── repository.py         # API d'accès aux données (mock vs. Postgres)
│   │   ├── goal_progress.py      # Calcul partagé début/fin/durée d'un objectif
│   │   ├── bot_heuristic.py      # Filtre heuristique des chatteurs probablement des bots
│   │   ├── anonymize.py          # Anonymisation de l'identité des chatteurs
│   │   ├── emote_cdn.py          # Résolution des URLs d'images d'emotes Twitch
│   │   ├── external_donations.py # Sources de dons externes (hors Twitch)
│   │   ├── chat_nlp.py           # Analyse de texte du chat, légère, sans dépendance
│   │   ├── chat_lexicons.py      # Listes de mots hostiles/positifs/hype (Chat Intelligence)
│   │   └── chat_ml.py            # ML réel : clustering/anomalies/prévision sklearn + transformers (Chat ML Lab)
│   └── components/
│       ├── theme.py              # Palette de graphiques & mise en page Plotly partagée
│       ├── chrome.py             # En-tête de page, bandeau source de données, sélecteur de langue
│       ├── filters.py            # Filtres globaux date/streamer/chatteur (widgets + application)
│       ├── search.py             # Recherche globale d'entité (saut vers la page correspondante)
│       └── network_graph.py      # Graphe de réseau à disposition dynamique (networkx + Plotly)
├── tests/                        # Suite de tests pytest
├── .streamlit/config.toml        # Configuration serveur & thème
├── .env.example                  # Variables d'environnement documentées (sans secret)
├── logging.yml                   # Profils de logs (development / production)
└── .claude/skills/karpathy-guidelines/SKILL.md  # Philosophie de code de ce dépôt
```

## Démarrage

Nécessite [uv](https://docs.astral.sh/uv/) et Python 3.14 (uv installe
l'interpréteur automatiquement).

```bash
git clone <ce-dépôt>
cd zevent-dataviz
uv sync                      # installe les dépendances dans .venv
cp .env.example .env         # renseigner les identifiants BDD une fois disponibles
uv run streamlit run app/🏠_Home.py
```

Sans identifiants de base de données dans `.env`, l'application fonctionne
immédiatement avec des données d'exemple — chaque page marche dès le départ.

## Configuration

Toute la configuration passe par des variables d'environnement (ou un
fichier `.env`), jamais en dur dans le code. Voir
[`.env.example`](.env.example) pour la liste complète ; les champs liés à la
base de données :

| Variable | Description | Valeur par défaut |
|---|---|---|
| `DB_HOST` | Hôte PostgreSQL/PgBouncer | _non défini → données factices_ |
| `DB_PORT` | Port PostgreSQL/PgBouncer | `5432` |
| `DB_NAME` | Nom de la base | _non défini_ |
| `DB_USER` | Utilisateur de la base (un rôle **lecture seule** est fortement recommandé) | _non défini_ |
| `DB_PASSWORD` | Mot de passe de la base | _non défini_ |
| `DB_POOL_SIZE` | Taille de base du pool de connexions | `5` |
| `DB_MAX_OVERFLOW` | Connexions supplémentaires autorisées en pic de charge | `10` |
| `DB_STATEMENT_TIMEOUT_MS` | Durée max qu'une requête peut retenir une connexion | `15000` |
| `APP_ENV` | `development` ou `production` — sélectionne aussi le profil [`logging.yml`](logging.yml) | `development` |

## Pages

Chaque page a un sélecteur de langue (EN/FR) dans la barre latérale, qui traduit tout le contenu de l'interface — voir `app/core/translations.py`.

| Page | Thématique |
|---|---|
| 📈 Donations | Dons cumulés, un podium top-3, rythme horaire, cette année vs. les éditions ZEvent passées, une course animée des dons par chaîne, les moments de pic de dons, répartition par phase, mouvements du classement, contrôle qualité |
| 🎙️ Streamers | Classement par dons/engagement/audience ; nuage de points de corrélation coloré par efficacité de don ; comparaison de jusqu'à 4 streamers sur un radar en percentiles, le mix de fidélité des chatteurs et le profil horaire ; chatteurs les plus actifs parmi les streamers sélectionnés |
| 🎮 Games | Catégories jouées, audience simultanée sur la durée de l'événement, sessions de stream récentes, et un classement des titres de stream par messages/dons |
| 🎯 Donation Goals | Les objectifs de dons fixés par les streamers, par catégorie et par streamer, un histogramme des montants à seuil ajustable, et un graphique ambition vs réalité (% de couverture des objectifs) |
| 💬 Live Chat | Volume de messages et taux d'engagement dans le temps, une course animée du nombre de messages par chaîne, les moments de pic de chat, une carte de chaleur chaîne×heure, chaînes les plus actives, emotes les plus utilisées |
| 👥 Community | Mix de fidélité et d'ancienneté des chatteurs, croissance cumulée des chatteurs, un graphe de réseau à disposition dynamique heure par heure des audiences partagées, chatteurs les plus actifs, paires de chaînes à audience partagée |
| 🏆 Donation Tracker | Suit le début/la complétion/la durée de chaque objectif de type « donation » — globalement sur tous les streamers, et par streamer, avec une chronologie façon Gantt |
| 🗣️ Chatters | Page Chatteurs, miroir de Streamers : classement par activité/étendue/fidélité, détail du profil par chaîne d'un chatteur |
| 📺 Activity | Chronologie titre/catégorie de stream par streamer — quand et à quelle fréquence un streamer a changé ce qu'il jouait |
| 🔎 Chat Messages | Parcourir et rechercher en plein texte des messages de chat individuels, avec l'identité réelle du chatteur/de la chaîne affichée |
| 🥇 Leaderboard | Podiums top-3 consolidés et classements complets, regroupant les différents classements par entité de l'application |
| 🧠 Chat Intelligence | Analyse légère, sans dépendance ML, du chat en direct — listes de mots hostilité/positivité, tendances d'emotes hype, détection de copier-coller, exemples de toxicité avec identité réelle du chatteur/de la chaîne |
| 🔬 Chat ML Lab | ML réel entraîné sur le chat et les données streamers/chatteurs : clustering de sujets de messages (KMeans + TF-IDF), clustering comportemental streamers/chatteurs avec projection 2D par ACP, détection d'anomalies par Isolation Forest, classification sentiment/toxicité par modèle transformer pré-entraîné comparée à l'heuristique par liste de mots, et un modèle de prévision de dons (Random Forest) qui prédit le total final de chaque streamer à partir d'un instantané en cours d'événement |
| ℹ️ About | Ce qu'est ZEvent, ce que fait ce tableau de bord et comment fonctionne son pipeline de données |

La vraie base (schémas `raw`/`stg`/`int`/`marts`, modélisés avec dbt) n'a
aucune dimension « équipe » pour les streamers, qui sont donc classés
individuellement plutôt que groupés, et aucune donnée de sentiment/émotion —
le taux d'engagement du chat (messages/min/100 viewers) est le signal réel
le plus proche de « l'engouement ». Elle est alimentée par **deux pipelines
indépendants** : un pipeline de dons (le site ZEvent lui-même —
`mart_donations__*`, `mart_event__*`, `mart_donation_goals__*`) et un
pipeline de métadonnées/chat Twitch (`mart_streams__*`, `mart_chat__*`,
`mart_chatters__*`, `mart_community__*`). Le champ `game` du pipeline de dons
n'est pas alimenté avant le début de l'événement, donc la page Games lit
volontairement les catégories depuis le pipeline Twitch. Les noms d'utilisateur
du chat ne sont dans aucune table `raw.chat_messages_*` accessible à ce rôle,
mais sont récupérables via `int.int_chat__chatter_activity.chatter`, joint
par `chatter_id`. Voir le point d'extension
`app/data/repository.py::PostgresDataSource`.

## Filtres globaux

Rendus une seule fois, dans la barre latérale (`app/🏠_Home.py`, via
`app/components/filters.py` et `app/components/search.py`) — Streamlit
ré-exécute ce point d'entrée avant chaque page, donc un seul rendu à cet
endroit place les filtres au-dessus des liens de navigation partout :

- **Plage de dates** — un curseur borné par les horodatages propres à
  l'événement (pas l'heure « maintenant », pour ne pas casser silencieusement
  avec des données factices ou après la fin de l'événement). Chaque page
  récupère ses données soit directement avec `(start, end)` issus de cette
  plage, soit en filtrant un DataFrame déjà récupéré avec
  `apply_global_date_filter`.
- **Streamers** / **Chatteurs** — des menus multi-sélection dans la barre
  latérale qui restreignent les données de chaque page aux entités
  sélectionnées (`apply_global_streamer_filter` / `apply_global_chatter_filter`) ;
  laissés vides, chaque page affiche tout le monde.
- **Recherche** — une boîte dans la barre latérale qui trouve un
  streamer/chatteur/chaîne par son nom et bascule vers la page qui le
  couvre, en préremplissant le widget de recherche/filtre local de cette
  page (`consume_search_query()`).
- **Langue (EN/FR)** — `language_selector()`, appuyé sur
  `app/core/translations.py` ; chaque chaîne visible par l'utilisateur, sur
  chaque page, passe par `t()`.

## Développement

```bash
uv run ruff format .        # mise en forme
uv run ruff check . --fix   # linting (docstrings style Google exigées)
uv run ty check .           # vérification statique des types
uv run pytest               # tests
```

Les quatre commandes doivent passer avant qu'un changement soit considéré
comme terminé — voir
[`.claude/skills/karpathy-guidelines/SKILL.md`](.claude/skills/karpathy-guidelines/SKILL.md)
pour les standards de code de ce dépôt.

## Sécurité

Conçue pour, à terme, être exposée sur Internet public, donc :

- **Secrets** : uniquement dans des variables d'environnement / `.env`
  (ignorés par git) — jamais dans le code source, jamais dans les logs.
  Utiliser un rôle de base de données **lecture seule**.
- **Injection SQL** : chaque requête vers la vraie base utilise
  `sqlalchemy.text()` avec des paramètres liés ; aucune requête SQL n'est
  construite par concaténation ou formatage de chaînes dans ce dépôt.
- **Épuisement des connexions** : un seul `Engine` mutualisé et borné est
  partagé par toutes les sessions concurrentes (`st.cache_resource`), avec
  `pool_pre_ping` et `pool_recycle`. La base est derrière **PgBouncer**, donc
  `statement_timeout` est appliqué via un `SET` à chaque emprunt de connexion
  au pool plutôt qu'en paramètre de démarrage — PgBouncer ne transmet qu'une
  liste fixe de paramètres de démarrage et rejette les autres, et réappliquer
  ce réglage à chaque emprunt est aussi le bon comportement sous le mode de
  pooling par transaction de PgBouncer, où une session logique peut se voir
  attribuer une connexion backend différente entre deux transactions.
- **Charge sur la base** : les résultats de requête sont mis en cache côté
  serveur pour une courte durée (`st.cache_data`), afin que de nombreux
  visiteurs simultanés partagent une même requête plutôt que d'en déclencher
  une nouvelle à chaque fois.
- **CSRF / origine croisée** : `server.enableXsrfProtection` et
  `server.enableCORS` sont activés ; avant un déploiement public, configurer
  aussi `server.allowedHosts` avec le(s) vrai(s) domaine(s) — aucun des deux
  réglages seul ne restreint les connexions WebSocket cross-origin.
- **Surface d'erreur** : `client.showErrorDetails` est désactivé, un
  visiteur en production voit une erreur générique, jamais une pile
  d'exécution interne.
- **Logs** : structurés, horodatés, tagués avec un identifiant de session
  (pour distinguer les logs de visiteurs concurrents), répartis par niveau
  dans des fichiers compressés (gzip) avec rotation sous `logging/`
  (configuration dans [`logging.yml`](logging.yml)) — jamais d'identifiants
  ni de chaîne de connexion complète loggés.

## Données et méthodologie

Tant que les identifiants réels ne sont pas configurés, tous les chiffres
proviennent de `app/data/mock.py` — des données d'exemple clairement
déterministes, signalées par un bandeau visible sur chaque page.

Avec la vraie base connectée : les chiffres reflètent le pipeline de
l'événement tel qu'il est en ce moment, ce qui peut vouloir dire des
graphiques majoritairement à zéro/vides avant le vrai démarrage du ZEvent —
c'est exact, pas un bug. Deux points de vigilance :

- **Les montants des objectifs de dons ne sont pas des chiffres « argent
  réel » fiables.** Les streamers fixent eux-mêmes leurs montants d'objectif,
  et des blagues à plusieurs centaines de millions d'euros côtoient des
  objectifs sincères. La page Donation Goals affiche des comptages, pas des
  montants sommés, précisément pour cette raison.
- **Aucune dimension « équipe »** n'existe dans l'entrepôt de données — la
  page Streamers classe uniquement des individus.

## Philosophie de code

Voir [`.claude/skills/karpathy-guidelines/SKILL.md`](.claude/skills/karpathy-guidelines/SKILL.md) :
lisibilité avant ingéniosité, indirection minimale, pas de généralité
spéculative. Les assistants IA ne sont **jamais** listés comme co-auteurs des
commits de ce dépôt.
