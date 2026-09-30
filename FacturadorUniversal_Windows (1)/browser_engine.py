from pathlib import Path
from playwright.sync_api import sync_playwright

COMMON_BUTTON_WORDS = [
    "facturar", "generar factura", "generar", "emitir", "continuar",
    "obtener factura", "solicitar factura"
]

class BrowserSession:
    def __init__(self, portal_url, data, learner, downloads_dir, callback=None):
        self.portal_url = portal_url
        self.data = data
        self.learner = learner
        self.downloads_dir = Path(downloads_dir)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.callback = callback
        self._event = None
        self.pw = None
        self.browser = None
        self.page = None
        self.fields = []
        self.captcha_detected = False

    def emit(self, payload):
        if self.callback:
            self.callback(payload)

    def open_and_fill(self):
        import threading
        self._event = threading.Event()

        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(headless=False)
        self.page = self.browser.new_page(accept_downloads=True)
        self.page.goto(self.portal_url, wait_until="domcontentloaded", timeout=60000)

        self.fields = self._decorate_fields(self.page.locator("input, select, textarea"))
        self._fill_confident(self.fields)

        body = self.page.locator("body").inner_text(timeout=10000).lower()
        self.captcha_detected = any(x in body for x in [
            "captcha", "recaptcha", "hcaptcha", "verifica que eres humano",
            "no soy un robot"
        ])

        uncertain = [
            f for f in self.fields
            if not f.get("target_field") or f.get("confidence", 0) < 0.63
        ]

        self.emit({
            "type": "ready",
            "fields": self.fields,
            "captcha": self.captcha_detected,
            "uncertain_count": len(uncertain)
        })

        # Espera a que la interfaz indique continuar, por ejemplo después
        # de que el usuario haya resuelto CAPTCHA o guardado una corrección.
        self._event.wait()

        mappings = getattr(self, "human_mappings", {})
        self._apply_human_mappings(mappings)

        # Intento conservador de pulsar una acción de facturación.
        clicked = self._click_invoice_action()
        self.emit({"type": "submitted", "clicked": clicked})

        downloads = self._collect_download_links_and_files()
        self.emit({"type": "downloads", **downloads})
        self.close()

    def continue_now(self, mappings=None):
        self.human_mappings = mappings or {}
        if self._event:
            self._event.set()

    def _decorate_fields(self, locator):
        raw = locator.evaluate_all("""
        els => els.map((e, i) => ({
            index: i,
            tag: e.tagName.toLowerCase(),
            type: e.type || "",
            name: e.name || "",
            id: e.id || "",
            placeholder: e.placeholder || "",
            aria: e.getAttribute("aria-label") || "",
            title: e.title || "",
            autocomplete: e.autocomplete || "",
            text: ((e.labels && e.labels[0]) ? e.labels[0].innerText : "") || ""
        }))
        """)
        out = []
        for f in raw:
            descriptor = " | ".join(str(f.get(k, "")) for k in
                                    ["tag","type","name","id","placeholder","aria","title","autocomplete","text"])
            target, confidence = self.learner.predict(descriptor)
            out.append({**f, "descriptor": descriptor, "target_field": target, "confidence": confidence})
        return out

    def _selector(self, f):
        if f.get("id"):
            return f'#{f["id"]}'
        if f.get("name"):
            return f'[name="{f["name"]}"]'
        if f.get("placeholder"):
            return f'input[placeholder="{f["placeholder"]}"]'
        if f.get("aria"):
            return f'[aria-label="{f["aria"]}"]'
        return f'{f["tag"]}:nth-of-type({f["index"] + 1})'

    def _fill_confident(self, fields):
        for f in fields:
            target = f.get("target_field")
            conf = f.get("confidence", 0)
            if not target or conf < 0.63 or target not in self.data:
                continue
            self._fill_field(f, self.data[target])

    def _apply_human_mappings(self, mappings):
        for f in self.fields:
            target = mappings.get(str(f.get("index")))
            if target and target in self.data:
                self._fill_field(f, self.data[target])

    def _fill_field(self, f, value):
        try:
            el = self.page.locator(self._selector(f)).first
            if f.get("tag") == "select":
                try:
                    el.select_option(label=str(value))
                except Exception:
                    el.select_option(str(value))
            else:
                el.fill(str(value))
        except Exception:
            pass

    def _click_invoice_action(self):
        try:
            buttons = self.page.locator("button, input[type=submit], input[type=button], a")
            count = buttons.count()
            for i in range(min(count, 100)):
                el = buttons.nth(i)
                try:
                    text = (el.inner_text(timeout=300) or el.get_attribute("value") or "").strip().lower()
                except Exception:
                    text = ""
                if any(word in text for word in COMMON_BUTTON_WORDS):
                    el.click(timeout=2000)
                    return text
        except Exception:
            pass
        return ""

    def _collect_download_links_and_files(self):
        result = {"pdf": "", "xml": "", "message": "Proceso terminado."}
        try:
            links = self.page.locator("a").evaluate_all("""
            els => els.map(a => ({href:a.href, text:(a.innerText||"").trim()}))
            """)
            for link in links:
                href = (link.get("href") or "").lower()
                txt = (link.get("text") or "").lower()
                if "xml" in href or "xml" in txt:
                    result["xml"] = link.get("href", "")
                if "pdf" in href or "pdf" in txt:
                    result["pdf"] = link.get("href", "")
        except Exception as e:
            result["message"] = f"Terminó con aviso: {e}"
        return result

    def close(self):
        try:
            if self.browser:
                self.browser.close()
            if self.pw:
                self.pw.stop()
        except Exception:
            pass

class BrowserEngine:
    def start(self, portal_url, data, learner, downloads_dir, callback=None):
        return BrowserSession(portal_url, data, learner, downloads_dir, callback)
