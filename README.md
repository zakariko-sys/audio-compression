# 🎵 Audio Compression Multi-Agent

Systeme multi-agent de compression audio intelligente, orchestre avec n8n et deploye sur Render.

---

## 📦 Prerequis et dependances

### Sur le PC portable qui execute le workflow

Exigences minimales:
- n8n (Cloud sur `app.n8n.cloud` ou self-hosted)
- Connexion Internet (pour appeler `https://audio-compression.onrender.com`)
- Navigateur web moderne
- Aucun Python local requis
- Aucun FFmpeg local requis

Compatibilite navigateur:
- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Dependances cote serveur (deja installees sur Render)

```
flask==3.0.3
gunicorn==22.0.0
numpy==2.1.3
librosa==0.10.2.post1
soundfile==0.13.1
pydub==0.25.1
ffmpeg
libsndfile1
```

Ces dependances sont installees automatiquement via [requirements.txt](requirements.txt) et [Dockerfile](Dockerfile).

---

## 🚀 Utilisation

### Etape 1: Importer le workflow JSON dans n8n
1. Ouvrir n8n
2. Creer un nouveau workflow
3. Importer le fichier JSON du workflow
4. Sauvegarder le workflow importe

### Etape 2: Envoyer un fichier audio
1. Ouvrir le noeud **Audio File Input Form**
2. Ouvrir l'URL du formulaire
3. Selectionner un fichier audio depuis le PC (WAV, MP3, AAC, FLAC, Opus, OGG)
4. Cliquer sur **Submit**

### Etape 3: Traitement automatique
Le workflow enchaine automatiquement:
1. Upload API -> stocke le fichier et renvoie `file_id`
2. Analyser API -> extrait les caracteristiques audio
3. Decision API -> choisit codec/debit
4. Compresser API -> compresse le fichier
5. Evaluer API -> calcule MSE, SNR, PSNR
6. Generation du rapport
7. Conversion en fichier de sortie

### Etape 4: Recuperer les resultats
A la fin, un rapport est disponible au telechargement avec:
- Taille originale
- Taille compressee
- Taux de compression
- Codec choisi
- Metriques de qualite

---

## 🔄 Politique de retry

Configuration recommandee dans n8n (pour chaque noeud HTTP API):

```
Retry On Fail: ENABLED
Max Tries: 2
Wait Between Tries: 2000 ms
```

Application par noeud:

| Noeud API | Retry active | Nombre max de tentatives | Attente |
|---|---|---|---|
| Call Upload API | Oui | 2 | 2000 ms |
| Call Analyser API | Oui | 2 | 2000 ms |
| Call Decision API | Oui | 2 | 2000 ms |
| Call Compresser API | Oui | 2 | 2000 ms |
| Call Evaluation API | Oui | 2 | 2000 ms |

Comportement:
1. Si un appel API echoue, n8n attend 2 secondes
2. n8n relance la meme requete automatiquement
3. Si le 2e essai echoue aussi, le workflow passe vers la branche d'erreur

---

## 👨‍💻 Auteurs

- Zakaria Ouaidrari
- Sabar Meriem
- Lahrich Mohamed
- Nouhaila Outaararate

---

## 📝 Notes

- Le traitement lourd est fait cote serveur
- Le workflow n8n sert d'orchestrateur
- Le rapport final est genere automatiquement

---

URL API:
`https://audio-compression.onrender.com`
