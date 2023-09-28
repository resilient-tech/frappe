frappe.ui.form.DocumentTemplate = class DocumentTemplate {
	constructor(opts) {
		$.extend(this, opts);
		this.doctype = this.frm.doctype;
		this.template_wrapper = this.wrapper.find(".document-template");
		this.templates = [];

		if (this.doctype == "DocType" || (!this.frm.is_new() && this.frm.doc.docstatus != 0)) {
			this.wrapper.toggle(false);
			return;
		}

		this.make();
		this.bind();
		this.refresh();
	}

	make() {
		// init dom
		this.template_wrapper.html(`
			<li class="input-area"></li>
			<li class="saved-templates"></li>
			<li class="sidebar-action">
				<a class="saved-templates-preview">${__("Show Saved Templates")}</a>
			</li>
		`);

		this.$input_area = this.template_wrapper.find(".input-area");
		this.$saved_templates = this.template_wrapper.find(".saved-templates").hide();
		this.$saved_templates_preview = this.template_wrapper.find(".saved-templates-preview");
		this.saved_templates_hidden = true;

		this.template_input = frappe.ui.form.make_control({
			df: {
				fieldtype: "Data",
				placeholder: __("Template Name"),
				input_class: "input-xs",
			},
			parent: this.$input_area,
			render_input: true,
		});
	}

	bind() {
		this.bind_save_template();
		this.bind_toggle_saved_templates();
		this.bind_click_template();
		this.bind_sync_templates();
		this.bind_remove_template();
	}

	refresh() {
		this.get_templates_list().then(() => {
			this.templates.length
				? this.$saved_templates_preview.show()
				: this.$saved_templates_preview.hide();
			const html = this.templates.map((template) => this.filter_template(template));
			this.template_wrapper.find(".filter-pill").remove();
			this.$saved_templates.append(html);
		});

		this.template_input.set_description("");
	}

	filter_template(template) {
		const template_name =
			template.template_name.length > 15
				? template.template_name.slice(0, 15) + "..."
				: template.template_name;

		return `
			<button class="list-link filter-pill list-sidebar-button data-pill btn" data-name="${
				template.name
			}">
				<a class="ellipsis template-name">${template_name}</a>
				<a class="mr-4 sync close">${frappe.utils.icon("es-line-reload")}</a>
				<a class="remove close">${frappe.utils.icon("close")}</a>
			</button>
		`;
	}

	bind_save_template() {
		this.template_input.$input.keydown(
			frappe.utils.debounce((e) => {
				const template_name = this.template_input.get_value();
				const has_value = Boolean(template_name);

				if (e.which === frappe.ui.keyCode["ENTER"]) {
					if (!has_value || this.template_exists(template_name)) return;

					this.template_input.set_value("");
					this.save_template(template_name).then(() => this.refresh());
					this.toggle_saved_templates(true);
				} else {
					let help_text = __("Press Enter to save");

					if (this.template_exists(template_name)) {
						help_text = __("Duplicate Template Name");
					}

					this.template_input.set_description(has_value ? help_text : "");
				}
			}, 300)
		);
	}

	bind_click_template() {
		this.template_wrapper.on("click", ".filter-pill .template-name", (e) => {
			let $template = $(e.currentTarget).parent(".filter-pill");
			this.set_applied_template($template);
			const name = $template.attr("data-name");

			try {
				this.get_template_data(name);
				let doc = JSON.parse(this.template_data);
				if (doc.doctype) {
					e.preventDefault();
					const sleep = frappe.utils.sleep;

					frappe.dom.freeze(__("Copying {0}", [doc.doctype]) + "...");
					sleep(300).then(() => {
						if (!this.frm.doc.__islocal) {
							let res = frappe.model.with_doctype(doc.doctype, () => {
								let newdoc = frappe.model.copy_doc(doc);
								newdoc.idx = null;
								newdoc.__run_link_triggers = false;
								frappe.set_route("Form", newdoc.doctype, newdoc.name);
								frappe.dom.unfreeze();
							});
							res && res.fail(frappe.dom.unfreeze);
						} else {
							let newdoc = this.update_existing_doc(doc);
							newdoc.__run_link_triggers = false;
							frappe.dom.unfreeze();
							this.frm.refresh_fields();
						}
					});
				}
			} catch (e) {
				//
			}
		});
	}

	bind_sync_templates() {
		this.template_wrapper.on("click", ".filter-pill .sync", (e) => {
			let $template = $(e.currentTarget).closest(".filter-pill");
			const filter_label = $template.text().trim();

			frappe.confirm(
				__("Are you sure you want to Update the {0} template?", [filter_label.bold()]),
				() => {
					const name = $template.attr("data-name");
					this.update_template(name).then(() => this.refresh());
				}
			);
		});
	}

	bind_remove_template() {
		this.template_wrapper.on("click", ".filter-pill .remove", (e) => {
			let $template = $(e.currentTarget).closest(".filter-pill");
			const filter_label = $template.text().trim();

			frappe.confirm(
				__("Are you sure you want to remove the {0} template?", [filter_label.bold()]),
				() => {
					const name = $template.attr("data-name");
					const applied_templates = this.get_template_values(name);
					$template.remove();
					this.remove_template(name).then(() => this.refresh());
				}
			);
		});
	}

	bind_toggle_saved_templates() {
		this.$saved_templates_preview.click(() => {
			this.toggle_saved_templates(this.saved_templates_hidden);
		});
	}

	toggle_saved_templates(show) {
		this.$saved_templates.toggle(show);
		const label = show ? __("Hide Saved") : __("Show Saved Templates");
		this.$saved_templates_preview.text(label);
		this.saved_templates_hidden = !this.saved_templates_hidden;
	}

	template_exists(template_name) {
		return (this.templates || []).find((f) => f.template_name === template_name);
	}

	save_template(template_name) {
		return frappe.db.insert({
			doctype: "Document Template",
			reference_doctype: this.doctype,
			template_name,
			data: JSON.stringify(this.frm.doc),
		});
	}

	update_template(template_name) {
		return frappe.db.set_value(
			"Document Template",
			template_name,
			"data",
			JSON.stringify(this.frm.doc)
		);
	}

	get_template_values(template_name) {
		const template = this.templates.find((template) => template.name === template_name);
		return JSON.parse(template.templates || "[]");
	}

	get_templates_list() {
		return frappe.db
			.get_list("Document Template", {
				fields: ["name", "template_name", "data"],
				filters: { reference_doctype: this.doctype },
			})
			.then((templates) => {
				this.templates = templates || [];
			});
	}

	set_applied_template($template) {
		this.$saved_templates
			.find(".btn-primary-light")
			.toggleClass("btn-primary-light btn-default");
		$template.toggleClass("btn-default btn-primary-light");
	}

	get_template_data(template_name) {
		const template = this.templates.find((template) => template.name === template_name);
		this.template_data = template.data;
	}

	remove_template(template_name) {
		if (!template_name) return;
		return frappe.db.delete_doc("Document Template", template_name);
	}

	update_existing_doc(doc, from_amend, parent_doc, parentfield) {
		var no_copy_list = ["name", "amended_from", "amendment_date", "cancel_reason"];

		var newdoc;

		if (!parentfield) {
			newdoc = frappe.get_doc(doc.doctype, this.frm.doc.name);
		} else {
			newdoc = frappe.model.get_new_doc(doc.doctype, parent_doc, parentfield);
		}

		for (var key in doc) {
			// dont copy name and blank fields
			var df = frappe.meta.get_docfield(doc.doctype, key);

			if (
				df &&
				key.substr(0, 2) != "__" &&
				!in_list(no_copy_list, key) &&
				!(df && !from_amend && cint(df.no_copy) == 1)
			) {
				var value = doc[key] || [];
				if (frappe.model.table_fields.includes(df.fieldtype)) {
					for (var i = 0, j = value.length; i < j; i++) {
						var d = value[i];
						this.update_existing_doc(d, from_amend, newdoc, df.fieldname);
					}
				} else {
					newdoc[key] = doc[key];
				}
			}
		}
		newdoc.lft = null;
		newdoc.rgt = null;
		return newdoc;
	}
};
