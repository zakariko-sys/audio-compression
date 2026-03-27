from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AnalyseAudio:
    """
    Structure de données minimale et flexible pour les caractéristiques audio
    produites par analyse.py. Les champs inconnus sont conservés dans `extras`.
    """

    duree_s: Optional[float] = None
    taux_echantillonnage_hz: Optional[int] = None
    canaux: Optional[int] = None

    # Indices de contenu (optionnel, si analyse.py peut les fournir)
    probabilite_parole: Optional[float] = None  # 0..1
    probabilite_musique: Optional[float] = None  # 0..1

    # Volume / dynamique (optionnel)
    lufs_integre: Optional[float] = None
    crete_vrai_dbfs: Optional[float] = None
    facteur_crete_db: Optional[float] = None

    # Indices d'encodage source (optionnel)
    codec_source: Optional[str] = None
    debit_source_kbps: Optional[int] = None

    extras: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def depuis_dictionnaire(m: Dict[str, Any]) -> "AnalyseAudio":
        connus = {}
        extras = dict(m)
        # Accepter les clés en anglais (rétrocompatibilité) ET en français
        correspondance = {
            "duration_s": "duree_s",
            "duree_s": "duree_s",
            "sample_rate_hz": "taux_echantillonnage_hz",
            "taux_echantillonnage_hz": "taux_echantillonnage_hz",
            "channels": "canaux",
            "canaux": "canaux",
            "speech_probability": "probabilite_parole",
            "probabilite_parole": "probabilite_parole",
            "music_probability": "probabilite_musique",
            "probabilite_musique": "probabilite_musique",
            "integrated_lufs": "lufs_integre",
            "lufs_integre": "lufs_integre",
            "true_peak_dbfs": "crete_vrai_dbfs",
            "crete_vrai_dbfs": "crete_vrai_dbfs",
            "crest_factor_db": "facteur_crete_db",
            "facteur_crete_db": "facteur_crete_db",
            "source_codec": "codec_source",
            "codec_source": "codec_source",
            "source_bitrate_kbps": "debit_source_kbps",
            "debit_source_kbps": "debit_source_kbps",
        }
        for cle_json, cle_champ in correspondance.items():
            if cle_json in extras:
                connus[cle_champ] = extras.pop(cle_json)
        return AnalyseAudio(**connus, extras=extras)


@dataclass(frozen=True)
class DecisionCompression:
    codec: str
    debit_kbps: int
    mode: str  # ex. "CBR" ou "VBR"
    justification: str
    raisonnement: Dict[str, Any] = field(default_factory=dict)

    def vers_json(self, *, indentation: int = 2) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=indentation)


# Codecs sources considérés comme sans perte.
_CODECS_SANS_PERTE = {
    "pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le",
    "pcm_s16be", "pcm_s24be", "pcm_s32be", "pcm_f32be",
    "wav", "flac", "alac", "aiff",
}


def _est_source_sans_perte(codec_source: Optional[str]) -> bool:
    """Vérifie si le codec source est un format sans perte."""
    if codec_source is None:
        return False
    return codec_source.lower() in _CODECS_SANS_PERTE


def _classifier_contenu(
    prob_parole: Optional[float], prob_musique: Optional[float]
) -> str:
    """Classifie le contenu : parole, musique, mixte ou inconnu."""
    if prob_parole is None and prob_musique is None:
        return "inconnu"
    p = prob_parole or 0.0
    m = prob_musique or 0.0
    if p >= max(m, 0.5):
        return "parole"
    if m >= max(p, 0.5):
        return "musique"
    return "mixte"


def decider_compression(entree_analyse: Dict[str, Any] | AnalyseAudio) -> DecisionCompression:
    """
    Agent de décision — choisit parmi 5 méthodes de compression :

    • MP3        – Compression avec pertes, compatibilité universelle
    • AAC        – Meilleure qualité que MP3 à débit égal
    • Opus       – Format moderne, excellent pour la voix
    • OGG Vorbis – Alternative libre au MP3
    • FLAC       – Compression sans perte

    La décision est basée sur les caractéristiques audio fournies.
    """
    analyse = (
        entree_analyse
        if isinstance(entree_analyse, AnalyseAudio)
        else AnalyseAudio.depuis_dictionnaire(entree_analyse)
    )

    prob_parole = analyse.probabilite_parole
    prob_musique = analyse.probabilite_musique

    # Priorité au hint explicite de l'analyseur quand il existe.
    etiquette_analyse = str(analyse.extras.get("etiquette_contenu", "")).lower()
    if etiquette_analyse in {"signal_tonal", "signal-tonal", "signal tonal", "tonal", "beep", "bip"}:
        type_contenu = "signal_tonal"
    else:
        type_contenu = _classifier_contenu(prob_parole, prob_musique)
    canaux = analyse.canaux or 2
    crete = analyse.facteur_crete_db
    debit_src = analyse.debit_source_kbps
    taux_ech = analyse.taux_echantillonnage_hz or 44100
    source_sans_perte = _est_source_sans_perte(analyse.codec_source)

    # ── Arbre de décision ────────────────────────────────────────────
    #
    # 1. FLAC : source sans perte + audio riche en dynamique ou haute résolution
    #    → Conserver la qualité originale intacte.
    if source_sans_perte and (
        (crete is not None and crete >= 14) or taux_ech >= 96000
    ):
        codec = "flac"
        mode = "sans_perte"
        debit = 0  # variable, déterminé par le contenu

    # 2. Source déjà compressée à bas débit → MP3
    #    Pas besoin d'un codec avancé, miser sur la compatibilité maximale.
    elif not source_sans_perte and debit_src is not None and debit_src <= 128:
        codec = "mp3"
        mode = "CBR"
        debit = min(debit_src, 128)

    # 3. Parole → Opus
    #    Le codec le plus efficace pour la voix, très bas débit possible.
    elif type_contenu == "parole":
        codec = "opus"
        mode = "VBR"
        debit = 32 if canaux == 1 else 64

    # 4. Musique → AAC
    #    Meilleure fidélité avec pertes que MP3, large compatibilité.
    elif type_contenu == "musique":
        codec = "aac"
        mode = "VBR"
        debit = 128 if canaux >= 2 else 96

    # 5. Signal tonal (bips/sinus) → Opus bas débit
    #    Très efficace sur ce type de signal synthétique.
    elif type_contenu == "signal_tonal":
        codec = "opus"
        mode = "VBR"
        debit = 40 if canaux == 1 else 56

    # 6. Mixte → OGG Vorbis
    #    Bon compromis libre entre parole et musique.
    elif type_contenu == "mixte":
        codec = "ogg_vorbis"
        mode = "VBR"
        debit = 112 if canaux >= 2 else 80

    # 7. Inconnu → MP3
    #    Compatibilité universelle comme choix sûr par défaut.
    else:
        codec = "mp3"
        mode = "VBR"
        debit = 128 if canaux >= 2 else 64

    # ── Ajustements post-décision (codecs avec pertes uniquement) ────
    if mode != "sans_perte":
        # Dynamique riche → augmenter le débit pour préserver les transitoires.
        if crete is not None and crete >= 14:
            debit = int(round(debit * 1.25))

        # Éviter le surencodage : ne pas dépasser ~110 % du débit source.
        if debit_src is not None:
            debit = min(debit, max(32, int(round(debit_src * 1.1))))

        # Bornes raisonnables.
        debit = max(24, min(debit, 320))

    justification = _construire_justification(
        type_contenu=type_contenu,
        codec=codec,
        mode=mode,
        debit=debit,
        analyse=analyse,
        source_sans_perte=source_sans_perte,
    )

    raisonnement = {
        "classe_contenu": type_contenu,
        "canaux": canaux,
        "source_sans_perte": source_sans_perte,
        "entrees_utilisees": {
            "probabilite_parole": prob_parole,
            "probabilite_musique": prob_musique,
            "facteur_crete_db": crete,
            "taux_echantillonnage_hz": taux_ech,
            "debit_source_kbps": debit_src,
            "codec_source": analyse.codec_source,
        },
    }

    return DecisionCompression(
        codec=codec,
        debit_kbps=debit,
        mode=mode,
        justification=justification,
        raisonnement=raisonnement,
    )


_NOMS_CODECS = {
    "mp3": "MP3",
    "aac": "AAC",
    "opus": "Opus",
    "ogg_vorbis": "OGG Vorbis",
    "flac": "FLAC",
}


def _construire_justification(
    *,
    type_contenu: str,
    codec: str,
    mode: str,
    debit: int,
    analyse: AnalyseAudio,
    source_sans_perte: bool,
) -> str:
    parties: list[str] = []
    nom_codec = _NOMS_CODECS.get(codec, codec.upper())

    # ── Raison principale du choix de codec ──
    if codec == "flac":
        parties.append(
            "Source sans perte avec dynamique riche ou haute résolution détectée ; "
            "FLAC choisi pour conserver la qualité originale intacte (compression sans perte)."
        )
    elif codec == "opus":
        if type_contenu == "signal_tonal":
            parties.append(
                "Signal tonal détecté (bip/sinus) ; Opus sélectionné en bas débit pour "
                "une très bonne efficacité de compression sur ce type de contenu."
            )
        else:
            parties.append(
                "Contenu à dominante parole détecté ; Opus sélectionné pour son excellente "
                "efficacité vocale à bas débit (format moderne, optimal pour la voix)."
            )
    elif codec == "aac":
        parties.append(
            "Contenu à dominante musique détecté ; AAC sélectionné pour sa meilleure "
            "qualité que MP3 à débit égal, avec une bonne compatibilité de lecture."
        )
    elif codec == "ogg_vorbis":
        parties.append(
            "Contenu mixte détecté ; OGG Vorbis sélectionné comme alternative libre "
            "offrant un bon compromis entre qualité vocale et musicale."
        )
    elif codec == "mp3":
        if not source_sans_perte and analyse.debit_source_kbps is not None and analyse.debit_source_kbps <= 128:
            parties.append(
                "Source déjà compressée à bas débit ; MP3 choisi pour sa compatibilité "
                "universelle (inutile d'utiliser un codec avancé sur un signal déjà dégradé)."
            )
        else:
            parties.append(
                "Type de contenu inconnu ; MP3 choisi par défaut pour sa compatibilité "
                "universelle (format le plus largement supporté)."
            )

    # ── Débit / mode ──
    if mode == "sans_perte":
        parties.append(f"{nom_codec} en mode sans perte (débit variable selon le contenu).")
    else:
        parties.append(f"{nom_codec} en {mode} à {debit} kbps.")

    # ── Indices source ──
    if analyse.codec_source or analyse.debit_source_kbps is not None:
        src = []
        if analyse.codec_source:
            src.append(analyse.codec_source)
        if analyse.debit_source_kbps is not None:
            src.append(f"{analyse.debit_source_kbps} kbps")
        parties.append(f"Source : {', '.join(src)}.")

    # ── Dynamique ──
    if analyse.facteur_crete_db is not None:
        parties.append(
            f"Facteur de crête {analyse.facteur_crete_db:.1f} dB "
            f"pris en compte pour la complexité/dynamique."
        )

    return " ".join(parties)


def charger_analyse_json(chemin: str) -> Dict[str, Any]:
    with open(chemin, "r", encoding="utf-8") as f:
        donnees = json.load(f)
    if not isinstance(donnees, dict):
        raise ValueError("Le fichier JSON d'analyse doit être un objet/dictionnaire")
    return donnees


def principal(argv: Optional[list[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(
        description="Agent de décision : choisir codec/débit/mode à partir de la sortie d'analyse.py."
    )
    p.add_argument("--analyse-json", type=str, required=True, help="Chemin vers le JSON produit par analyse.py")
    args = p.parse_args(argv)

    analyse = charger_analyse_json(args.analyse_json)
    decision = decider_compression(analyse)
    print(decision.vers_json(indentation=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
