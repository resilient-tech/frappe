# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
import re
from io import BytesIO

import xlrd
from xlsxwriter.workbook import Workbook as wkb
import pylightxl

import frappe
from frappe.utils.html_utils import unescape_html

ILLEGAL_CHARACTERS_RE = re.compile(r'[\000-\010]|[\013-\014]|[\016-\037]')


# return xlsx file object
def make_xlsx(data, sheet_name, wb=None, column_widths=None):
	column_widths = column_widths or []
	flag = False if column_widths else True 
	xlsx_file = BytesIO()
	if wb is None:
		wb = wkb(xlsx_file)

	ws = wb.add_worksheet(sheet_name)

	bold_format = wb.add_format({'bold': True})
	bold_format.set_font_name('Calibri')
	ws.set_row(0,None,bold_format)

	idr = 0
	for row in data:
		for item in row:
			if isinstance(item, str) and (sheet_name not in ['Data Import Template', 'Data Export']):
				value = handle_html(item)
			else:
				value = item

			if isinstance(item, str) and next(ILLEGAL_CHARACTERS_RE.finditer(value), None):
				value = re.sub(ILLEGAL_CHARACTERS_RE, '', value)

			ws.write(idr, row.index(item), value)
			if flag:
				get_column_widths(column_widths,row.index(item),str(value))
			
		idr+=1

	if column_widths:
		 for i, column_width in enumerate(column_widths):
				if column_width > 0:
					ws.set_column(i, i, column_width)
	wb.close()
	return xlsx_file


def handle_html(data):
	from html2text import HTML2Text

	# return if no html tags found
	data = frappe.as_unicode(data)

	if '<' not in data or '>' not in data:
		return data

	h = unescape_html(data or "")

	obj = HTML2Text()
	obj.ignore_links = True
	obj.body_width = 0

	try:
		value = obj.handle(h)
	except Exception:
		# unable to parse html, send it raw
		return data

	value = ", ".join(value.split('  \n'))
	value = " ".join(value.split('\n'))
	value = ", ".join(value.split('# '))

	return value


def read_xlsx_file_from_attached_file(file_url=None, fcontent=None, filepath=None):
	if file_url:
		_file = frappe.get_doc("File", {"file_url": file_url})
		filename = _file.get_full_path()
	elif fcontent:
		filename = BytesIO(fcontent)
	elif filepath:
		filename = filepath
	else:
		return

	rows = []
	wb1 = pylightxl.readxl(fn=filename)
	ws1 = wb1.ws(wb1.ws_names[0])#migt not be the active one || search on the net man.
	for row in ws1.rows:
		tmp_list = []
		for cell in row:
			tmp_list.append(cell)
		rows.append(tmp_list)
	return rows


def read_xls_file_from_attached_file(content):
	book = xlrd.open_workbook(file_contents=content)
	sheets = book.sheets()
	sheet = sheets[0]
	rows = []
	for i in range(sheet.nrows):
		rows.append(sheet.row_values(i))
	return rows


def build_xlsx_response(data, filename):
	xlsx_file = make_xlsx(data, filename)
	# write out response as a xlsx type
	frappe.response['filename'] = filename + '.xlsx'
	frappe.response['filecontent'] = xlsx_file.getvalue()
	frappe.response['type'] = 'binary'
	
def get_column_widths(column_widths,idc,val):
	try:
		column_widths[idc]
		if column_widths[idc] < len(val):
				column_widths[idc] = len(val)
	except:
		column_widths.append(len(val))

	return column_widths