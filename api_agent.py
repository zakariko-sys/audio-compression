import os
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime

from flask import Flask, request, jsonify

from analyse_agent import AgentAnalyse
from agent_compresseur import CompressorAgent
from agent_decision import decider_compression
from agent_evaluateur import EvaluatorAgent

app = Flask(__name__)


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
    extensions = {
        "mp3": ".mp3",
        "aac": ".aac",
        "opus": ".opus",
        "ogg": ".ogg",
        "ogg_vorbis": ".ogg",
        "flac": ".flac",
    }
    extension = extensions.get(codec, f".{codec}")
    return f"{base}_compresse{extension}"


def _resoudre_fichier_input(donnees):
    """
    Accepte soit:
    - chemin_fichier local sur le serveur
    - file_url (http/https), téléchargé dans un fichier temporaire

    Retourne (chemin_local, est_temporaire)
    """
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
        
        agent = AgentAnalyse()
        resultat = agent.analyser(chemin_fichier)
        
        return jsonify({
            "success": True,
            "analyse": resultat.vers_dictionnaire()
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

        audio_path = donnees.get("audio_path") or analyse.get("chemin_fichier")
        codec = donnees.get("codec") or decision.get("codec")
        bitrate = donnees.get("bitrate") or decision.get("debit_kbps")
        output_path = donnees.get("output_path")

        if not output_path and audio_path and codec:
            output_path = _construire_sortie_par_defaut(audio_path, codec)

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

        original_path = donnees.get("original_path") or analyse.get("chemin_fichier")
        compressed_path = donnees.get("compressed_path") or compression.get("fichier_compressé")

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

    Body:
    {
      "chemin_fichier": "d:/Agent_dec/test_tone.wav",
      "output_path": "d:/Agent_dec/sortie.opus"  # optionnel
    }
    """
    try:
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
