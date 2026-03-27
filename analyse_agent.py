from __future__ import annotations

import argparse
import json
import math
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict

import librosa
import numpy as np
import soundfile as sf


@dataclass(frozen=True)
class ResultatAnalyse:
    duree_s: float
    taux_echantillonnage_hz: int
    canaux: int
    probabilite_parole: float
    probabilite_musique: float
    lufs_integre: float
    crete_vrai_dbfs: float
    facteur_crete_db: float
    codec_source: str
    debit_source_kbps: int
    extras: Dict[str, Any] = field(default_factory=dict)

    def vers_dictionnaire(self) -> Dict[str, Any]:
        donnees = asdict(self)
        extras = donnees.pop("extras", {})
        donnees.update(extras)
        return donnees

    def vers_json(self, *, indentation: int = 2) -> str:
        return json.dumps(self.vers_dictionnaire(), ensure_ascii=False, indent=indentation)


class AgentAnalyse:
    """Analyse un fichier audio et produit un JSON compatible avec agent_decision.py."""

    def analyser(self, chemin_fichier: str) -> ResultatAnalyse:
        if not os.path.exists(chemin_fichier):
            raise FileNotFoundError(f"Fichier introuvable : {chemin_fichier}")

        info = sf.info(chemin_fichier)
        signal, taux_echantillonnage = librosa.load(chemin_fichier, sr=None, mono=False)
        signal = np.asarray(signal, dtype=np.float32)

        if signal.ndim == 1:
            canaux = 1
            signal_mono = signal
        else:
            canaux = int(signal.shape[0])
            signal_mono = np.mean(signal, axis=0)

        duree_s = float(librosa.get_duration(y=signal_mono, sr=taux_echantillonnage))
        taille_fichier_octets = os.path.getsize(chemin_fichier)
        debit_source_kbps = self._estimer_debit_kbps(taille_fichier_octets, duree_s)

        zcr = float(np.mean(librosa.feature.zero_crossing_rate(signal_mono)))
        rms = float(np.mean(librosa.feature.rms(y=signal_mono)))

        try:
            tempo = float(librosa.feature.rhythm.tempo(y=signal_mono, sr=taux_echantillonnage)[0])
        except Exception:
            tempo = 0.0

        spectral_centroid = float(
            np.mean(librosa.feature.spectral_centroid(y=signal_mono, sr=taux_echantillonnage))
        )
        spectral_bandwidth = float(
            np.mean(librosa.feature.spectral_bandwidth(y=signal_mono, sr=taux_echantillonnage))
        )
        spectral_rolloff = float(
            np.mean(librosa.feature.spectral_rolloff(y=signal_mono, sr=taux_echantillonnage))
        )

        stft = np.abs(librosa.stft(signal_mono))
        stft_normalise = stft / (np.sum(stft) + 1e-10)
        entropie_spectrale = float(-np.sum(stft_normalise * np.log2(stft_normalise + 1e-10)))

        probabilite_parole, probabilite_musique, etiquette_contenu = self._estimer_probabilites(
            zcr=zcr,
            rms=rms,
            tempo=tempo,
            spectral_centroid=spectral_centroid,
            spectral_bandwidth=spectral_bandwidth,
            entropie_spectrale=entropie_spectrale,
        )

        crete = float(np.max(np.abs(signal_mono)))
        crete_vrai_dbfs = self._amplitude_vers_dbfs(crete)
        rms_dbfs = self._amplitude_vers_dbfs(rms)
        facteur_crete_db = round(max(0.0, crete_vrai_dbfs - rms_dbfs), 2)
        lufs_integre = round(rms_dbfs, 2)

        codec_source = self._normaliser_codec_source(info)

        extras = {
            "chemin_fichier": chemin_fichier,
            "nom_fichier": os.path.basename(chemin_fichier),
            "taille_fichier_mb": round(taille_fichier_octets / 1_000_000, 3),
            "tempo_bpm": round(tempo, 1),
            "zero_crossing_rate": round(zcr, 5),
            "rms_energie": round(rms, 5),
            "spectral_centroid_hz": round(spectral_centroid, 1),
            "spectral_bandwidth_hz": round(spectral_bandwidth, 1),
            "spectral_rolloff_hz": round(spectral_rolloff, 1),
            "entropie_spectrale": round(entropie_spectrale, 3),
            "etiquette_contenu": etiquette_contenu,
            "format_source": info.format,
            "sous_type_source": info.subtype,
        }

        return ResultatAnalyse(
            duree_s=round(duree_s, 2),
            taux_echantillonnage_hz=int(taux_echantillonnage),
            canaux=canaux,
            probabilite_parole=probabilite_parole,
            probabilite_musique=probabilite_musique,
            lufs_integre=lufs_integre,
            crete_vrai_dbfs=round(crete_vrai_dbfs, 2),
            facteur_crete_db=facteur_crete_db,
            codec_source=codec_source,
            debit_source_kbps=debit_source_kbps,
            extras=extras,
        )

    @staticmethod
    def _estimer_debit_kbps(taille_fichier_octets: int, duree_s: float) -> int:
        if duree_s <= 0:
            return 0
        return int(round((taille_fichier_octets * 8) / 1000 / duree_s))

    @staticmethod
    def _amplitude_vers_dbfs(valeur: float) -> float:
        return float(20 * math.log10(max(valeur, 1e-10)))

    @staticmethod
    def _normaliser_codec_source(info: sf.SoundFile) -> str:
        format_source = (info.format or "").lower()
        sous_type = (info.subtype or "").lower()

        if format_source == "wav" and sous_type.startswith("pcm_"):
            return sous_type
        if format_source == "flac":
            return "flac"
        if format_source == "ogg":
            return "ogg_vorbis"
        if format_source == "mp3":
            return "mp3"
        if format_source in {"m4a", "mp4"}:
            return "aac"
        return format_source or sous_type or "inconnu"

    @staticmethod
    def _estimer_probabilites(
        *,
        zcr: float,
        rms: float,
        tempo: float,
        spectral_centroid: float,
        spectral_bandwidth: float,
        entropie_spectrale: float,
    ) -> tuple[float, float, str]:
        # Détection précoce d'un signal tonal (bip/sinus): bande étroite + faible entropie + pas de rythme.
        if (
            tempo < 20
            and spectral_bandwidth < 500
            and entropie_spectrale < 8.0
            and 0.005 <= zcr <= 0.08
        ):
            return 0.0, 0.0, "signal tonal"

        score_parole = 0.0
        score_musique = 0.0

        if zcr >= 0.08:
            score_parole += 0.35
        if 0.01 <= rms <= 0.12:
            score_parole += 0.15
        if tempo < 70:
            score_parole += 0.25
        if spectral_centroid < 2200:
            score_parole += 0.15

        if tempo >= 80:
            score_musique += 0.35
        if spectral_centroid >= 1800:
            score_musique += 0.25
        if spectral_bandwidth >= 1500:
            score_musique += 0.20
        if rms >= 0.02:
            score_musique += 0.10

        score_parole = min(score_parole, 0.95)
        score_musique = min(score_musique, 0.95)

        if score_parole == 0 and score_musique == 0:
            return 0.0, 0.0, "inconnu"

        total = score_parole + score_musique
        probabilite_parole = round(score_parole / total, 3)
        probabilite_musique = round(score_musique / total, 3)

        if probabilite_parole >= 0.6:
            etiquette = "parole"
        elif probabilite_musique >= 0.6:
            etiquette = "musique"
        else:
            etiquette = "mixte"

        return probabilite_parole, probabilite_musique, etiquette


def sauvegarder_analyse_json(resultat: ResultatAnalyse, chemin_sortie: str) -> None:
    with open(chemin_sortie, "w", encoding="utf-8") as fichier:
        fichier.write(resultat.vers_json(indentation=2))
        fichier.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyse un fichier audio et produit un JSON compatible avec agent_decision.py."
    )
    parser.add_argument("fichier_audio", type=str, help="Chemin vers le fichier audio à analyser")
    parser.add_argument(
        "--sortie-json",
        type=str,
        default="analyse_sortie.json",
        help="Chemin du fichier JSON de sortie",
    )
    args = parser.parse_args()

    agent = AgentAnalyse()
    resultat = agent.analyser(args.fichier_audio)
    sauvegarder_analyse_json(resultat, args.sortie_json)
    print(resultat.vers_json(indentation=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())