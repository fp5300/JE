import hashlib
import json
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────
# Configuration (via variables d'environnement)
# ──────────────────────────────────────────────

URL_TO_WATCH   = os.environ.get("URL_TO_WATCH",   "https://example.com")
EMAIL_SENDER   = os.environ.get("EMAIL_SENDER",   "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER", "")
HASH_FILE      = "last_hash.txt"   # fichier local où on stocke le hash précédent

# ──────────────────────────────────────────────
# Étape 1 : Télécharger et nettoyer la page
# ──────────────────────────────────────────────

def fetch_page_content(url: str) -> str:
    """Télécharge la page et retourne le texte visible (sans balises HTML)."""
    headers = {"User-Agent": "Mozilla/5.0 (website-monitor-bot/1.0)"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Supprime les scripts, styles et balises invisibles
    for tag in soup(["script", "style", "meta", "link", "noscript"]):
        tag.decompose()

    return soup.get_text(separator=" ", strip=True)


# ──────────────────────────────────────────────
# Étape 2 : Calculer le hash MD5 du contenu
# ──────────────────────────────────────────────

def compute_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ──────────────────────────────────────────────
# Étape 3 : Lire / écrire le hash précédent
# ──────────────────────────────────────────────

def load_previous_hash() -> str | None:
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            return f.read().strip()
    return None


def save_hash(hash_value: str) -> None:
    with open(HASH_FILE, "w") as f:
        f.write(hash_value)


# ──────────────────────────────────────────────
# Étape 4 : Envoyer un email via Gmail SMTP
# ──────────────────────────────────────────────

def send_email(url: str) -> None:
    subject = f"[Monitor] La page a changé : {url}"
    body = f"""Bonjour,

La page suivante a été mise à jour :

  {url}

Cliquez sur le lien pour voir les changements.

---
Bot de surveillance automatique
"""

    msg = MIMEMultipart()
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECEIVER
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())

    print("✉️  Email envoyé avec succès.")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    print(f"🔍 Surveillance de : {URL_TO_WATCH}")

    # Téléchargement
    try:
        content = fetch_page_content(URL_TO_WATCH)
    except Exception as e:
        print(f"❌ Impossible de télécharger la page : {e}")
        sys.exit(1)

    # Hash actuel
    current_hash = compute_hash(content)
    print(f"📌 Hash actuel  : {current_hash}")

    # Hash précédent
    previous_hash = load_previous_hash()
    print(f"📂 Hash précédent : {previous_hash or 'aucun (première exécution)'}")

    # Comparaison
    if previous_hash is None:
        print("ℹ️  Première exécution — hash sauvegardé, aucun email envoyé.")
        save_hash(current_hash)

    elif current_hash != previous_hash:
        print("🆕 Changement détecté !")
        save_hash(current_hash)
        try:
            send_email(URL_TO_WATCH)
        except Exception as e:
            print(f"❌ Échec de l'envoi d'email : {e}")
            sys.exit(1)

    else:
        print("✅ Aucun changement détecté.")


if __name__ == "__main__":
    main()
