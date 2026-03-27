# metrics.py
# Module des métriques pour l'agent évaluateur

import numpy as np
import librosa
import os

# ============================================================
# 1. TAUX DE COMPRESSION
# ============================================================

def taux_compression(original_path, compressed_path):
    """
    Calcule le pourcentage de réduction de taille du fichier
    Formule : τ = (1 - taille_c / taille_o) × 100
    """
    taille_o = os.path.getsize(original_path)
    taille_c = os.path.getsize(compressed_path)
    taux = (1 - taille_c / taille_o) * 100
    return round(taux, 2)


# ============================================================
# 2. MSE - ERREUR QUADRATIQUE MOYENNE
# ============================================================

def mse(original, compresse):
    """
    Calcule l'erreur quadratique moyenne (Mean Square Error)
    Formule : MSE = moyenne((original - compressé)²)
    """
    difference = original - compresse
    return np.mean(difference ** 2)


# ============================================================
# 3. SNR - RAPPORT SIGNAL/BRUIT
# ============================================================

def snr(original, valeur_mse):
    """
    Calcule le rapport signal sur bruit (Signal-to-Noise Ratio)
    Formule : SNR = 10 × log10(V / MSE) où V = moyenne(original²)
    """
    puissance_signal = np.mean(original ** 2)
    if valeur_mse == 0:
        return 100.0
    return round(10 * np.log10(puissance_signal / valeur_mse), 2)


# ============================================================
# 4. PSNR - RAPPORT SIGNAL/BRUIT DE CRÊTE
# ============================================================

def psnr(valeur_mse, max_val=1.0):
    """
    Calcule le rapport signal sur bruit de crête (Peak SNR)
    Formule : PSNR = 10 × log10(max² / MSE)
    """
    if valeur_mse == 0:
        return 100.0
    return round(10 * np.log10((max_val ** 2) / valeur_mse), 2)


# ============================================================
# 5. INTERPRÉTATION OPTIMALE (PSNR + SNR + Taux)
# ============================================================

def interpretation_optimale(taux, snr, psnr):
    """
    Interprétation combinée des 3 métriques
    Retourne analyse détaillée pour l'interface
    
    Niveaux de qualité:
    - 5: Excellente (PSNR ≥ 40, SNR ≥ 35)
    - 4: Très bonne (PSNR 35-40, SNR 30-35)
    - 3: Bonne (PSNR 30-35, SNR 25-30)
    - 2: Moyenne (PSNR 25-30, SNR 20-25)
    - 1: Passable (PSNR 20-25, SNR 15-20)
    - 0: Mauvaise (PSNR < 20, SNR < 15)
    """
    
    # 1. ÉVALUATION DE LA QUALITÉ
    if psnr >= 40 and snr >= 35:
        qualite = "Excellente"
        niveau = 5
        commentaire = "Qualité parfaite, aucune perte perceptible"
        recommandation = "Compression idéale pour l'archivage et la production musicale"
        
    elif psnr >= 35 and snr >= 30:
        qualite = "Très bonne"
        niveau = 4
        commentaire = "Perte à peine perceptible, excellente fidélité"
        recommandation = "Parfait pour écoute sur équipement haut de gamme"
        
    elif psnr >= 30 and snr >= 25:
        qualite = "Bonne"
        niveau = 3
        commentaire = "Qualité acceptable, perte non perceptible sur équipement standard"
        recommandation = "Idéal pour diffusion web, streaming et usage mobile"
        
    elif psnr >= 25 and snr >= 20:
        qualite = "Moyenne"
        niveau = 2
        commentaire = "Perte audible sur équipement haute fidélité"
        recommandation = "Acceptable pour podcasts, audiobooks et contenus parlés"
        
    elif psnr >= 20 and snr >= 15:
        qualite = "Passable"
        niveau = 1
        commentaire = "Perte nettement audible, son dégradé"
        recommandation = "Limite acceptable pour stockage de masse"
        
    else:
        qualite = "Mauvaise"
        niveau = 0
        commentaire = "Qualité médiocre, compression trop agressive"
        recommandation = "Augmenter le bitrate ou changer de codec"
    
    # 2. ÉVALUATION DE L'EFFICACITÉ
    if taux >= 90:
        efficacite = "Maximale"
        facteur = round(100/(100-taux), 1)
        gain = f"Réduction de {taux}% : le fichier est {facteur}x plus petit"
    elif taux >= 75:
        efficacite = "Très élevée"
        facteur = round(100/(100-taux), 1)
        gain = f"Réduction de {taux}% : le fichier est {facteur}x plus petit"
    elif taux >= 50:
        efficacite = "Élevée"
        facteur = round(100/(100-taux), 1)
        gain = f"Réduction de {taux}% : le fichier est {facteur}x plus petit"
    elif taux >= 25:
        efficacite = "Modérée"
        gain = f"Réduction de {taux}% : gain de stockage limité"
    else:
        efficacite = "Faible"
        gain = f"Réduction de {taux}% : compression presque inexistante"
    
    # 3. CONCLUSION FINALE
    if (psnr >= 30 and taux >= 75) or (psnr >= 35 and taux >= 50):
        conclusion = "Compression optimale - Excellent compromis taille/qualité"
    elif psnr >= 25 and taux >= 80:
        conclusion = "Compression agressive - Bon compromis pour stockage"
    elif psnr >= 30 and taux < 50:
        conclusion = "Compression légère - Priorité à la qualité"
    elif psnr < 25 and taux > 85:
        conclusion = "Compression trop agressive - Perte de qualité excessive"
    elif psnr < 25:
        conclusion = "Qualité insuffisante - À améliorer"
    else:
        conclusion = "Compression acceptable - Convient pour l'usage visé"
    
    return {
        "qualite": qualite,
        "niveau": niveau,
        "commentaire": commentaire,
        "recommandation": recommandation,
        "efficacite": efficacite,
        "gain": gain,
        "conclusion": conclusion
    }


# ============================================================
# 6. UTILITAIRE : CHARGEMENT ET ALIGNEMENT
# ============================================================

def charger_et_aligner(original_path, compressed_path):
    """
    Charge deux fichiers audio et les aligne à la même longueur
    Nécessaire pour comparer des signaux de durées différentes
    """
    y_orig, sr_orig = librosa.load(original_path, sr=None)
    y_comp, sr_comp = librosa.load(compressed_path, sr=None)
    
    min_len = min(len(y_orig), len(y_comp))
    y_orig = y_orig[:min_len]
    y_comp = y_comp[:min_len]
    
    return y_orig, y_comp


