import os
import glob
import tempfile
import urllib.parse
import urllib.request
import uuid
from datetime import datetime

from flask import Flask, request, jsonify

from analyse_agent import AgentAnalyse
from agent_compresseur import CompressorAgent
from agent_decision import decider_compression
from agent_evaluateur import EvaluatorAgent

app = Flask(__name__)

STORAGE_DIR = os.path.join(tempfile.gettempdir(), "audio_api_store")


def _get_storage_dir():
    os.makedirs(STORAGE_DIR, exist_ok=True)
    return STORAGE_DIR


def _nouveau_file_id():
    return uuid.uuid4().hex


def _extension_pour_codec(codec):
    extensions = {
        "mp3": ".mp3",
        "aac": ".aac",
        "opus": ".opus",
        "ogg": ".ogg",
        "ogg_vorbis": ".ogg",
        "flac": ".flac",
    }
    return extensions.get(codec, f".{codec}")


def _resoudre_path_par_file_id(file_id):
    if not file_id:
        raise ValueError("file_id est requis")

    file_id = str(file_id).strip()
    if not file_id:
        raise ValueError("file_id invalide")

    pattern = os.path.join(_get_storage_dir(), f"{file_id}.*")
    matches = glob.glob(pattern)
    if not matches:
        raise ValueError(f"Aucun fichier trouve pour file_id={file_id}")

    return matches[0]


def _sauvegarder_upload(uploaded_file):
    if uploaded_file is None:
        raise ValueError("Le champ fichier est requis")

    original_name = uploaded_file.filename or "audio"
    extension = os.path.splitext(original_name)[1] or ".audio"
    file_id = _nouveau_file_id()
    output_path = os.path.join(_get_storage_dir(), f"{file_id}{extension}")
    uploaded_file.save(output_path)
    return file_id, output_path


def _extraire_analyse(donnees):
    if isinstance(donnees, dict) and isinstance(donnees.get("analyse"), dict):
        return donnees["analyse"]
    return donnees


def _extraire_decision(donnees):
    if isinstance(donnees, dict) and isinstance(donnees.get("decision"), dict):
        return donnees["decision"]
    return donnees


def _construire_sortie_par_defaut(audio_path, codec):
    base, _ = os.path.splitext(audio_path)
    extension = _extension_pour_codec(codec)
    return f"{base}_compresse{extension}"


def _resoudre_fichier_input(donnees):
    """
    Accepte soit:
    - chemin_fichier local sur le serveur
    - file_url (http/https), téléchargé dans un fichier temporaire

    Retourne (chemin_local, est_temporaire)
    """
    file_id = donnees.get("file_id")
    if file_id:
        return _resoudre_path_par_file_id(file_id), False

    chemin_fichier = donnees.get("chemin_fichier")
    if chemin_fichier:
        return chemin_fichier, False

    file_url = donnees.get("file_url")
    if not file_url:
        raise ValueError("chemin_fichier ou file_url est requis")

    parsed = urllib.parse.urlparse(file_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("file_url doit utiliser http ou https")

    extension = os.path.splitext(parsed.path)[1] or ".audio"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
    temp_file.close()
    urllib.request.urlretrieve(file_url, temp_file.name)
    return temp_file.name, True


def _construire_resultat_consolide(*, audio_path, analyse_raw, decision_raw, compression_raw, evaluation_raw):
    analyse = analyse_raw.get("analyse", {}) if isinstance(analyse_raw, dict) else {}
    decision = decision_raw.get("decision", {}) if isinstance(decision_raw, dict) else {}
    evaluation = evaluation_raw.get("evaluation", {}) if isinstance(evaluation_raw, dict) else {}

    workflow_success = all(
        isinstance(payload, dict) and payload.get("success") is True
        for payload in (analyse_raw, decision_raw, compression_raw, evaluation_raw)
    )

    return {
        "consolidated_result": {
            "metadata": {
                "workflow_status": "SUCCESS" if workflow_success else "FAILED",
                "audio_path": audio_path,
                "timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
                "notes": "Consolidated multi-agent result",
            },
            "analyse_agent": {
                "label": "Agent 1 - Audio Analysis",
                "meaning": "Extracts audio characteristics and content hints",
                "raw": analyse_raw,
            },
            "decision_agent": {
                "label": "Agent 2 - Compression Decision",
                "meaning": "Chooses codec/bitrate/mode from analysis",
                "raw": decision_raw,
            },
            "compression_agent": {
                "label": "Agent 3 - Audio Compression",
                "meaning": "Applies compression with selected codec settings",
                "raw": compression_raw,
            },
            "evaluation_agent": {
                "label": "Agent 4 - Quality Evaluation",
                "meaning": "Measures quality/compression tradeoff after processing",
                "raw": evaluation_raw,
            },
            "interpretation": {
                "selected_codec": decision.get("codec"),
                "selected_bitrate_kbps": decision.get("debit_kbps"),
                "quality_label": evaluation.get("qualite"),
                "quality_level": evaluation.get("niveau"),
                "conclusion": evaluation.get("conclusion"),
            },
        }
    }


@app.route("/api/upload", methods=["POST"])
def upload_audio():
    """
    Upload un fichier audio une seule fois et retourne un file_id.

    Form-data:
    - fichier: binaire du fichier audio
    """
    try:
        if "fichier" not in request.files:
            return jsonify({"success": False, "error": "Le champ fichier est requis"}), 400

        file_id, output_path = _sauvegarder_upload(request.files["fichier"])
        size_bytes = os.path.getsize(output_path)
        return jsonify(
            {
                "success": True,
                "file_id": file_id,
                "stored_path": output_path,
                "size_bytes": size_bytes,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/analyser", methods=["POST"])
def analyser():
    """
    Reçoit un chemin de fichier audio, analyse, et retourne JSON.
    
    Body:
    {
      "chemin_fichier": "d:/Agent_dec/aeiou.wav"
    }
    """
    try:
        donnees = request.get_json() or {}
        chemin_fichier, est_temporaire = _resoudre_fichier_input(donnees)
        file_id = donnees.get("file_id")
        
        agent = AgentAnalyse()
        resultat = agent.analyser(chemin_fichier)
        analyse_dict = resultat.vers_dictionnaire()
        if file_id:
            analyse_dict["file_id"] = file_id
        
        return jsonify({
            "success": True,
            "analyse": analyse_dict
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
    finally:
        try:
            if "est_temporaire" in locals() and est_temporaire and os.path.exists(chemin_fichier):
                os.remove(chemin_fichier)
        except Exception:
            pass

@app.route("/api/decider", methods=["POST"])
def decider():
    """
    Reçoit l'analyse JSON et retourne la décision de compression.
    
    Body: (l'analyse JSON complète)
    {
      "duree_s": 183.2,
      "canaux": 2,
      "probabilite_parole": 0.15,
      "probabilite_musique": 0.85,
      ...
    }
    """
    try:
        donnees = request.get_json() or {}
        analyse = _extraire_analyse(donnees)
        decision = decider_compression(analyse)
        
        return jsonify({
            "success": True,
            "decision": {
                "codec": decision.codec,
                "debit_kbps": decision.debit_kbps,
                "mode": decision.mode,
                "justification": decision.justification,
                "raisonnement": decision.raisonnement,
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/compresser", methods=["POST"])
def compresser():
    """
    Reçoit les paramètres de compression et retourne le résultat du compresseur.

    Body:
    {
      "audio_path": "...",
      "output_path": "...",
      "codec": "aac",
      "bitrate": 128
    }
    """
    try:
        donnees = request.get_json() or {}
        analyse = _extraire_analyse(donnees)
        decision = _extraire_decision(donnees)

        file_id = donnees.get("file_id") or analyse.get("file_id")
        audio_path = donnees.get("audio_path") or analyse.get("chemin_fichier")
        if not audio_path and file_id:
            audio_path = _resoudre_path_par_file_id(file_id)

        codec = donnees.get("codec") or decision.get("codec")
        bitrate = donnees.get("bitrate") or decision.get("debit_kbps")
        output_path = donnees.get("output_path")
        output_file_id = donnees.get("output_file_id")

        if not output_path and codec:
            if not output_file_id:
                output_file_id = _nouveau_file_id()
            output_path = os.path.join(_get_storage_dir(), f"{output_file_id}{_extension_pour_codec(codec)}")

        if not output_path and audio_path and codec:
            output_path = _construire_sortie_par_defaut(audio_path, codec)

        if not output_file_id and output_path:
            basename = os.path.basename(output_path)
            output_file_id = os.path.splitext(basename)[0]

        if not audio_path or not output_path or not codec:
            return jsonify({
                "success": False,
                "error": "audio_path, output_path et codec sont requis",
            }), 400

        agent = CompressorAgent()
        resultat = agent.compresser(
            audio_path=audio_path,
            output_path=output_path,
            codec=codec,
            bitrate=bitrate,
        )
        resultat["output_file_id"] = output_file_id
        return jsonify({"success": True, "compression": resultat})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/evaluer", methods=["POST"])
def evaluer():
    """
    Reçoit les chemins original/compressé et retourne les métriques d'évaluation.

    Body:
    {
      "original_path": "...",
      "compressed_path": "..."
    }
    """
    try:
        donnees = request.get_json() or {}
        analyse = _extraire_analyse(donnees)
        compression = donnees.get("compression") if isinstance(donnees.get("compression"), dict) else {}

        original_file_id = donnees.get("original_file_id") or donnees.get("file_id") or analyse.get("file_id")
        compressed_file_id = donnees.get("compressed_file_id") or compression.get("output_file_id")

        original_path = donnees.get("original_path") or analyse.get("chemin_fichier")
        if not original_path and original_file_id:
            original_path = _resoudre_path_par_file_id(original_file_id)

        compressed_path = donnees.get("compressed_path") or compression.get("fichier_compressé")
        if not compressed_path and compressed_file_id:
            compressed_path = _resoudre_path_par_file_id(compressed_file_id)

        if not original_path or not compressed_path:
            return jsonify({
                "success": False,
                "error": "original_path et compressed_path sont requis",
            }), 400

        agent = EvaluatorAgent()
        resultat = agent.evaluer(original_path, compressed_path)
        if "erreur" in resultat:
            return jsonify({"success": False, "error": resultat["erreur"]}), 400
        return jsonify({"success": True, "evaluation": resultat})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/orchestrer", methods=["POST"])
def orchestrer():
    """
    Exécute le pipeline complet en une seule requête:
    analyse -> décision -> compression -> évaluation

    Accepte soit:
    - multipart/form-data avec champ "fichier" (upload direct depuis n8n)
    - JSON avec "file_url" (URL publique)
    - JSON avec "chemin_fichier" (chemin local sur le serveur)
    """
    try:
        if request.files.get("fichier"):
            f = request.files["fichier"]
            ext = os.path.splitext(f.filename)[1] if f.filename else ".audio"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            f.save(tmp.name)
            tmp.close()
            chemin_fichier = tmp.name
            est_temporaire = True
            donnees = request.form.to_dict()
        else:
            donnees = request.get_json() or {}
            chemin_fichier, est_temporaire = _resoudre_fichier_input(donnees)

        # 1) Analyse
        agent_analyse = AgentAnalyse()
        analyse_resultat = agent_analyse.analyser(chemin_fichier)
        analyse_raw = {"success": True, "analyse": analyse_resultat.vers_dictionnaire()}

        # 2) Décision
        decision = decider_compression(analyse_raw["analyse"])
        decision_raw = {
            "success": True,
            "decision": {
                "codec": decision.codec,
                "debit_kbps": decision.debit_kbps,
                "mode": decision.mode,
                "justification": decision.justification,
                "raisonnement": decision.raisonnement,
            },
        }

        # 3) Compression
        codec = decision_raw["decision"]["codec"]
        output_path = donnees.get("output_path") or _construire_sortie_par_defaut(chemin_fichier, codec)

        agent_compresseur = CompressorAgent()
        compression = agent_compresseur.compresser(
            audio_path=chemin_fichier,
            output_path=output_path,
            codec=codec,
            bitrate=decision_raw["decision"].get("debit_kbps"),
        )
        compression_raw = {"success": True, "compression": compression}

        # 4) Évaluation
        agent_evaluateur = EvaluatorAgent()
        evaluation = agent_evaluateur.evaluer(chemin_fichier, compression.get("fichier_compressé"))
        if "erreur" in evaluation:
            return jsonify({"success": False, "error": evaluation["erreur"]}), 400
        evaluation_raw = {"success": True, "evaluation": evaluation}

        # Consolidation orchestrateur
        return jsonify(
            _construire_resultat_consolide(
                audio_path=chemin_fichier,
                analyse_raw=analyse_raw,
                decision_raw=decision_raw,
                compression_raw=compression_raw,
                evaluation_raw=evaluation_raw,
            )
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
    finally:
        try:
            if "est_temporaire" in locals() and est_temporaire:
                if os.path.exists(chemin_fichier):
                    os.remove(chemin_fichier)
                # Le compresseur crée un fichier de sortie; le supprimer aussi en mode fichier temporaire.
                if "output_path" in locals() and output_path and os.path.exists(output_path):
                    os.remove(output_path)
        except Exception:
            pass

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
