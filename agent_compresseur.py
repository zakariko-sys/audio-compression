# agent_compresseur.py
# Agent Compresseur

import os

from compression_utils import compress_aac, compress_flac, compress_mp3, compress_ogg, compress_opus

class CompressorAgent:

    @staticmethod
    def _normaliser_bitrate(bitrate):
        if bitrate is None:
            return None
        if isinstance(bitrate, int):
            return f"{bitrate}k"
        bitrate_str = str(bitrate).strip().lower()
        if bitrate_str.endswith("k"):
            return bitrate_str
        if bitrate_str.isdigit():
            return f"{bitrate_str}k"
        return bitrate_str
    
    def compresser(self, audio_path, output_path, codec, bitrate=None):
        print(f"[CompressorAgent] Compression de: {os.path.basename(audio_path)}")
        
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Fichier introuvable: {audio_path}")
        
        taille_originale = os.path.getsize(audio_path)
        codec_normalise = "ogg" if codec == "ogg_vorbis" else codec
        bitrate = self._normaliser_bitrate(bitrate)
        
        if codec_normalise == "mp3":
            if not bitrate:
                bitrate = "128k"
            compress_mp3(audio_path, output_path, bitrate)
        elif codec_normalise == "aac":
            if not bitrate:
                bitrate = "128k"
            compress_aac(audio_path, output_path, bitrate)
        elif codec_normalise == "opus":
            if not bitrate:
                bitrate = "64k"
            compress_opus(audio_path, output_path, bitrate)
        elif codec_normalise == "ogg":
            if not bitrate:
                bitrate = "128k"
            compress_ogg(audio_path, output_path, bitrate)
        elif codec_normalise == "flac":
            compress_flac(audio_path, output_path)
        else:
            raise ValueError(f"Format non supporte: {codec}")
        
        taille_compressée = os.path.getsize(output_path)
        taux = (1 - taille_compressée / taille_originale) * 100
        
        resultat = {
            "taux_compression": round(taux, 2),
            "taille_originale_ko": round(taille_originale / 1024, 2),
            "taille_compressée_ko": round(taille_compressée / 1024, 2),
            "codec": codec_normalise,
            "bitrate": bitrate if bitrate else "N/A",
            "fichier_original": audio_path,
            "fichier_compressé": output_path
        }
        
        print(f"[CompressorAgent] Compression terminee: {round(taux, 2)}%")
        return resultat