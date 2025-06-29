import json
from functools import cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple, Union

from agent.libs.mysql_config_validator.variables import VariableDefinition, VariableType


@cache
def read_variable_definitions(db_type: str, version: str | None = None) -> SimpleNamespace:
    """Load variable definitions from JSON file"""
    if version is None:
        version = "11.4" if db_type == "mariadb" else "8.4"
    specs_file = Path(__file__).parent / "variables" / db_type / f"{version}.json"
    with open(specs_file, "r") as f:
        specs_json = json.loads(f.read())
    return SimpleNamespace(**{key: VariableDefinition.from_dict({
        "name": key,
        **spec
    }) for key, spec in specs_json.items()})


def validate_config(
        current_config: Dict[str, Any] | None,
        updates: Dict[str, Any],
        remove_configs: List[str],
        db_type: str,
        version: str | None = None
) -> Tuple[bool, Dict[str, Any], Dict[str, str], bool]:
    """
    Validate a configuration change against the variable definitions.

    Returns:
        bool: True if valid, False if not valid
        dict: The updated configuration
        dict: Validation errors {variable_name: error_message}
        bool: True if restart required for the change
    """
    variable_definitions = read_variable_definitions(db_type, version)

    if current_config is None:
        current_config = {}

    errors = {}
    restart_required = False
    filtered_updates = {}
    new_config = current_config.copy()

    for var_name, new_value in updates.items():
        var_name_lower = var_name.lower()

        # Check if variable exists
        if not hasattr(variable_definitions, var_name_lower):
            errors[var_name] = "Unknown variable"
            continue

        var_def = getattr(variable_definitions, var_name_lower)

        # Check if variable supports SET type (not supported)
        if var_def.type == VariableType.SET:
            errors[var_name] = "SET type variables are not supported"
            continue

        # Check if variable is global (required)
        if not var_def.is_global:
            errors[var_name] = "Only global variables are supported"
            continue

        # Cast the value to appropriate type
        try:
            if var_def.type == VariableType.BOOLEAN:
                if isinstance(new_value, str):
                    casted_value = 1 if new_value.lower() in ["true", "1", "on"] else 0
                elif isinstance(new_value, bool):
                    casted_value = 1 if new_value else 0
                else:
                    casted_value = 1 if int(new_value) != 0 else 0
            elif var_def.type == VariableType.INTEGER:
                casted_value = int(new_value)
            elif var_def.type == VariableType.FLOAT:
                casted_value = float(new_value)
            elif var_def.type == VariableType.TEXT:
                casted_value = str(new_value)
            else:
                errors[var_name] = f"Unsupported variable type: {var_def.type}"
                continue
        except (ValueError, TypeError):
            errors[var_name] = f"Cannot convert '{new_value}' to {var_def.type.value}"
            continue

        # Get current and default values for comparison
        current_value = current_config.get(var_name)
        default_value = var_def.default

        # Cast current and default values for comparison
        casted_current_value = None
        if current_value is not None:
            try:
                if var_def.type == VariableType.BOOLEAN:
                    if isinstance(current_value, str):
                        casted_current_value = 1 if current_value.lower() in ["true", "1", "on"] else 0
                    elif isinstance(current_value, bool):
                        casted_current_value = 1 if current_value else 0
                    else:
                        casted_current_value = 1 if int(current_value) != 0 else 0
                elif var_def.type == VariableType.INTEGER:
                    casted_current_value = int(current_value)
                elif var_def.type == VariableType.FLOAT:
                    casted_current_value = float(current_value)
                elif var_def.type == VariableType.TEXT:
                    casted_current_value = str(current_value)
            except (ValueError, TypeError):
                pass  # Keep as None if casting fails

        casted_default_value = None
        if default_value is not None:
            try:
                if var_def.type == VariableType.BOOLEAN:
                    if isinstance(default_value, str):
                        casted_default_value = 1 if default_value.lower() in ["true", "1", "on"] else 0
                    elif isinstance(default_value, bool):
                        casted_default_value = 1 if default_value else 0
                    else:
                        casted_default_value = 1 if int(default_value) != 0 else 0
                elif var_def.type == VariableType.INTEGER:
                    casted_default_value = int(default_value)
                elif var_def.type == VariableType.FLOAT:
                    casted_default_value = float(default_value)
                elif var_def.type == VariableType.TEXT:
                    casted_default_value = str(default_value)
            except (ValueError, TypeError):
                pass  # Keep as None if casting fails

        # Skip if new value matches current value
        if casted_value == casted_current_value:
            continue

        # Skip if new value matches default value and that's not in the current config
        if casted_value == casted_default_value and var_name not in current_config:
            continue

        # Validate range for numeric types
        if var_def.type in [VariableType.INTEGER, VariableType.FLOAT]:
            if var_def.min_value is not None and casted_value < var_def.min_value:
                errors[var_name] = f"Value {casted_value} below minimum {var_def.min_value}"
                continue
            if var_def.max_value is not None and casted_value > var_def.max_value:
                errors[var_name] = f"Value {casted_value} above maximum {var_def.max_value}"
                continue

        # Check allowed values
        if var_def.allowed_values is not None:
            # Convert casted_value to string for comparison with allowed_values
            str_casted_value = str(casted_value)
            if casted_value not in var_def.allowed_values:
                errors[var_name] = f"Value '{str_casted_value}' not in allowed values: {var_def.allowed_values}"
                continue

        # If we reach here, the value is valid
        filtered_updates[var_name] = casted_value

        # Check if restart is required (non-dynamic variables)
        if not var_def.is_dynamic:
            restart_required = True

    for var_name in remove_configs:
        var_name_lower = var_name.lower()

        # Check if variable exists
        if not hasattr(variable_definitions, var_name_lower):
            errors[var_name] = "Unknown variable"
            continue

        var_def = getattr(variable_definitions, var_name_lower)

        # Check if variable supports SET type (not supported)
        if var_def.type == VariableType.SET:
            errors[var_name] = "SET type variables are not supported"
            continue

        # Check if variable is global (required)
        if not var_def.is_global:
            errors[var_name] = "Only global variables are supported"
            continue

        # Check if restart is required for removal
        if not var_def.is_dynamic:
            restart_required = True

        # Remove the variable from the new configuration
        if var_name in new_config:
            del new_config[var_name]

    # Create the new configuration by merging current with filtered updates
    new_config.update(filtered_updates)

    return len(errors) == 0, new_config, errors, restart_required
