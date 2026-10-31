#!/usr/bin/env python3
"""
Script principal pour ajouter des équipements à l'inventaire depuis le chat.
Utilisation : python update_inventory_from_chat.py "votre description"
"""

import os
import sys
import csv
from datetime import datetime

# Configuration des chemins
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'data')
INVENTAIRE_CSV = os.path.join(DATA_DIR, 'inventaire.csv')

# Base de connaissances simplifiée
KNOWLEDGE_BASE = {
    'gilet': {'category': 'Sécurité', 'subcategory': 'Gilet', 'system': 'SC'},
    'veste': {'category': 'Sécurité', 'subcategory': 'Gilet', 'system': 'SC'},
    'sauvetage': {'category': 'Sécurité', 'subcategory': 'Gilet', 'system': 'SC'},
    'bouée': {'category': 'Sécurité', 'subcategory': 'Bouée', 'system': 'SC'},
    'extincteur': {'category': 'Sécurité', 'subcategory': 'Extincteur', 'system': 'SC'},
    'trousse': {'category': 'Sécurité', 'subcategory': 'Trousse', 'system': 'SC'},
    'lampe': {'category': 'Éclairage', 'subcategory': 'Lampe', 'system': 'LT'},
    'ampoule': {'category': 'Éclairage', 'subcategory': 'Ampoule', 'system': 'LT'},
    'table': {'category': 'Mobilier', 'subcategory': 'Table', 'system': 'WD'},
    'chaise': {'category': 'Mobilier', 'subcategory': 'Chaise', 'system': 'WD'},
    'siège': {'category': 'Mobilier', 'subcategory': 'Siège', 'system': 'WD'},
    'dossier': {'category': 'Mobilier', 'subcategory': 'Dossier', 'system': 'WD'},
    'matelas': {'category': 'Confort', 'subcategory': 'Matelas', 'system': 'CF'},
    'coussin': {'category': 'Confort', 'subcategory': 'Coussin', 'system': 'CF'},
    'moteur': {'category': 'Mécanique', 'subcategory': 'Moteur', 'system': 'ME'},
    'pompe': {'category': 'Mécanique', 'subcategory': 'Pompe', 'system': 'ME'},
    'batterie': {'category': 'Électrique', 'subcategory': 'Batterie', 'system': 'EL'},
    'câble': {'category': 'Électrique', 'subcategory': 'Câble', 'system': 'EL'},
    'voile': {'category': 'Voilerie', 'subcategory': 'Voile', 'system': 'VL'},
    'corde': {'category': 'Voilerie', 'subcategory': 'Corde', 'system': 'VL'},
    'ancre': {'category': 'Ancrage', 'subcategory': 'Ancre', 'system': 'AN'},
    'chaîne': {'category': 'Ancrage', 'subcategory': 'Chaîne', 'system': 'AN'},
    'GPS': {'category': 'Navigation', 'subcategory': 'GPS', 'system': 'NA'},
    'radio': {'category': 'Communication', 'subcategory': 'Radio', 'system': 'CM'},
}

# Mappages de position
ZONE_MAP = {'avant': 'F', 'proue': 'F', 'arrière': 'A', 'poupe': 'A', 'milieu': 'M', 'centre': 'M', 'carré': 'M', 'plateau': 'M'}
SIDE_MAP = {'bâbord': 'P', 'gauche': 'P', 'tribord': 'S', 'droite': 'S', 'centre': 'C', 'sur ma droite': 'S', 'sur ma gauche': 'P'}
LEVEL_MAP = {'intérieur': 'I', 'cabine': 'I', 'bas': 'I', 'extérieur': 'U', 'pont': 'U', 'haut': 'U', 'cockpit': 'U'}

# Couleurs
COLORS = ['rouge', 'bleu', 'vert', 'jaune', 'noir', 'blanc', 'orange', 'gris', 'marron', 'beige', 'doré']

# Conditions
CONDITIONS = {'neuf': 'Neuf', 'bon état': 'Bon état', 'en bon état': 'Bon état', 'usagé': 'Usagé', 'cassé': 'Cassé', 'poussiéreux': 'Poussiéreux'}

def clean_text(text):
    """Nettoie le texte pour analyse"""
    import re
    text = text.strip().lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def extract_name(text):
    """Extrait le nom de l'équipement"""
    for kw in sorted(KNOWLEDGE_BASE.keys(), key=len, reverse=True):
        if f' {kw} ' in f' {text} ':
            return kw
    return text.split()[0] if text else "inconnu"

def extract_category(text):
    """Extrait catégorie, sous-catégorie et système"""
    for kw, info in KNOWLEDGE_BASE.items():
        if f' {kw} ' in f' {text} ':
            return info['category'], info['subcategory'], info['system']
    return "Autre", "", "XX"

def extract_position(text, full_text=None):
    """Extrait zone, côté, niveau"""
    zone, side, level = "M", "C", "I"
    context = full_text or text

    for kw, val in ZONE_MAP.items():
        if kw in context:
            zone = val
    for kw, val in SIDE_MAP.items():
        if kw in context:
            side = val
    for kw, val in LEVEL_MAP.items():
        if kw in context:
            level = val

    return zone, side, level

def extract_color(text):
    """Extrait la couleur"""
    for color in COLORS:
        if color in text:
            return color
    return ""

def extract_quantity(text):
    """Extrait la quantité"""
    import re
    nums = re.findall(r'\b\d+\b', text)
    return int(nums[0]) if nums else 1

def extract_condition(text):
    """Extrait la condition"""
    for phrase, cond in CONDITIONS.items():
        if phrase in text:
            return cond
    return ""

def extract_voltage(text):
    """Extrait le voltage"""
    import re
    match = re.search(r'\b(\d+)\s*volts?\b', text, re.I)
    return match.group(1) if match else ""

def generate_unique_code(zone, side, level, system, csv_path):
    """Génère un code unique"""
    key = f"{zone}-{side}-{level}-{system}"
    count = 0

    if os.path.exists(csv_path):
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Unique Code', '').startswith(key):
                    count += 1

    return f"{key}-{count+1:03d}"

def parse_description(description):
    """Parse une description et retourne les équipements"""
    clean_desc = clean_text(description)

    # Trouver les mots-clés
    keywords = sorted(KNOWLEDGE_BASE.keys(), key=len, reverse=True)
    positions = []
    for kw in keywords:
        import re
        for m in re.finditer(rf'\b{kw}\b', clean_desc):
            positions.append(m.start())

    positions = sorted(set(positions))

    if not positions:
        return [{'name': clean_desc, 'category': 'Autre', 'system': 'XX'}]

    # Diviser en équipements
    items = []
    for i, pos in enumerate(positions):
        if i > 0:
            item_text = clean_desc[positions[i-1]:pos].strip()
            if len(item_text) > 3:
                items.append(item_text)

    if positions:
        last_text = clean_desc[positions[-1]:].strip()
        if len(last_text) > 3:
            items.append(last_text)

    if not items:
        items = [clean_desc]

    # Parser chaque équipement
    results = []
    for item_text in items:
        name = extract_name(item_text)
        category, subcategory, system = extract_category(item_text)
        zone, side, level = extract_position(item_text, clean_desc)
        color = extract_color(item_text)
        quantity = extract_quantity(item_text)
        condition = extract_condition(item_text)
        voltage = extract_voltage(item_text)

        results.append({
            'name': name,
            'category': category,
            'subcategory': subcategory,
            'system': system,
            'zone': zone,
            'side': side,
            'level': level,
            'position': '',
            'color': color,
            'quantity': quantity,
            'condition': condition,
            'voltage': voltage,
            'brand': '',
            'model': '',
            'notes': item_text,
            'timestamp': datetime.now().isoformat()
        })

    return results

def load_inventory(csv_path):
    """Charge l'inventaire existant"""
    if not os.path.exists(csv_path):
        return []
    with open(csv_path, mode='r', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def save_inventory(data, csv_path):
    """Sauvegarde l'inventaire"""
    if not data:
        return

    headers = list(data[0].keys())
    with open(csv_path, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

def update_inventory(description, csv_path=INVENTAIRE_CSV):
    """Met à jour l'inventaire avec une nouvelle description"""
    # Charger l'inventaire existant
    existing = load_inventory(csv_path)

    # Parser la nouvelle description
    new_items = parse_description(description)

    # Générer les codes uniques
    for item in new_items:
        code = generate_unique_code(item['zone'], item['side'], item['level'], item['system'], csv_path)
        item['Unique Code'] = code

    # Fusionner avec l'existant
    updated = existing + new_items

    # Sauvegarder
    save_inventory(updated, csv_path)

    return new_items

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python update_inventory_from_chat.py 'votre description'")
        print("Exemple: python update_inventory_from_chat.py 'une lampe dorée sur ma droite'")
        sys.exit(1)

    description = ' '.join(sys.argv[1:])
    print(f"Analyse de la description: {description}")

    new_items = update_inventory(description)

    print(f"\n✅ {len(new_items)} équipement(s) ajouté(s):")
    for item in new_items:
        print(f"  - {item['Unique Code']}: {item['name']} ({item['category']}) - Position: {item['zone']}-{item['side']}-{item['level']}-{item['system']}")

    print(f"\n📝 Fichier mis à jour: {INVENTAIRE_CSV}")
