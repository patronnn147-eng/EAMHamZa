"""
Model Registry
Track ML model versions and metadata
"""
from datetime import datetime
from typing import Dict, Optional
import json
import os
import logging

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Track ML model versions and metadata."""
    
    def __init__(self):
        self.models: Dict[str, Dict] = {}
        # Registry file location is configurable via MODEL_REGISTRY_PATH env var.
        # Default writes to /data/model_registry.json (persistent volume).
        # Fallback: parent of src/ dir (ml-microservice root) for local dev.
        self._registry_file = os.getenv(
            'MODEL_REGISTRY_PATH',
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'model_registry.json',
            ),
        )
        self._load_from_disk()
    
    def register(
        self, 
        model_name: str, 
        version: str, 
        metrics: Dict = None,
        model_path: str = None
    ) -> Dict:
        """
        Register a model version.
        
        Args:
            model_name: Name of the model (e.g., 'p1_failure')
            version: Version string (e.g., '1.0.0')
            metrics: Optional metrics dict
            model_path: Path to model file
        
        Returns:
            Registration entry
        """
        entry = {
            "name": model_name,
            "version": version,
            "registered_at": datetime.now().isoformat(),
            "metrics": metrics or {},
            "model_path": model_path
        }
        
        key = f"{model_name}:{version}"
        self.models[key] = entry
        self._save_to_disk()
        
        logger.info(f"Registered model: {key}")
        return entry
    
    def get(self, model_name: str, version: str = None) -> Optional[Dict]:
        """
        Get model metadata.
        
        Args:
            model_name: Name of the model
            version: Version string (latest if None)
        
        Returns:
            Model metadata or None
        """
        if version:
            key = f"{model_name}:{version}"
            return self.models.get(key)
        
        # Get latest version
        matching = [
            v for k, v in self.models.items() 
            if k.startswith(f"{model_name}:")
        ]
        
        if matching:
            # Sort by registered_at descending
            matching.sort(
                key=lambda x: x.get('registered_at', ''), 
                reverse=True
            )
            return matching[0]
        
        return None
    
    def list_versions(self, model_name: str) -> list:
        """
        List all versions of a model.
        
        Args:
            model_name: Name of the model
        
        Returns:
            List of version entries
        """
        return [
            v for k, v in self.models.items() 
            if k.startswith(f"{model_name}:")
        ]
    
    def list_all_models(self) -> Dict[str, list]:
        """
        List all registered models and their versions.
        
        Returns:
            Dict mapping model names to version lists
        """
        result = {}
        for key, entry in self.models.items():
            name = entry['name']
            if name not in result:
                result[name] = []
            result[name].append({
                "version": entry['version'],
                "registered_at": entry['registered_at'],
                "metrics": entry.get('metrics', {})
            })
        return result
    
    def _save_to_disk(self):
        """Save registry to JSON file."""
        try:
            with open(self._registry_file, 'w') as f:
                json.dump(self.models, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")
    
    def _load_from_disk(self):
        """Load registry from JSON file."""
        if os.path.exists(self._registry_file):
            try:
                with open(self._registry_file) as f:
                    self.models = json.load(f)
                logger.info(f"Loaded {len(self.models)} model entries from registry")
            except Exception as e:
                logger.warning(f"Failed to load registry: {e}")
                self.models = {}


# Global registry instance
registry = ModelRegistry()


def register_model(
    model_name: str, 
    version: str, 
    metrics: Dict = None,
    model_path: str = None
) -> Dict:
    """Convenience function to register a model."""
    return registry.register(model_name, version, metrics, model_path)


def get_model_info(model_name: str, version: str = None) -> Optional[Dict]:
    """Convenience function to get model info."""
    return registry.get(model_name, version)


def list_model_versions(model_name: str) -> list:
    """Convenience function to list versions."""
    return registry.list_versions(model_name)