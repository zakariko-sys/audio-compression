# agent_evaluateur.py
# Agent Évaluateur - Version classe simple

import os

from metrics import (
    taux_compression,
    mse,
    snr,
    psnr,
    interpretation_optimale,
    charger_et_aligner
)

class EvaluatorAgent:
    """
    Agent 4 : Évalue la qualité de compression audio
    Entrée  : chemins original et compressé
    Sortie  : dictionnaire avec toutes les métriques
    """
    
    def evaluer(self, original_path, compressed_path):
        """
        Évalue la compression audio
        Retourne toutes les métriques et interprétations
        """
        print(f"[EvaluatorAgent] Evaluation de : {os.path.basename(original_path)}")
        
        # Vérifier fichiers
        if not os.path.exists(original_path):
            raise FileNotFoundError(f"Fichier original introuvable: {original_path}")
        if not os.path.exists(compressed_path):
            raise FileNotFoundError(f"Fichier compresse introuvable: {compressed_path}")
        
        try:
            # 1. Taux compression
            taux = taux_compression(original_path, compressed_path)
            
            # 2. Charger et aligner
            y_orig, y_comp = charger_et_aligner(original_path, compressed_path)
            
            # 3. MSE, SNR, PSNR
            val_mse = mse(y_orig, y_comp)
            val_snr = snr(y_orig, val_mse)
            val_psnr = psnr(val_mse)
            
            # 4. Interprétation
            interp = interpretation_optimale(taux, val_snr, val_psnr)
            
            # 5. Tailles
            taille_o = os.path.getsize(original_path) / 1024
            taille_c = os.path.getsize(compressed_path) / 1024
            
            resultat = {
                "taux_compression": float(taux),
                "snr": float(val_snr),
                "psnr": float(val_psnr),
                "mse": float(round(float(val_mse), 6)),
                "taille_originale_ko": float(round(taille_o, 2)),
                "taille_compressee_ko": float(round(taille_c, 2)),
                "qualite": interp["qualite"],
                "niveau": int(interp["niveau"]),
                "commentaire": interp["commentaire"],
                "recommandation": interp["recommandation"],
                "efficacite": interp["efficacite"],
                "gain": interp["gain"],
                "conclusion": interp["conclusion"]
            }
            
            print(f"[EvaluatorAgent] Evaluation terminee : {taux}% compression, {interp['qualite']}")
            return resultat
            
        except Exception as e:
            print(f"[EvaluatorAgent] Erreur: {e}")
            return {"erreur": str(e)}