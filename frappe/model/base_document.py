# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

import frappe
from frappe import _, _dict
from frappe.modules import load_doctype_module

DOCTYPE_TABLE_FIELDS = [
	_dict(fieldname="fields", options="DocField"),
	_dict(fieldname="permissions", options="DocPerm"),
	_dict(fieldname="actions", options="DocType Action"),
	_dict(fieldname="links", options="DocType Link"),
	_dict(fieldname="states", options="DocType State"),
]

TABLE_DOCTYPES_FOR_DOCTYPE = {df["fieldname"]: df["options"] for df in DOCTYPE_TABLE_FIELDS}
DOCTYPES_FOR_DOCTYPE = {"DocType", *TABLE_DOCTYPES_FOR_DOCTYPE.values()}

max_positive_value = {"smallint": 2**15 - 1, "int": 2**31 - 1, "bigint": 2**63 - 1}


def get_controller(doctype):
	"""Return the locally cached **class** object of the given DocType.

	For `custom` type, return `frappe.model.document.Document`.

	:param doctype: DocType name as string.
	"""

	if frappe.local.dev_server or frappe.flags.in_migrate:
		return import_controller(doctype)

	site_controllers = frappe.controllers.setdefault(frappe.local.site, {})
	if doctype not in site_controllers:
		site_controllers[doctype] = import_controller(doctype)

	return site_controllers[doctype]


def import_controller(doctype):
	from frappe.model.document import Document
	from frappe.utils.nestedset import NestedSet

	module_name = "Core"
	if doctype not in DOCTYPES_FOR_DOCTYPE:
		doctype_info = frappe.db.get_value("DocType", doctype, fieldname="*")
		if doctype_info:
			if doctype_info.custom:
				return NestedSet if doctype_info.is_tree else Document
			module_name = doctype_info.module

	module_path = None
	class_overrides = frappe.get_hooks("override_doctype_class")
	if class_overrides and class_overrides.get(doctype):
		import_path = class_overrides[doctype][-1]
		module_path, classname = import_path.rsplit(".", 1)
		module = frappe.get_module(module_path)

	else:
		module = load_doctype_module(doctype, module_name)
		classname = doctype.replace(" ", "").replace("-", "")

	class_ = getattr(module, classname, None)
	if class_ is None:
		raise ImportError(
			doctype
			if module_path is None
			else f"{doctype}: {classname} does not exist in module {module_path}"
		)

	if not issubclass(class_, BaseDocument):
		raise ImportError(f"{doctype}: {classname} is not a subclass of BaseDocument")

	return class_
