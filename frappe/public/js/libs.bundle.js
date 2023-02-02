import "./jquery-bootstrap";
import "./lib/moment";
import Sortable from "sortablejs";
import * as DOMPurify from "dompurify";

window.SetVueGlobals = (app) => {
	app.config.globalProperties.__ = window.__;
	app.config.globalProperties.frappe = window.frappe;
};
window.Sortable = Sortable;
window.DOMPurify = DOMPurify;
