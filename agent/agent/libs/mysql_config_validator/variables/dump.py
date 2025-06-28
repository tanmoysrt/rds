from dataclasses import dataclass
from enum import Enum

from typing import Any, Dict, List, Optional, Union

class DatabaseType(Enum):
    MYSQL = "mysql"
    MARIADB = "mariadb"

class VariableType(Enum):
    BOOLEAN = "bool"
    INTEGER = "int"
    FLOAT = "float"
    TEXT = "text"
    SET = "set"

@dataclass
class VariableDefinition:
    name: str
    type: VariableType
    default: Optional[Union[int, float, bool, str, List[str]]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    allowed_values: Optional[List[str]] = None
    is_dynamic: bool = False
    is_global: bool = False
    is_session: bool = False
    platform_specific: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "default": self.default,
            "min": self.min_value,
            "max": self.max_value,
            "allowed_values": self.allowed_values,
            "is_dynamic": self.is_dynamic,
            "is_global": self.is_global,
            "is_session": self.is_session
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "VariableDefinition":
        return VariableDefinition(
            name=d.get("name", ""),
            type=VariableType(d["type"]),
            default=d.get("default"),
            min_value=d.get("min"),
            max_value=d.get("max"),
            allowed_values=d.get("allowed_values"),
            is_dynamic=d.get("is_dynamic", False),
            is_global=d.get("is_global", False),
            is_session=d.get("is_session", False),
            platform_specific=d.get("platform_specific")
        )

class VariableDumper:
    def __init__(self, db_type: DatabaseType, version: str = "latest"):
        self.db_type = db_type
        self.version = version
        self.variables: Dict[str, VariableDefinition] = {}

    def collect_and_save(self) -> None:
        if self.db_type == DatabaseType.MYSQL:
            self._dump_mysql_variables()
        elif self.db_type == DatabaseType.MARIADB:
            self._dump_mariadb_variables()

        self._save_to_file()

    # MySQL specific
    # Scrap the MySQL documentation pages for variable specs
    def _dump_mysql_variables(self) -> None:
        urls = [
            f"https://dev.mysql.com/doc/refman/{self.version}/en/server-system-variables.html",
            f"https://dev.mysql.com/doc/refman/{self.version}/en/innodb-parameters.html",
            f"https://dev.mysql.com/doc/refman/{self.version}/en/performance-schema-system-variables.html"
        ]

        for url in urls:
            self._parse_mysql_doc_page(url)

    def _parse_mysql_doc_page(self, url: str) -> None:
        import requests
        from bs4 import BeautifulSoup

        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        for var in soup.find_all('li', class_='listitem'):
            table = var.find('table')
            if not table:
                continue

            var_data = self._extract_mysql_var_data(table)
            if var_data and var_data.name:
                # Skip SET type variables for MySQL as requested
                if var_data.type == VariableType.SET:
                    continue
                self.variables[var_data.name] = var_data

    def _extract_mysql_var_data(self, table) -> Optional[VariableDefinition]:
        """Extract variable data from a MySQL documentation table"""
        data = {
            'name': None,
            'type': VariableType.TEXT,
            'default': None,
            'min_value': None,
            'max_value': None,
            'allowed_values': None,
            'is_dynamic': False,
            'is_global': False,
            'is_session': False,
            'platform_specific': None
        }

        # Track all max value variants we find
        max_value_candidates = []

        for row in table.find_all('tr'):
            th = row.find('th')
            td = row.find('td')

            if not th or not td:
                continue

            th_text = th.get_text(strip=True)
            td_text = td.get_text(strip=True)

            if th_text == "System Variable":
                data['name'] = td_text.lower()
            elif th_text == "Scope":
                data['is_global'] = "Global" in td_text
                data['is_session'] = "Session" in td_text
            elif th_text == "Dynamic":
                data['is_dynamic'] = "Yes" in td_text
            elif th_text == "Type":
                data['type'] = self._map_mysql_type(td_text)
            elif th_text == "Default Value":
                # Handle empty string explicitly
                if td_text.lower() == "empty string":
                    data['default'] = ""
                else:
                    data['default'] = self._format_value(td_text, data['type'])
            elif th_text in ["Minimum Value", "Minimum Value (64-bit platforms)"]:
                if data['min_value'] is None or "64-bit" in th_text:
                    data['min_value'] = self._evaluate_expression(td_text, data['type'])
            elif "Maximum Value" in th_text:
                # Collect all maximum value variants
                value = self._evaluate_expression(td_text, data['type'])
                if value is not None:
                    max_value_candidates.append((self._get_platform_priority(th_text), value))
            elif th_text == "Valid Values":
                literals = td.find_all('code', class_='literal')
                if literals:
                    data['allowed_values'] = [lit.get_text(strip=True) for lit in literals]
            elif th_text == "Platform Specific":
                data['platform_specific'] = td_text

        if not data['name']:
            return None

        # Select the highest maximum value from all candidates
        if max_value_candidates:
            max_value_candidates.sort(reverse=True)  # Sort by platform priority
            data['max_value'] = max_value_candidates[0][1]  # Take the highest priority value

        return VariableDefinition(**data)

    def _evaluate_expression(self, expr: str, var_type: VariableType) -> Optional[Union[int, float]]:
        import ast

        """Evaluate mathematical expressions in min/max values"""
        if not expr or expr.lower() in ["none", "null"]:
            return None

        try:
            # Handle special cases
            if expr.lower() == "empty string":
                return ""

            # Clean up parenthetical explanations - extract just the numeric part
            if "(" in expr and ")" in expr:
                # Extract everything before the first parenthesis
                expr = expr.split("(")[0].strip()

            # Remove any trailing commas or semicolons
            expr = expr.rstrip(",;").strip()

            # Try to parse as a simple number first
            try:
                if var_type == VariableType.INTEGER:
                    return int(expr)
                elif var_type == VariableType.FLOAT:
                    return float(expr)
            except ValueError:
                pass

            # Evaluate mathematical expressions
            if any(op in expr for op in ["+", "-", "*", "/", "**", "^"]):
                # Replace ^ with ** for exponentiation
                expr = expr.replace("^", "**")
                # Evaluate safely using ast
                node = ast.parse(expr, mode="eval")
                if isinstance(node, ast.Expression):
                    value = eval(compile(node, "<string>", "eval"), {"__builtins__": None}, {})
                    if var_type == VariableType.INTEGER:
                        return int(value)
                    return float(value)

            # Fall back to normal formatting if not an expression
            return self._format_value(expr, var_type)
        except:
            return self._format_value(expr, var_type)

    def _get_platform_priority(self, platform_text: str) -> int:
        """Determine priority of platform-specific maximum values"""
        platform_text = platform_text.lower()
        if "64-bit" in platform_text:
            return 2
        if "32-bit" in platform_text:
            return 1
        return 0

    # MariaDB specific
    def _dump_mariadb_variables(self) -> None:
        from agent.libs.tmp_db_container import TmpDBContainer

        """Dump MariaDB variables using a temporary container"""
        with TmpDBContainer("mariadb", tag=self.version, auto_start=True) as container:
            db_conn = container.get_db()
            output = db_conn.query(
                "SELECT * FROM information_schema.system_variables",
                as_dict=True
            )

            for row in output:
                var_data = self._extract_mariadb_var_data(row)
                if var_data and var_data.name:
                    # Skip FLAGSET type variables as requested (already handled in mapping)
                    self.variables[var_data.name] = var_data

    def _extract_mariadb_var_data(self, row: Dict) -> Optional[VariableDefinition]:
        """Extract variable data from MariaDB system_variables query"""
        var_type = {
            "VARCHAR": VariableType.TEXT,
            "BOOLEAN": VariableType.BOOLEAN,
            "SET": VariableType.SET,
            "ENUM": VariableType.TEXT,
            "INT": VariableType.INTEGER,
            "INT UNSIGNED": VariableType.INTEGER,
            "BIGINT": VariableType.INTEGER,
            "BIGINT UNSIGNED": VariableType.INTEGER,
            "DOUBLE": VariableType.FLOAT
        }.get(row['VARIABLE_TYPE'])
        if var_type is None:  # This will skip FLAGSET types
            return None

        # Handle empty string defaults
        default_value = row['DEFAULT_VALUE']
        if isinstance(default_value, str) and default_value.lower() == "empty string":
            default_value = ""

        allowed_values = (
            [self._format_value(v, var_type)
             for v in self._format_value(row.get('ENUM_VALUE_LIST'), VariableType.SET, default=[])]
            if var_type != VariableType.SET
            else self._format_value(row.get('ENUM_VALUE_LIST'), VariableType.SET, default=[])
        )

        return VariableDefinition(
            name=row['VARIABLE_NAME'].lower(),
            type=var_type,
            default=self._format_value(default_value, var_type),
            min_value=self._evaluate_expression(row.get('NUMERIC_MIN_VALUE'), var_type),
            max_value=self._evaluate_expression(row.get('NUMERIC_MAX_VALUE'), var_type),
            allowed_values=allowed_values if allowed_values else None,
            is_dynamic=row['READ_ONLY'] == 'NO',
            is_global="GLOBAL" in str(row['VARIABLE_SCOPE']),
            is_session="SESSION" in str(row['VARIABLE_SCOPE']),
        )

    def _map_mysql_type(self, mysql_type: str) -> VariableType:
        mysql_type = mysql_type.lower()
        if "boolean" in mysql_type:
            return VariableType.BOOLEAN
        if "integer" in mysql_type:
            return VariableType.INTEGER
        if "numeric" in mysql_type:
            return VariableType.FLOAT
        if "set" in mysql_type:
            return VariableType.SET
        return VariableType.TEXT

    def _format_value(self,
                      val: Union[str, None],
                      val_type: VariableType,
                      default=None) -> Union[int, float, bool, str, List[str], None]:
        """Format a raw value according to its type"""
        if val is None or val == "NULL":
            return default

        try:
            if val_type == VariableType.INTEGER:
                return int(val)
            if val_type == VariableType.FLOAT:
                return float(val)
            if val_type == VariableType.BOOLEAN:
                return int(val.upper() in ["TRUE", "1", "ON", "true"])
            if val_type == VariableType.TEXT:
                return str(val)
            if val_type == VariableType.SET:
                if not val:
                    return []
                return [v.strip() for v in val.split(',')]
        except (ValueError, AttributeError):
            return val

    def _save_to_file(self) -> None:
        import json
        from pathlib import Path

        output = {
            var_name: var_def.to_dict()
            for var_name, var_def in self.variables.items()
        }

        filename = Path(__file__).parent / self.db_type.value / f"{self.version}.json"
        with open(filename, "w") as f:
            json.dump(output, f, indent=4, ensure_ascii=False)

if __name__ == '__main__':
    import sys

    if len(sys.argv) != 3:
        print("Usage: python dump.py <mysql/mariadb> <version>")
        sys.exit(1)

    try:
        db_type = DatabaseType(sys.argv[1].lower())
        version = sys.argv[2]

        dumper = VariableDumper(db_type, version)
        dumper.collect_and_save()

        print(f"Variable information for {db_type.value} version {version} dumped successfully.")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
