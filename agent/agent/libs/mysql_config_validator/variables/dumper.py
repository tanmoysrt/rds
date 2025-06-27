from typing import Literal


def dump_variables(db_type:Literal["mysql", "mariadb"], version:str):
    image = f"docker.io/{db_type}:{version}"


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 2:
        print("Usage: python variable_info_dump.py <version>")
        sys.exit(1)

    version = sys.argv[1]
    dump_variables(version)
    print(f"Variable information for MySQL version {version} dumped successfully.")
