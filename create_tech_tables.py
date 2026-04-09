import asyncio
import sys
sys.path.insert(0, '/workspace/app/backend')

from tools.libs.be.backend_manager import BackendManager

async def create_tables():
    manager = BackendManager()
    
    tables_json = '''[
  {
    "title": "notifications",
    "type": "object",
    "properties": {
      "id": {"type": "integer", "description": "Primary key, auto-increment"},
      "utilisateur_id": {"type": "integer", "description": "User ID who receives the notification"},
      "titre": {"type": "string", "description": "Notification title"},
      "message": {"type": "string", "description": "Notification message"},
      "type": {"type": "string", "description": "Notification type: ASSIGNMENT, STATUS_CHANGE, URGENT_ALERT, COMMENT"},
      "priorite": {"type": "string", "description": "Priority: NORMALE, URGENTE"},
      "lu": {"type": "boolean", "description": "Read status"},
      "ordre_travail_id": {"type": "integer", "description": "Related work order ID"},
      "created_at": {"type": "string", "format": "date-time", "description": "Creation timestamp"}
    },
    "required": ["id", "utilisateur_id", "titre", "message", "type", "priorite"],
    "create_only": false
  },
  {
    "title": "commentaires",
    "type": "object",
    "properties": {
      "id": {"type": "integer", "description": "Primary key, auto-increment"},
      "ordre_travail_id": {"type": "integer", "description": "Related work order ID"},
      "utilisateur_id": {"type": "integer", "description": "User ID who created the comment"},
      "contenu": {"type": "string", "description": "Comment content"},
      "fichier_url": {"type": "string", "description": "Attached file URL"},
      "created_at": {"type": "string", "format": "date-time", "description": "Creation timestamp"}
    },
    "required": ["id", "ordre_travail_id", "utilisateur_id", "contenu"],
    "create_only": false
  },
  {
    "title": "alertes_urgentes",
    "type": "object",
    "properties": {
      "id": {"type": "integer", "description": "Primary key, auto-increment"},
      "utilisateur_id": {"type": "integer", "description": "User ID who created the alert"},
      "categorie": {"type": "string", "description": "Alert category: SECURITE, PANNE_CRITIQUE, QUALITE"},
      "description": {"type": "string", "description": "Alert description"},
      "machine_id": {"type": "integer", "description": "Related machine ID"},
      "photo_url": {"type": "string", "description": "Photo URL"},
      "statut": {"type": "string", "description": "Status: EN_ATTENTE, TRAITE"},
      "ordre_travail_genere_id": {"type": "integer", "description": "Generated work order ID"},
      "created_at": {"type": "string", "format": "date-time", "description": "Creation timestamp"}
    },
    "required": ["id", "utilisateur_id", "categorie", "description", "statut"],
    "create_only": false
  }
]'''
    
    try:
        result = await manager.create_tables(tables_json)
        print("Tables created successfully:", result)
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    asyncio.run(create_tables())