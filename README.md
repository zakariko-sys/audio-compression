# 🎵 Audio Compression Multi-Agent

[![GitHub](https://img.shields.io/badge/GitHub-zakariko--sys%2Faudio--compression-blue?logo=github)](https://github.com/zakariko-sys/audio-compression)
[![Render](https://img.shields.io/badge/Deployed%20on-Render-0aaaaa?logo=render)](https://audio-compression.onrender.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python)](https://www.python.org/)

Un système d'orchestration multi-agent pour la compression audio intelligente, déployé sur cloud avec n8n comme orchestrateur workflow.

---

## 📋 Table des matières

- [Objectif](#objectif)
- [Architecture](#architecture)
- [Endpoints API](#endpoints-api)
- [Installation & Configuration](#installation--configuration)
- [Utilisation](#utilisation)
- [Dépannage](#dépannage)
- [Licence](#licence)

---

## 🎯 Objectif

Ce projet compresse intelligemment un fichier audio en analysant ses caractéristiques et en choisissant automatiquement le meilleur codec et débit :

1. **Agent Analyse** → Extrait les caractéristiques audio (spectre, durée, canaux, contenu)
2. **Agent Décision** → Choisit codec + bitrate optimal via règles heuristiques
3. **Agent Compression** → Compresse le fichier avec les paramètres décidés
4. **Agent Évaluation** → Mesure la qualité (SNR, PSNR, MSE)

Le workflow n8n orchestre ces étapes et génère un rapport final.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     n8n Cloud (Orchestrator)                 │
│  ┌────────────────┐   ┌──────────────────────────────────┐  │
│  │ Audio Form ⬆️  │──→│ 1. Call Upload API               │  │
│  └────────────────┘   │ 2. Call Analyser API             │  │
│                       │ 3. Call Decision API             │  │
│                       │ 4. Call Compression API          │  │
│                       │ 5. Call Evaluation API           │  │
│                       │ 6. Generate Report (JavaScript)  │  │
│                       │ 7. Convert to File ⬇️            │  │
│                       └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ⬇️
                        HTTP/JSON (REST)
                              ⬇️
┌─────────────────────────────────────────────────────────────┐
│            Render Cloud (Backend API Server)                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Flask API Server (api_agent.py)                    │   │
│  ├─ /api/upload ───────→ [file_id storage]            │   │
│  ├─ /api/analyser ─────→ AgentAnalyse (librosa)       │   │
│  ├─ /api/decider ──────→ DecisionAgent (heuristics)   │   │
│  ├─ /api/compresser ───→ CompressorAgent (pydub+FFmpeg) │   │
│  ├─ /api/evaluer ──────→ EvaluatorAgent (metrics)     │   │
│  └─ /health ───────────→ Status check                 │   │
│                                                         │   │
│  Déploiement via Dockerfile:                           │   │
│  • Python 3.11-slim base                              │   │
│  • FFmpeg + libsndfile installés                       │   │
│  • Gunicorn server (production)                        │   │
│  • PORT env variable                                  │   │
│                                                         │   │
│  GitHub trigger → Render auto-redeploy                │   │
│  (chaque push == nouvelle version)                     │   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔌 Endpoints API

### Base URL
```
https://audio-compression.onrender.com
```

### 1️⃣ POST /api/upload
**Stocke le fichier audio et retourne un identifiant unique**

Request (multipart/form-data):
```
fichier: <audio_file_binary>
```

Response:
```json
{
  "success": true,
  "file_id": "a1b2c3d4e5f6g7h8",
  "stored_path": "/tmp/audio_api_store/a1b2c3d4e5f6g7h8.wav",
  "size_bytes": 1048576
}
```

---

### 2️⃣ POST /api/analyser
**Analyse les caractéristiques audio**

Request (JSON):
```json
{
  "file_id": "a1b2c3d4e5f6g7h8"
}
```

Response:
```json
{
  "success": true,
  "analyse": {
    "duree_s": 45.2,
    "taux_echantillonnage_hz": 44100,
    "canaux": 2,
    "probabilite_parole": 0.1,
    "probabilite_musique": 0.85,
    "etiquette_contenu": "musique",
    "file_id": "a1b2c3d4e5f6g7h8"
  }
}
```

---

### 3️⃣ POST /api/decider
**Choisit codec et débit optimal**

Request (JSON):
```json
{
  "analyse": {
    "duree_s": 45.2,
    "canaux": 2,
    "probabilite_musique": 0.85,
    ...
  }
}
```

Response:
```json
{
  "success": true,
  "decision": {
    "codec": "aac",
    "debit_kbps": 128,
    "mode": "VBR",
    "justification": "Musique détectée → AAC recommandé",
    "raisonnement": {
      "classe_contenu": "musique",
      "canaux": 2,
      "source_sans_perte": false
    }
  }
}
```

---

### 4️⃣ POST /api/compresser
**Compresse le fichier avec les paramètres décidés**

Request (JSON):
```json
{
  "file_id": "a1b2c3d4e5f6g7h8",
  "decision": {
    "codec": "aac",
    "debit_kbps": 128,
    "mode": "VBR"
  }
}
```

Response:
```json
{
  "success": true,
  "compression": {
    "taux_compression": 75.3,
    "taille_originale_ko": 4096.5,
    "taille_compressée_ko": 1015.8,
    "codec": "aac",
    "bitrate": "128k",
    "output_file_id": "x9y8z7w6v5u4t3s2"
  }
}
```

---

### 5️⃣ POST /api/evaluer
**Mesure la qualité après compression**

Request (JSON):
```json
{
  "file_id": "a1b2c3d4e5f6g7h8",
  "compression": {
    "output_file_id": "x9y8z7w6v5u4t3s2"
  }
}
```

Response:
```json
{
  "success": true,
  "evaluation": {
    "mse": 0.0012,
    "snr_db": 62.5,
    "psnr_db": 68.2,
    "qualite": "Excellente",
    "niveau": 5,
    "conclusion": "Compression réussie, qualité préservée"
  }
}
```

---

### 🏥 GET /health
**Test de disponibilité du serveur**

Request:
```
GET /health
```

Response:
```json
{
  "status": "ok"
}
```

---

## 📦 Installation & Configuration

### Prérequis (autre PC)
- Compte n8n (Cloud ou self-hosted)
- Accès au repo GitHub : `https://github.com/zakariko-sys/audio-compression`
- Pour exécution locale : Python 3.11+, FFmpeg, pip

### Option 1 : Utiliser le serveur déjà déployé (recommandé)

✅ **Déjà live à :** `https://audio-compression.onrender.com`

Vérifier l'état :
```bash
curl https://audio-compression.onrender.com/health
# Réponse: {"status":"ok"}
```

### Option 2 : Déployer votre propre instance sur Render

1. Fork le repo GitHub
2. Sur Render.com → **New Web Service**
3. Connecter votre repo
4. Paramètres Render :
   - **Runtime** : Docker
   - **Build Command** : `docker build -t audio-compression .`
   - **Start Command** : Render détecte automatiquement
   - **Port** : 5000
5. Cliquer **Deploy** (5-10 min)

### Option 3 : Exécuter localement

```bash
# 1. Cloner le repo
git clone https://github.com/zakariko-sys/audio-compression.git
cd audio-compression

# 2. Créer un venv
python -m venv .venv
.venv\Scripts\activate  # Windows
# ou
source .venv/bin/activate  # macOS/Linux

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Installer FFmpeg
# Windows : https://ffmpeg.org/download.html
# macOS : brew install ffmpeg
# Linux : sudo apt-get install ffmpeg

# 5. Lancer le serveur
python api_agent.py
# Serveur écoute sur http://localhost:5000
```

---

## 🚀 Utilisation

### Importer le workflow n8n

1. Ouvrir **n8n** (version cloud ou locale)
2. Créer un nouveau workflow
3. Suivre la structure standard :
   - **Audio File Input Form** (fichier upload)
   - **Call Upload API** → `/api/upload`
   - **Call Analyser API** → `/api/analyser`
   - **Call Decision API** → `/api/decider`
   - **Call Compression API** → `/api/compresser`
   - **Call Evaluation API** → `/api/evaluer`
   - **Code (JavaScript)** → générer rapport
   - **Convert to File** → télécharger PDF/TXT

### Configurations n8n importantes

#### Timeouts (par nœud HTTP)
| Nœud | Timeout (ms) |
|---|---|
| Upload | 120000 |
| Analyser | 300000 |
| Decider | 60000 |
| Compresser | 300000 |
| Evaluer | 300000 |

#### Retry Policy
- **Retry On Fail** : OUI
- **Max Tries** : 2-3
- **Wait Between Tries** : 2000-5000 ms

#### Form Fields (Audio File Input Form)
- **fichier** (type: File Upload, required: yes)

#### Body Field Mapping (Call Upload API)
- **Type** : Form-Data
- **Field Name** : `fichier`
- **Field Type** : n8n Binary File
- **Value Source** : binaire depuis le formulaire

---

## 🛠️ Dépannage

| Problème | Cause | Solution |
|---|---|---|
| Erreur `source.on is not a function` | Fichier envoyé en JSON au lieu de binaire | Passer le champ `fichier` en type **n8n Binary File**, pas expression |
| Timeout 300000 dépassé | Cold start Render ou traitement audio long | Augmenter timeout à 600000 ms ; ajouter retries |
| Fichier compressé plus grand que l'original | Codec overhead (re-encodage d'MP3/AAC) | Le système détecte et garde l'original automatiquement (`taux_compression: 0`) |
| API répond `404 Not Found` | URL base API incorrecte | Vérifier `https://audio-compression.onrender.com` |
| `ECONNREFUSED` dans n8n | Serveur Render suspendu (inactivité) | Attendre 30s, retry ; ou garder warm avec requête `/health` périodique |

---

## 📁 Structure du projet

```
audio-compression/
├── api_agent.py              # Flask server + 5 endpoints
├── analyse_agent.py          # Audio spectral analysis (librosa)
├── agent_decision.py         # Codec/bitrate decision (heuristics)
├── agent_compresseur.py      # Audio compression (pydub + FFmpeg)
├── agent_evaluateur.py       # Quality metrics (SNR/PSNR/MSE)
├── compression_utils.py      # Codec-specific encoding functions
├── metrics.py                # MSE/SNR/PSNR calculations
├── requirements.txt          # Python dependencies
├── Dockerfile                # Docker build config
├── .dockerignore             # Files excluded from Docker
├── .gitignore                # Git-ignored files
└── README.md                 # This file
```

---

## 📊 Décision d'encodage (heuristiques)

| Contenu Détecté | Codec | Débit | Mode | Raison |
|---|---|---|---|---|
| **Parole** | Opus | 32-64 kbps | VBR | Très efficace sur voix |
| **Musique** | AAC | 96-128 kbps | VBR | Meilleure qualité que MP3 |
| **Signal Tonal** (bips) | Opus | 40-56 kbps | VBR | Excellent sur synthétique |
| **Mixte** | OGG Vorbis | 80-112 kbps | VBR | Bon compromis libre |
| **Inconnu** | MP3 | 64-128 kbps | VBR | Compatible universellement |
| **Source sans perte** | FLAC | - | Lossless | Préserve qualité originale |

---

## 🔄 Déploiement & CI/CD

**Workflow automatique :**

1. Push vers GitHub (`main` branch)
2. Render détecte le commit
3. Render rebuild le Docker image
4. Test sur port 5000
5. Nouvelle version live en ~3-5 minutes

**Fichiers critiques :**
- `Dockerfile` → instructions build
- `requirements.txt` → dépendances Python
- `.dockerignore` → exclure fichiers volumineux (audio, venv)

---

## 📝 Notes

- **Serveur gratuit Render** : peut avoir un "cold start" après 15min d'inactivité → ajuster timeouts n8n à 300-600s
- **Fichiers temporaires** : stockés dans `/tmp/audio_api_store`, nettoyés automatiquement après chaque requête upload
- **Limite de taille** : pas de limite programmée, mais respecter limites Render (disque, mémoire)
- **Authentification** : actuellement aucune ; ajouter Bearer token sur demande

---

## 📄 Licence

MIT License - Voir [LICENSE](LICENSE) pour les détails.

---

## 👨‍💻 Auteur

Zakariko-sys  
[GitHub Profile](https://github.com/zakariko-sys)

---

**Questions ou issues ?** Open an issue sur GitHub.
