# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import ast
from typing import Dict, List

import frappe
from frappe.model.document import Document
from frappe.utils.safe_exec import safe_exec
from frappe import _


class ServerScript(Document):
    def validate(self):
        frappe.only_for("Script Manager", True)
        self.validate_script()
        self.sync_scheduled_jobs()
        self.clear_scheduled_events()

    def on_update(self):
        frappe.cache().delete_value("server_script_map")
        self.sync_scheduler_events()

    def on_trash(self):
        if self.script_type == "Scheduler Event":
            for job in self.scheduled_jobs:
                frappe.delete_doc("Scheduled Job Type", job.name)

    @property
    def scheduled_jobs(self) -> List[Dict[str, str]]:
        return frappe.get_all(
            "Scheduled Job Type",
            filters={"server_script": self.name},
            fields=["name", "stopped"],
        )

    def validate_script(self):
        """Utilizes the ast module to check for syntax errors"""
        ast.parse(self.script)

    def sync_scheduled_jobs(self):
        """Sync Scheduled Job Type statuses if Server Script's disabled status is changed"""
        if self.script_type != "Scheduler Event" or not self.has_value_changed(
            "disabled"
        ):
            return

        for scheduled_job in self.scheduled_jobs:
            if bool(scheduled_job.stopped) != bool(self.disabled):
                job = frappe.get_doc("Scheduled Job Type", scheduled_job.name)
                job.stopped = self.disabled
                job.save()

    def sync_scheduler_events(self):
        """Create or update Scheduled Job Type documents for Scheduler Event Server Scripts"""
        if (
            not self.disabled
            and self.event_frequency
            and self.script_type == "Scheduler Event"
        ):
            setup_scheduler_events(
                script_name=self.name, frequency=self.event_frequency
            )

    def clear_scheduled_events(self):
        """Deletes existing scheduled jobs by Server Script if self.event_frequency has changed"""
        if self.script_type == "Scheduler Event" and self.has_value_changed(
            "event_frequency"
        ):
            for scheduled_job in self.scheduled_jobs:
                frappe.delete_doc("Scheduled Job Type", scheduled_job.name)

    def execute_method(self) -> Dict:
        """Specific to API endpoint Server Scripts

        Raises:
                frappe.DoesNotExistError: If self.script_type is not API
                frappe.PermissionError: If self.allow_guest is unset for API accessed by Guest user

        Returns:
                dict: Evaluates self.script with frappe.utils.safe_exec.safe_exec and returns the flags set in it's safe globals
        """
        # wrong report type!
        if self.script_type != "API":
            raise frappe.DoesNotExistError

        # validate if guest is allowed
        if frappe.session.user == "Guest" and not self.allow_guest:
            raise frappe.PermissionError

        # output can be stored in flags
        _globals, _locals = safe_exec(self.script)
        return _globals.frappe.flags

    def execute_doc(self, doc: Document):
        """Specific to Document Event triggered Server Scripts

        Args:
                doc (Document): Executes script with for a certain document's events
        """
        safe_exec(self.script, _locals={"doc": doc})

    def execute_scheduled_method(self):
        """Specific to Scheduled Jobs via Server Scripts

        Raises:
                frappe.DoesNotExistError: If script type is not a scheduler event
        """
        if self.script_type != "Scheduler Event":
            raise frappe.DoesNotExistError

        safe_exec(self.script)

    def get_permission_query_conditions(self, user: str) -> List[str]:
        """Specific to Permission Query Server Scripts

        Args:
                user (str): Takes user email to execute script and return list of conditions

        Returns:
                list: Returns list of conditions defined by rules in self.script
        """
        locals = {"user": user, "conditions": ""}
        safe_exec(self.script, None, locals)
        if locals["conditions"]:
            return locals["conditions"]


@frappe.whitelist()
def setup_scheduler_events(script_name, frequency):
    """Creates or Updates Scheduled Job Type documents based on the specified script name and frequency

    Args:
            script_name (str): Name of the Server Script document
            frequency (str): Event label compatible with the Frappe scheduler
    """
    method = frappe.scrub(f"{script_name}-{frequency}")
    scheduled_script = frappe.db.get_value("Scheduled Job Type", {"method": method})

    if not scheduled_script:
        frappe.get_doc(
            {
                "doctype": "Scheduled Job Type",
                "method": method,
                "frequency": frequency,
                "server_script": script_name,
            }
        ).insert()

        frappe.msgprint(
            _("Enabled scheduled execution for script {0}").format(script_name)
        )

    else:
        doc = frappe.get_doc("Scheduled Job Type", scheduled_script)

        if doc.frequency == frequency:
            return

        doc.frequency = frequency
        doc.save()

        frappe.msgprint(
            _("Scheduled execution for script {0} has updated").format(script_name)
        )
