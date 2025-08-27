"""
Configuration validation for SimTool projects.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml
from dataclasses import dataclass


class ConfigValidationError(Exception):
    """Exception raised when configuration validation fails."""
    pass


@dataclass
class ValidationRule:
    """Configuration validation rule."""
    field: str
    required: bool = False
    field_type: type = None
    allowed_values: List[Any] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    custom_validator: Optional[callable] = None
    description: str = ""


class ConfigValidator:
    """Validates SimTool project configuration."""
    
    # Define validation rules
    VALIDATION_RULES = [
        ValidationRule(
            field='default_simulator',
            required=True,
            field_type=str,
            allowed_values=['verilator', 'icarus', 'questa', 'xcelium'],
            description="Default simulator to use"
        ),
        ValidationRule(
            field='default_waves',
            required=True,
            field_type=bool,
            description="Enable waveform generation by default"
        ),
        ValidationRule(
            field='rtl_paths',
            required=True,
            field_type=list,
            min_length=1,
            description="List of RTL source paths"
        ),
        ValidationRule(
            field='tb_paths',
            required=True,
            field_type=list,
            min_length=1,
            description="List of testbench paths"
        ),
        ValidationRule(
            field='build_dir',
            required=True,
            field_type=str,
            description="Build directory path"
        ),
        ValidationRule(
            field='include_paths',
            required=False,
            field_type=list,
            description="Include paths for compilation"
        ),
        ValidationRule(
            field='defines',
            required=False,
            field_type=dict,
            description="Preprocessor defines"
        ),
        ValidationRule(
            field='verilator_path',
            required=False,
            field_type=(str, type(None)),
            custom_validator=lambda x: x is None or Path(x).exists(),
            description="Path to Verilator executable"
        ),
        ValidationRule(
            field='gtkwave_path',
            required=False,
            field_type=(str, type(None)),
            custom_validator=lambda x: x is None or Path(x).exists(),
            description="Path to GTKWave executable"
        ),
    ]
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> None:
        """
        Validate configuration dictionary.
        
        Args:
            config: Configuration dictionary to validate
            
        Raises:
            ConfigValidationError: If validation fails
        """
        errors = []
        
        for rule in cls.VALIDATION_RULES:
            try:
                cls._validate_field(config, rule)
            except ConfigValidationError as e:
                errors.append(str(e))
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ConfigValidationError(error_msg)
    
    @classmethod
    def _validate_field(cls, config: Dict[str, Any], rule: ValidationRule) -> None:
        """Validate a single configuration field."""
        field_name = rule.field
        
        # Check if required field is present
        if rule.required and field_name not in config:
            raise ConfigValidationError(f"Required field '{field_name}' is missing")
        
        # Skip validation if field is not present and not required
        if field_name not in config:
            return
            
        value = config[field_name]
        
        # Type validation
        if rule.field_type is not None:
            if isinstance(rule.field_type, tuple):
                # Multiple allowed types
                if not isinstance(value, rule.field_type):
                    type_names = ' or '.join(t.__name__ for t in rule.field_type)
                    raise ConfigValidationError(
                        f"Field '{field_name}' must be of type {type_names}, got {type(value).__name__}"
                    )
            else:
                # Single type
                if not isinstance(value, rule.field_type):
                    raise ConfigValidationError(
                        f"Field '{field_name}' must be of type {rule.field_type.__name__}, got {type(value).__name__}"
                    )
        
        # Value validation
        if rule.allowed_values is not None and value not in rule.allowed_values:
            allowed_str = ', '.join(str(v) for v in rule.allowed_values)
            raise ConfigValidationError(
                f"Field '{field_name}' must be one of [{allowed_str}], got '{value}'"
            )
        
        # Length validation for lists/strings
        if rule.min_length is not None and hasattr(value, '__len__'):
            if len(value) < rule.min_length:
                raise ConfigValidationError(
                    f"Field '{field_name}' must have at least {rule.min_length} items, got {len(value)}"
                )
        
        if rule.max_length is not None and hasattr(value, '__len__'):
            if len(value) > rule.max_length:
                raise ConfigValidationError(
                    f"Field '{field_name}' must have at most {rule.max_length} items, got {len(value)}"
                )
        
        # Custom validation
        if rule.custom_validator is not None:
            try:
                if not rule.custom_validator(value):
                    raise ConfigValidationError(f"Field '{field_name}' failed custom validation")
            except Exception as e:
                raise ConfigValidationError(f"Field '{field_name}' validation error: {e}")
    
    @classmethod
    def validate_yaml_file(cls, config_path: Path) -> Dict[str, Any]:
        """
        Validate YAML configuration file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Validated configuration dictionary
            
        Raises:
            ConfigValidationError: If file is invalid or validation fails
        """
        if not config_path.exists():
            raise ConfigValidationError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise ConfigValidationError(f"Error reading configuration file: {e}")
        
        if config is None:
            raise ConfigValidationError("Configuration file is empty")
        
        if not isinstance(config, dict):
            raise ConfigValidationError("Configuration must be a YAML dictionary")
        
        # Validate the configuration
        cls.validate_config(config)
        
        return config
    
    @classmethod
    def generate_schema_documentation(cls) -> str:
        """Generate documentation for configuration schema."""
        doc = "SimTool Configuration Schema\n"
        doc += "=" * 30 + "\n\n"
        
        for rule in cls.VALIDATION_RULES:
            doc += f"**{rule.field}**"
            if rule.required:
                doc += " (required)"
            doc += "\n"
            
            if rule.field_type:
                if isinstance(rule.field_type, tuple):
                    type_names = ' | '.join(t.__name__ for t in rule.field_type)
                    doc += f"  Type: {type_names}\n"
                else:
                    doc += f"  Type: {rule.field_type.__name__}\n"
            
            if rule.allowed_values:
                allowed_str = ', '.join(str(v) for v in rule.allowed_values)
                doc += f"  Allowed values: {allowed_str}\n"
            
            if rule.description:
                doc += f"  Description: {rule.description}\n"
            
            doc += "\n"
        
        return doc


def create_default_config() -> Dict[str, Any]:
    """Create a default configuration dictionary."""
    return {
        'default_simulator': 'verilator',
        'default_waves': True,
        'rtl_paths': ['rtl'],
        'tb_paths': ['tb/cocotb', 'tb/sv'],
        'build_dir': 'work',
        'include_paths': [],
        'defines': {},
        'systemc_path': None,
        'gtkwave_path': None,
        'verilator_path': None
    }