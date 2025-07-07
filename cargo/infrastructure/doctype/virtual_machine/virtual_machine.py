# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from cargo.infrastructure import Ansible


class VirtualMachine(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        cluster: DF.Data
        instance_id: DF.Data | None
        private_ip: DF.Data | None
        provider: DF.Literal["Generic", "Press"]
        public_ip: DF.Data | None
        ssh_non_root_public_key: DF.Code | None
        ssh_non_root_user: DF.Data
        ssh_port: DF.Int
        ssh_root_public_key: DF.Code | None
        ssh_root_user: DF.Data
        status: DF.Literal["Draft", "Pending", "Started", "Stopped", "Terminated"]
    # end: auto-generated types

    @frappe.whitelist()
    def ping(self):
        self.ansible("ping.yml").run()

    def ansible(self, playbook: str, variables: dict | None = None, run_as_root_user: bool = True):
        return Ansible(self, playbook=playbook, variables=variables, run_as_root_user=run_as_root_user)
