# Boat Inventory AI System

## Overview

This is a complete **AI-powered boat inventory management system** that allows you to:

1. **Dictate or type** descriptions of equipment in natural French
2. **Automatically extract** object name, category, position, color, quantity, and condition
3. **Generate unique codes** following the pattern `{Zone}-{Side}-{Level}-{System}-{ObjectNo.}`
4. **Save to CSV** for Google Sheets integration

## Files Structure
boat-inventory/
├── data/
│   ├── inventaire.csv          # Main inventory (from Google Drive)
│   ├── BaseConnaissance.csv    # Knowledge base for classification
│   └── PositionMapping.csv     # Position to Zone/Side/Level mapping
├── scripts/
│   ├── boat_inventory_agent.py    # Main AI agent
│   ├── inventory_parser.py       # Natural language parser
│   └── update_inventory_from_chat.py # Chat integration
└── README.md

## Quick Start

### Parse a description
python
from scripts.boat_inventory_agent import BoatInventoryAgent

agent = BoatInventoryAgent()
agent.add_items_from_text("Sur ma droite, je vois une lampe dorée")
agent.to_csv("data/inventaire.csv")
Unique Code Format
{Zone}-{Side}-{Level}-{System}-{ObjectNo.}

Zone: F (Forward), M (Mid), A (Aft)
Side: P (Port), C (Center), S (Starboard)
Level: I (Interior), U (Upper)
System: LT (Lighting), SC (Security), WD (Furniture), etc.
ObjectNo: 001, 002, 003...
---

### **`requirements.txt`**
pandas>=1.0.0
openpyxl>=3.0.0

---

### **`INSTRUCTIONS_MISTRAL_AGENT.md`**
```markdown
# Mistral AI Agent Instructions for Boat Inventory

## Role
You are an AI assistant for boat inventory management. Parse French descriptions, extract structured data, generate unique codes, and update CSV files.

## Workflow
1. Parse French descriptions (e.g., "une lampe dorée sur ma droite")
2. Extract: name, category, position (Zone/Side/Level), color, quantity, condition
3. Generate unique code: {Zone}-{Side}-{Level}-{System}-{ObjectNo.}
4. Update data/inventaire.csv

## Code Format
- Zone: F (Forward/Avant), M (Mid/Milieu), A (Aft/Arrière)
- Side: P (Port/Bâbord), C (Center/Centre), S (Starboard/Tribord)
- Level: I (Interior/Intérieur), U (Upper/Extérieur)
- System: LT (Éclairage), SC (Sécurité), WD (Mobilier), CF (Confort), ME (Mécanique), EL (Électrique), VL (Voilerie), AN (Ancrage), NA (Navigation), CM (Communication), ST (Structure)

## Knowledge Base (BaseConnaissance.csv)
Maps keywords to categories/systems. Extend as needed.

## Position Mapping (PositionMapping.csv)
Maps French position descriptions to Zone/Side/Level.

## Example
Input: "une lampe dorée sur ma droite dans le carré"
Output:
- Name: lampe
- Category: Éclairage
- System: LT
- Zone: M, Side: S, Level: I
- Color: doré
- Code: M-S-I-LT-001

## Commands
- /list - List all items
- /search [term] - Search inventory
- /stats - Show statistics
- /help - Show help
