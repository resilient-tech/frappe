# Copyright (c) 2022, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DocumentTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		data: DF.Code | None
		reference_doctype: DF.Link | None
		template_name: DF.Data | None
	# end: auto-generated types
	pass

	def validate(self):
		frappe.has_permission(self.reference_doctype, "write", throw=True)
		frappe.has_permission(self.reference_doctype, "create", throw=True)
