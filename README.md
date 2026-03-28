# 🎵 Audio Compression Multi-Agent

A multi-agent orchestration system for intelligent audio compression, deployed on cloud with n8n as workflow orchestrator.

---

## 📦 Prerequisites & Required Libraries

### On the Laptop Running the Workflow (n8n)

**Minimum Requirements:**
- **n8n** (Cloud version at `app.n8n.cloud` or self-hosted)
- **Internet connection** (to reach `https://audio-compression.onrender.com`)
- **Web browser** (modern, JavaScript enabled)
- **No local Python required** (all processing happens on the server)
- **No FFmpeg required locally** (installed on Render server)

**Browser compatibility:**
- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Server-Side (Render) - Already Installed

The deployed API server includes all required dependencies automatically:

```
flask==3.0.3              # Web framework
gunicorn==22.0.0          # Production server
numpy==2.1.3              # Numerical computations
librosa==0.10.2.post1     # Audio analysis
soundfile==0.13.1         # Audio file reading
pydub==0.25.1             # Audio compression
ffmpeg                    # Audio codec processing (system package)
libsndfile1               # Audio library (system package)
```

**Note:** All these come from [requirements.txt](requirements.txt) and are automatically installed via the [Dockerfile](Dockerfile).

---

## 🚀 Utilisation

### Step 1: Access n8n
Open your n8n instance (Cloud or self-hosted) and navigate to your audio compression workflow.

### Step 2: Upload Audio File
1. Click on **Audio File Input Form** node
2. Open the form URL displayed
3. Select an audio file from your laptop (WAV, MP3, AAC, FLAC, Opus, OGG supported)
4. Click **Submit**

### Step 3: Monitor Execution
The workflow automatically sequences through:
1. Upload API → stores file on server, returns `file_id`
2. Analyser API → extracts audio features
3. Decision API → chooses optimal codec/bitrate
4. Compresser API → compresses the file
5. Evaluator API → measures quality (SNR, PSNR, MSE)
6. Report Generation → consolidates results
7. File Output → ready for download

### Step 4: Download Results
After completion, a report file (TXT/JSON) is available for download containing:
- Original file size
- Compressed file size
- Compression ratio
- Codec used
- Quality metrics
- Recommendations

---

## 🔄 Retry Policies

### Automatic Retry Configuration (n8n)

Each HTTP API call is configured with automatic retry to handle transient failures and Render cold starts.

**Global Retry Settings (apply to all API nodes):**

```
Retry On Fail: ENABLED
Max Tries: 2
Wait Between Tries: 2000 ms (2 seconds)
```

**Per-Node Retry Behavior:**

| API Node | Retry Enabled | Max Attempts | Wait (ms) |
|---|---|---|---|
| Call Upload API | Yes | 2 | 2000 |
| Call Analyser API | Yes | 2 | 2000 |
| Call Decision API | Yes | 2 | 2000 |
| Call Compresser API | Yes | 2 | 2000 |
| Call Evaluation API | Yes | 2 | 2000 |

**How It Works:**
1. If an API call fails (timeout, 5xx error, connection refused), n8n waits 2 seconds
2. Retries the exact same request
3. If still fails on 2nd attempt, error node is triggered
4. Workflow stops with error message displayed to user

**Why Retry?**
- Render free tier may have "cold start" delays (first call after idle)
- Temporary network hiccups
- Server processing large audio files (auto-retry gives more time)

**Manual Intervention:**
If all retries fail, check:
1. Internet connection
2. Render server status: `https://audio-compression.onrender.com/health`
3. Audio file size (very large files may need longer processing)
4. Try again manually (server may have recovered)

---

## 👨‍💻 Authors

- **Zakaria Ouaidrari**
- **Sabar Meriem**
- **Lahrich Mohamed**
- **Nouhaila Outaararate**

---

## 📝 Notes

- **No installation required on your laptop** for workflow execution
- **Server handles all heavy lifting** (FFmpeg, audio analysis, compression)
- **Automatic retry logic** ensures robustness against transient failures
- **Report generation** is automatic and includes all metrics

---

**API Base URL:** `https://audio-compression.onrender.com`

**Documentation:** See main [README.md](README.md) for full architecture, endpoints, and troubleshooting.
