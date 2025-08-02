"""
Schema validation utility for agents-deep-research.
Used to validate JSON schemas and provide consistent error messages.
"""

import json
import jsonschema
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, Union
import glob

SCHEMAS_DIR = Path(__file__).parent

class SchemaValidator:
    """Validates JSON data against predefined schemas"""
    
    def __init__(self):
        self.schemas = {}
        self.registry = {}
        self._load_schemas()
        self._load_registry()
    
    def _load_schemas(self):
        """Auto-discover and load all schemas from the schemas directory"""
        # Auto-discover schema files using glob pattern
        schema_files = glob.glob(str(SCHEMAS_DIR / "*_v*.json"))
        
        for schema_file in schema_files:
            schema_path = Path(schema_file)
            # Extract schema name from filename (e.g., "select_tools_v1.json" -> "select_tools")
            schema_name = schema_path.stem.rsplit('_v', 1)[0]
            
            try:
                with open(schema_path, 'r') as f:
                    self.schemas[schema_name] = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load schema {schema_file}: {e}")
    
    def _load_registry(self):
        """Load the schema registry for version management"""
        registry_path = SCHEMAS_DIR / "registry.json"
        if registry_path.exists():
            try:
                with open(registry_path, 'r') as f:
                    data = json.load(f)
                    self.registry = data.get("schema_registry", {})
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load registry: {e}")
    
    def get_latest_version(self, schema_name: str) -> int:
        """Get the latest version number for a schema"""
        if schema_name in self.registry.get("schemas", {}):
            return self.registry["schemas"][schema_name]["current_version"]
        return 1  # Default to version 1
    
    def validate(self, schema_name: str, data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[jsonschema.ValidationError]]:
        """
        Validate data against a schema.
        
        Args:
            schema_name: Name of the schema to validate against
            data: JSON data to validate
            
        Returns:
            Tuple of (is_valid, error_message, validation_error_object)
        """
        if schema_name not in self.schemas:
            return False, f"Unknown schema: {schema_name}", None
        
        try:
            jsonschema.validate(instance=data, schema=self.schemas[schema_name])
            return True, None, None
        except jsonschema.ValidationError as e:
            return False, str(e), e
        except Exception as e:
            return False, f"Validation error: {str(e)}", None
    
    def get_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """Get a schema by name"""
        return self.schemas.get(schema_name)
    
    def list_schemas(self) -> list:
        """List all available schema names"""
        return list(self.schemas.keys())

# Global validator instance
validator = SchemaValidator()