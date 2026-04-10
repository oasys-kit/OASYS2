"""
popup.py — AI Assistant chat popup
====================================
AIAssistantPopup(QDialog)
  A floating, non-modal, frameless Tool window that appears when the FAB
  is clicked. Contains the full chat interface backed by the Anthropic API.

  Key design choices:
  ───────────────────
  • Qt.Tool | Qt.FramelessWindowHint  → no title bar, stays above canvas
  • Non-modal → user can still interact with OASYS while chatting
  • Draggable by its header bar (mouse press/move events)
  • System prompt built at first-show from the live Orange registry
  • "Draw on Canvas" button injects beamline directly via SchemeEditWidget
"""

import json
import logging
import os.path
import re
import time
from typing import Optional, List, Dict
import ast

import requests

from AnyQt.QtCore import (
    Qt, QThread, pyqtSignal, QObject, QTimer, QSettings,
    QPoint, QEvent
)
from AnyQt.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QScrollArea, QFrame,
    QSizeGrip, QComboBox
)

from orangecanvas import resources

log = logging.getLogger(__name__)

# ── OASYS color palette (matches OASYS2 UI) ──────────────────────────────────

_C = {
    # Backgrounds
    "bg_popup":   "#f0eeea",   # warm off-white (sidebar tone)
    "bg_header":  "#e8e4df",   # slightly darker header
    "bg_input":   "#ffffff",   # white input fields
    "bg_msg_usr": "#ffffff",
    "bg_msg_bot": "#f7f4f0",
    "bg_key_bar": "#ece8e3",
    "bg_draw_btn":"#f0a030",   # OASYS orange (selection highlight color)
    "bg_send_btn":"#f0a030",
    "bg_think":   "#f7f4f0",

    # Borders
    "border_popup":  "#c8c0b8",
    "border_header": "#c0b8b0",
    "border_input":  "#c8c0b8",
    "border_msg_usr":"#d8d0c8",
    "border_msg_bot":"#f0a030",  # orange left-border on assistant bubbles

    # Text
    "text_title":  "#3a2800",   # dark brown (matches OASYS header text)
    "text_msg_usr":"#2a1800",
    "text_msg_bot":"#333333",
    "text_tag":    "#a05000",
    "text_label":  "#666050",
    "text_btn_sec":"#888070",
    "text_key":    "#3a2800",
    "text_think":  "#a07830",

    # Misc
    "tag_bg":      "#fff3d0",
    "tag_border":  "#e0b060",
    "grip_bg":     "transparent",
}

# ─── Registry inspector (identical logic to the widget add-on) ────────────────

class _Registry:
    PREFIXES = (
        "orangecontrib.shadow",
        "orangecontrib.srw",
        "orangecontrib.xoppy",
        "orangecontrib.wofry",
        "orangecontrib.syned",
        "orangecontrib.oasys",
        "oasys.",
    )

    @classmethod
    def get(cls):
        try:
            from orangecanvas.registry import global_registry
            r = global_registry()
            if r is not None:
                return r
        except Exception:
            pass
        try:
            from orangecanvas.application.canvasmain import CanvasMainWindow
            app = QApplication.instance()
            for w in (app.topLevelWidgets() if app else []):
                if isinstance(w, CanvasMainWindow):
                    doc = w.current_document()
                    for a in ("widget_registry", "_registry", "registry",
                              "_SchemeEditWidget__registry"):
                        r = getattr(doc, a, None)
                        if r is not None:
                            return r
        except Exception:
            pass
        return None

    @classmethod
    def _sigs(cls, sigs) -> str:
        parts = []
        for s in (sigs or []):
            n = getattr(s, "name", "?")
            t = getattr(s, "type", None)
            if isinstance(t, str):
                tn = t.split(".")[-1]
            elif t is not None:
                tn = getattr(t, "__name__", str(t))
            else:
                tn = ""
            parts.append(f"{n} ({tn})" if tn else n)
        return ", ".join(parts)

    @classmethod
    def catalog(cls) -> str:
        reg = cls.get()
        if reg is None:
            return ("INSTALLED OASYS WIDGETS: Registry unavailable. "
                    "Click 'Refresh Catalog' after OASYS has loaded.")
        groups: Dict[str, list] = {}
        try:
            all_d = list(reg.widgets())
        except Exception as e:
            return f"INSTALLED OASYS WIDGETS: Enumeration failed: {e}"
        for d in all_d:
            qn = getattr(d, "qualified_name", "") or ""
            if not any(qn.startswith(p) for p in cls.PREFIXES):
                continue
            cat = str(getattr(d, "category", "") or "Uncategorised").strip()
            inp = cls._sigs(getattr(d, "inputs", None))
            out = cls._sigs(getattr(d, "outputs", None))
            groups.setdefault(cat, []).append(
                (getattr(d, "name", "?"), qn, inp, out))
        if not groups:
            return ("INSTALLED OASYS WIDGETS: No OASYS widgets found. "
                    "Install the Shadow4, SRW, or XOPPY add-ons first.")
        lines = [
            "INSTALLED OASYS WIDGETS",
            "(Auto-generated from live registry — authoritative.",
            " Use ONLY these qualified_name and channel values in JSON output.)",
            "",
        ]
        for cat in sorted(groups):
            lines.append(f"## {cat}")
            for name, qn, inp, out in sorted(groups[cat]):
                lines.append(f'  - name: "{name}"')
                lines.append(f'    qualified_name: {qn}')
                if inp: lines.append(f'    inputs:  {inp}')
                if out: lines.append(f'    outputs: {out}')
            lines.append("")
        return "\n".join(lines)

    @classmethod
    def find(cls, reg, qname: str):
        try:
            return reg.widget(qname)
        except Exception:
            pass
        for d in (reg.widgets() or []):
            if getattr(d, "qualified_name", None) == qname:
                return d
        return None


# ── Console prompt reference ──────────────────────────────────────────────────
WORKER_URL = "https://oasys-ai.lucarebuffi.workers.dev"
TEST_MODE = True

def _build_prompt() -> str:
    """Fetch system prompt via the Worker (key is server-side)."""
    try:
        r = requests.get(
            f"{WORKER_URL}/prompt",
            headers={"User-Agent": "OASYS-AI/1.0"},
            timeout=10,
        )
        r.raise_for_status()
        return r.json().get("prompt", "")
    except Exception as e:
        log.warning("Could not fetch prompt from Worker: %s", e)
        return 'Respond ONLY with valid JSON: {"text":"...","beamline":null}'

# ─── Canvas injector ──────────────────────────────────────────────────────────

class _Injector:
    @staticmethod
    def _doc():
        try:
            from orangecanvas.application.canvasmain import CanvasMainWindow
        except ImportError:
            raise RuntimeError("orangecanvas not importable.")
        app = QApplication.instance()
        for w in (app.topLevelWidgets() if app else []):
            if isinstance(w, CanvasMainWindow):
                return w.current_document()
        raise RuntimeError("No open OASYS workflow tab found.")

    @classmethod
    def inject(cls, beamline: Dict) -> Dict:
        if isinstance(beamline, list): beamline = beamline[0] if beamline else {}

        from orangecanvas.scheme import SchemeNode, SchemeLink
        result = {"nodes_added": 0, "skipped": [], "links_added": 0, "links_failed": 0}
        doc = cls._doc()
        reg = _Registry.get()
        if reg is None:
            raise RuntimeError("Widget registry unavailable.")

        node_map: Dict[int, SchemeNode] = {}
        i_node = 0
        for nd in beamline.get("nodes", []):
            qn   = nd.get("qualified_name", "")
            desc = _Registry.find(reg, qn)
            if desc is None:
                log.warning("Not in registry: %s", qn)
                result["skipped"].append(qn)
                continue
            node = SchemeNode(
                description=desc,
                title=nd.get("label") or nd.get("name") or desc.name,
                position=(float(nd.get("x", 100 + i_node*100)), float(nd.get("y", 300))),
            )
            i_node += 1
            try:
                doc.addNode(node)
                node_map[nd["id"]] = node
                result["nodes_added"] += 1

                params = nd.get("parameters")
                if params and isinstance(params, dict):
                    try:
                        print(params)
                        # TODO: parsing of properties according to the widget type
                        #node.properties = params  # Orange stores widget settings here
                        log.debug("Applied %d parameters to %s", len(params), node.title)
                    except Exception as e:
                        log.warning("Could not set parameters on %s: %s", node.title, e)

            except Exception as e:
                log.error("addNode: %s", e)
                result["skipped"].append(qn)

        for lk in beamline.get("links", []):
            src = node_map.get(lk.get("source_node_id"))
            if not src: src = node_map.get(lk.get("source_id"))
            snk = node_map.get(lk.get("sink_node_id"))
            if not snk: snk = node_map.get(lk.get("sink_id"))
            if not src or not snk:
                result["links_failed"] += 1
                continue
            try:
                link = SchemeLink(
                    src, lk.get("source_channel", ""),
                    snk, lk.get("sink_channel", ""),
                )
                doc.addLink(link)
                result["links_added"] += 1
            except Exception as e:
                log.warning("addLink: %s", e)
                result["links_failed"] += 1
        return result


# ─── API worker thread ────────────────────────────────────────────────────────

data_directory = os.path.join(resources.package_dirname("oasys2.canvas.ai"), "data")

class _Worker(QThread):
    done  = pyqtSignal(dict)
    error = pyqtSignal(str)
    URL = WORKER_URL

    MODELS = [
        ["claude-opus-4-5-20251101",  64000],
        ["claude-sonnet-4-5-20250929", 64000],
        ["claude-haiku-4-5-20251001",  64000],
        ["claude-opus-4-6",           128000],
        ["claude-sonnet-4-6",         128000],
    ]

    @staticmethod
    def _open_test_model_file(selected_model: int):
        model, _ = _Worker.MODELS[selected_model]
        with open(os.path.join(data_directory, f"{model}.json"), "r") as f: return json.load(f)

    _selected_model = 2

    def __init__(self, msgs: List[Dict], prompt: str,
                 catalog: str, source_json: str, parent=None):
        super().__init__(parent)
        self._msgs       = msgs
        self._prompt     = prompt
        self._catalog    = catalog
        self._source_json = source_json

    @staticmethod
    def _wrap_user_message(msgs: List[Dict],
                           catalog: str, source_json: str) -> List[Dict]:
        """
        Wrap the last user message with the three XML tags the Console
        prompt expects.  Earlier turns are left untouched so conversation
        history still makes sense.
        """
        if not msgs:
            return msgs
        out = list(msgs)
        last = out[-1]
        if last["role"] == "user":
            out[-1] = {
                "role": "user",
                "content": (
                    f"<oasys-catalog>\n{catalog}\n</oasys-catalog>\n\n"
                    f"<syned-source-file>\n{source_json or '{}'}\n</syned-source-file>\n\n"
                    f"<beamline_requirements>\n{last['content']}\n</beamline_requirements>"
                ),
            }
        return out

    def run(self):
        try:
            if TEST_MODE:
                answer = self._open_test_model_file(self._selected_model)
            else:
                wrapped          = self._wrap_user_message(self._msgs, self._catalog, self._source_json)
                model, max_tokes = self.MODELS[self._selected_model]

                r = requests.post(
                    self.URL,
                    headers={
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                        "User-Agent": "OASYS-AI/1.0",
                    },
                    json={"model": model,
                          "max_tokens": max_tokes,
                          "cache_control": {"type": "ephemeral"},
                          "system": self._prompt,
                          "messages": wrapped},
                    timeout=600,
                )
                r.raise_for_status()
                answer = r.json()

                timestamp = time.time()
                with open(f"{model}_{timestamp}.json", "w") as f: json.dump(answer, f)

            raw = "".join(
                b.get("text", "")
                for b in answer.get("content", [])
                if b.get("type") == "text"
            )

            self.done.emit(self._parse(raw, self._selected_model))
        except requests.HTTPError as e:
            try:
                msg = e.response.json().get("error", {}).get("message", "")
            except Exception:
                msg = str(e)
            self.error.emit(f"HTTP {e.response.status_code}: {msg}")
        except requests.Timeout:
            self.error.emit("Timed out (90 s). Please retry.")
        except requests.ConnectionError:
            self.error.emit("Connection failed — check network.")
        except Exception as e:
            self.error.emit(str(e))

    @staticmethod
    def _parse(raw: str, selected_model) -> Dict:
        raw = raw.strip()

        beamline = None
        display_text = raw

        if selected_model == 2:  # claude-haiku-4-5-20251001
            pass
        elif selected_model in [0, 1, 3, 4]:  # claude-opus-4-5-20251101, claude-sonnet-4-5-20250929, claude-opus-4-6, claude-sonnet-4-6
            tokens = raw.split("```")
            scratchpad_text = tokens[0].strip()
            json_data = tokens[1].strip()[4:]

            beamline = json.loads(json_data)
            display_text = scratchpad_text

            if   "orangecontrib.srw"     in json_data: beamline["engine"] = "SRW"
            elif "orangecontrib.shadow4" in json_data: beamline["engine"] = "Shadow4"
            else:                                      beamline["engine"] = "No Engine"

        return {"text": display_text, "beamline": beamline}


    '''
    @staticmethod
    def _parse(raw: str) -> Dict:
        scratchpad_match = re.search(r"<scratchpad>([\s\S]*?)</scratchpad>", raw)
        scratchpad_text  = scratchpad_match.group(1).strip() if scratchpad_match else ""

        beamline     = None
        display_text = scratchpad_text



        answer_match = re.search(r"<answer>([\s\S]*?)</answer>", raw)
        if answer_match:
            c = answer_match.group(1).strip()
            fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", c)
            if fence_match: c = fence_match.group(1).strip()
            else: pass
            try:
                parsed = json.loads(c)
                if isinstance(parsed, dict):
                    beamline     = parsed.get("beamline")
                    display_text = parsed.get("text", "")
            except json.JSONDecodeError as e:
                print("Error parsing beamline: ", e)

        if not display_text and not beamline:
            c = re.sub(r"^```(?:json)?\s*", "", raw.strip())
            c = re.sub(r"\s*```$", "", c)
            try:
                parsed = json.loads(c)
                return parsed
            except json.JSONDecodeError:
                return {"text": raw, "beamline": None}

        return {"text": display_text, "beamline": beamline}
    '''

# ─── Chat bubble ──────────────────────────────────────────────────────────────

class _Bubble(QFrame):
    def __init__(self, role: str, text: str, tag: str = "", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)

        row = QHBoxLayout(self)
        row.setContentsMargins(4, 1, 4, 1)
        is_user = role == "user"

        av = QLabel("👤" if is_user else "🔬")
        av.setFixedSize(24, 24)
        av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet("border-radius:12px;background:#e8e0d0;border:1px solid #c8b890;")

        bub = QFrame()
        bub.setFrameShape(QFrame.NoFrame)
        bl = QVBoxLayout(bub)
        bl.setContentsMargins(8, 6, 8, 6)
        bl.setSpacing(3)

        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl.setStyleSheet(
            f"color:{_C['text_msg_usr'] if is_user else _C['text_msg_bot']};font-size:12px;line-height:1.55;"
        )
        bl.addWidget(lbl)

        if tag:
            tl = QLabel(f"⚡ {tag}")
            tl.setStyleSheet(
                f"color:{_C['text_tag']};font-size:9px;font-family:monospace;"
                f"background:{_C['tag_bg']};border:1px solid {_C['tag_border']};"
                "border-radius:3px;padding:1px 5px;"

            )
            bl.addWidget(tl)

        bc = _C["border_msg_usr"] if is_user else _C["border_popup"]
        bg = _C["bg_msg_usr"] if is_user else _C["bg_msg_bot"]
        br = "7px 2px 7px 7px" if is_user else "2px 7px 7px 7px"
        bub.setStyleSheet(
            f"QFrame{{background:{bg};border:1px dashed {bc};border-radius:{br};}}"
        )

        if is_user: row.addStretch(); row.addWidget(bub); row.addWidget(av)
        else:       row.addWidget(av); row.addWidget(bub); row.addStretch()


# ─── Main popup dialog ────────────────────────────────────────────────────────

_SETTINGS_ORG = "OASYS"
_SETTINGS_APP = "AIAssistant"
_KEY_GEOMETRY = "popup_geometry"

_POPUP_W = 480
_POPUP_H = 580

class AIAssistantPopup(QDialog):
    """
    Non-modal, frameless floating chat window.

    Lifecycle:
      • Created lazily on first FAB click (parent = CanvasMainWindow)
      • Shown/hidden by subsequent FAB clicks
      • Draggable via its custom header bar
      • Resizable via QSizeGrip in the bottom-right corner
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(
            parent,
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WA_DeleteOnClose, False)  # hide, don't destroy
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._drag_pos: Optional[QPoint] = None
        self._conversation: List[Dict] = []
        self._beamline: Optional[Dict] = None
        self._prompt: Optional[str] = None
        self._worker: Optional[_Worker] = None
        self._source_json_content: str = ""
        self._waiting_for_source: bool = True

        self._settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)

        self.resize(_POPUP_W, _POPUP_H)
        self._build_ui()
        self._restore_geometry()
        self._schedule_catalog()
        self._add_msg("assistant",
                      "OASYS AI Beamline Assistant ready.\n\n"
                      "Type 'browse' to select a SYNED source JSON file, "
                      "or 'skip' to proceed without one."
                      )

    # ── Geometry persistence ─────────────────────────────────────────────

    def _restore_geometry(self) -> None:
        g = self._settings.value(_KEY_GEOMETRY)
        if g:
            self.restoreGeometry(g)

    def _save_geometry(self) -> None:
        self._settings.setValue(_KEY_GEOMETRY, self.saveGeometry())

    def hideEvent(self, event) -> None:
        self._save_geometry()
        super().hideEvent(event)

    # ── UI construction ──────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Root layout — no margins (we draw rounded corners via stylesheet)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Outer frame (rounded, bordered) ──
        frame = QFrame(self)
        frame.setObjectName("PopupFrame")
        frame.setStyleSheet(
            "#PopupFrame{"
            f"  background:{_C['bg_popup']};"
            f"  border:1px solid {_C['border_popup']};"
            "  border-radius:12px;"
            "}"
        )
        root.addWidget(frame)

        fl = QVBoxLayout(frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)

        # ── Draggable header ──
        self._header = self._make_header()
        fl.addWidget(self._header)

        # ── Message scroll area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{background:#e8e4df;width:4px;}"
            "QScrollBar::handle:vertical{background:#c0a060;border-radius:2px;}"
        )
        self._msg_w = QWidget()
        self._msg_w.setStyleSheet("background:transparent;")
        self._msg_layout = QVBoxLayout(self._msg_w)
        self._msg_layout.setContentsMargins(8, 8, 8, 8)
        self._msg_layout.setSpacing(8)
        self._msg_layout.addStretch()
        self._scroll.setWidget(self._msg_w)
        fl.addWidget(self._scroll, 1)

        # ── Thinking indicator ──
        self._thinking = QLabel("🔬  Thinking…")
        self._thinking.setStyleSheet(
            f"color:{_C['text_think']};font-size:11px;font-family:monospace;"
            "background:transparent;padding:4px 12px;"
        )
        self._thinking.setVisible(False)
        fl.addWidget(self._thinking)

        # ── Draw button (appears when a beamline is ready) ──
        self._draw_btn = QPushButton("⊕  Draw on OASYS Canvas")
        self._draw_btn.setVisible(False)
        self._draw_btn.setFixedHeight(32)
        self._draw_btn.setStyleSheet(
            f"QPushButton{{background:{_C['bg_draw_btn']};color:#ffffff;"
            "border:none;font-size:12px;font-weight:bold;margin:0 8px 2px 8px;"
            "border-radius:6px;}"
            "QPushButton:hover{background:#d08820;}"
        )
        self._draw_btn.clicked.connect(self._draw_on_canvas)
        fl.addWidget(self._draw_btn)

        # ── Input row ──
        inp_row = self._make_input_row()
        fl.addWidget(inp_row)

        # ── Resize grip ──
        grip_row = QWidget(frame)
        grip_row.setFixedHeight(16)
        grip_row.setStyleSheet("background:transparent;")
        gl = QHBoxLayout(grip_row)
        gl.setContentsMargins(0, 0, 4, 4)
        gl.addStretch()
        grip = QSizeGrip(self)
        grip.setStyleSheet("background:transparent;")
        gl.addWidget(grip)
        fl.addWidget(grip_row)

    def _make_header(self) -> QFrame:
        hdr = QFrame()
        hdr.setFixedHeight(38)
        hdr.setStyleSheet(
            f"QFrame{{background:{_C['bg_header']};border-top-left-radius:12px;"
            "border-top-right-radius:12px;}"
        )
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(12, 0, 8, 0)

        # Title
        title = QLabel("🔬 OASYS AI Assistant")
        title.setStyleSheet(
            f"color:{_C['text_title']};font-size:13px;font-weight:bold;background:transparent;"

        )
        hl.addWidget(title)
        hl.addStretch()

        # Model selector combobox
        self._model_combo = QComboBox()
        for model_name, _ in _Worker.MODELS:
            self._model_combo.addItem(model_name)
        self._model_combo.setCurrentIndex(_Worker._selected_model)
        self._model_combo.setToolTip("Select Claude model")
        self._model_combo.setStyleSheet(
            "QComboBox{background:#f0eeea;color:#3a2800;border:1px solid #c8c0b8;"
            "border-radius:4px;padding:1px 4px;font-size:10px;max-width:160px;}"
            "QComboBox:hover{border-color:#f0a030;}"
            "QComboBox::drop-down{border:none;width:14px;}"
            "QComboBox QAbstractItemView{background:#f0eeea;color:#3a2800;"
            "selection-background-color:#f0a030;selection-color:#ffffff;}"
        )
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        hl.addWidget(self._model_combo)

        # TEST MODE toggle button
        self._test_btn = QPushButton("TEST")
        self._test_btn.setFixedSize(42, 22)
        self._test_btn.setCheckable(True)
        self._test_btn.setChecked(TEST_MODE)
        self._test_btn.setToolTip("Toggle test mode (uses cached response, no API call)")
        self._update_test_btn_style(self._test_btn.isChecked())
        self._test_btn.toggled.connect(self._on_test_toggled)
        hl.addWidget(self._test_btn)

        # Refresh catalog
        self._ref_btn = QPushButton("↻")
        self._ref_btn.setFixedSize(24, 24)
        self._ref_btn.setToolTip("Refresh widget catalog from registry")
        self._ref_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#a09080;"
            "border:none;font-size:14px;}"
            "QPushButton:hover{color:#f0a030;}"
        )
        self._ref_btn.clicked.connect(self._on_refresh)
        hl.addWidget(self._ref_btn)

        # Close
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#a09080;"
            "border:none;font-size:13px;}"
            "QPushButton:hover{color:#cc3300;}"
        )
        close_btn.clicked.connect(self.hide)
        hl.addWidget(close_btn)

        # Make header draggable
        hdr.mousePressEvent   = self._hdr_press
        hdr.mouseMoveEvent    = self._hdr_move
        hdr.mouseReleaseEvent = self._hdr_release
        return hdr

    def _update_test_btn_style(self, checked: bool) -> None:
        if checked:
            self._test_btn.setStyleSheet(
                "QPushButton{background:#f0a030;color:#ffffff;"
                "border:none;border-radius:4px;font-size:9px;font-weight:bold;}"
                "QPushButton:hover{background:#d08820;}"
            )
        else:
            self._test_btn.setStyleSheet(
                "QPushButton{background:#d0c8c0;color:#666050;"
                "border:none;border-radius:4px;font-size:9px;font-weight:bold;}"
                "QPushButton:hover{background:#b8b0a8;}"
            )

    def _on_test_toggled(self, checked: bool) -> None:
        global TEST_MODE
        TEST_MODE = checked
        self._update_test_btn_style(checked)
        state = "ON" if checked else "OFF"
        log.info("TEST_MODE set to %s", state)

    def _on_model_changed(self, index: int) -> None:
        _Worker._selected_model = index
        model_name = _Worker.MODELS[index][0]
        log.info("Model changed to: %s", model_name)

    def _make_input_row(self) -> QFrame:
        row = QFrame()
        row.setStyleSheet(
            f"QFrame{{background:{_C['bg_key_bar']};border-top:1px solid {_C['border_input']};"
            "border-bottom-left-radius:12px;border-bottom-right-radius:12px;}"
        )
        rl = QHBoxLayout(row)
        rl.setContentsMargins(8, 6, 8, 6)
        rl.setSpacing(6)

        self._input = QTextEdit()
        self._input.setPlaceholderText("Describe your beamline… (Ctrl+Enter to send)")
        self._input.setFixedHeight(54)
        self._input.setStyleSheet(
            f"QTextEdit{{background:{_C['bg_input']};color:#333333;"
            f"border:1px solid {_C['border_input']};border-radius:5px;"
            "padding:4px 8px;font-size:12px;}"
            "QTextEdit:focus{border-color:#f0a030;}"
        )
        self._input.installEventFilter(self)

        self._send_btn = QPushButton("↑")
        self._send_btn.setFixedSize(54, 54)
        self._send_btn.setStyleSheet(
            f"QPushButton{{background:{_C['bg_send_btn']};color:#ffffff;"
            "border:none;border-radius:5px;font-size:18px;font-weight:bold;}"
            "QPushButton:hover{background:#1a5a9a;}"
            "QPushButton:disabled{background:#d8d0c0;color:#a09080;}"
        )
        self._send_btn.clicked.connect(self._on_send)
        rl.addWidget(self._input)
        rl.addWidget(self._send_btn)
        return row

    # ── Header drag ──────────────────────────────────────────────────────

    def _hdr_press(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def _hdr_move(self, event) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)

    def _hdr_release(self, _event) -> None:
        self._drag_pos = None

    # ── Event filter (Ctrl+Enter) ────────────────────────────────────────

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._input and event.type() == QEvent.KeyPress:
            if (event.key() == Qt.Key_Return
                    and event.modifiers() & Qt.ControlModifier):
                self._on_send()
                return True
        return super().eventFilter(obj, event)

    # ── Catalog ──────────────────────────────────────────────────────────

    def _schedule_catalog(self) -> None:
        QTimer.singleShot(500, lambda: self._refresh_prompt())

    def _refresh_prompt(self) -> None:
        self._prompt = _build_prompt()
        n = self._prompt.count("qualified_name:")
        log.info("AI popup: prompt fetched, %d widgets in catalog.", n)

    def _on_refresh(self) -> None:
        self._refresh_prompt()
        self._add_msg("assistant", "Prompt refreshed from Anthropic Console.")

        # ── Source file loading ───────────────────────────────────────────────

    def _open_source_dialog(self) -> None:
        from AnyQt.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SYNED source JSON file",
            "",
            "JSON files (*.json);;All files (*.*)",
        )
        if path:
            self._load_source_from_path(path)
        else:
            # User cancelled the dialog
            self._add_msg("assistant",
                          "No file selected.\n\n"
                          "Type 'browse' to open the dialog again, "
                          "or 'skip' to proceed without a source file."
                          )

    def _load_source_from_path(self, path: str) -> None:
        import os, json as _json

        path = path.strip().strip('"').strip("'")

        if path.lower() == "browse":
            self._open_source_dialog()
            return

        if path.lower() == "skip":
            self._source_json_content = ""
            self._waiting_for_source = False
            self._add_msg("assistant",
                          "Proceeding without a source file — the prompt will use "
                          "its default source parameters.\n\n"
                          "Describe your experiment — technique, energy range, "
                          "required resolution or focal spot size — and I will design "
                          "the beamline layout."
                          )
            return

        if not os.path.isfile(path):
            self._add_msg("assistant",
                          f"File not found:\n  {path}\n\n"
                          "Please check the path and try again."
                          )
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = _json.load(f)
            self._source_json_content = _json.dumps(data, indent=2)
            self._waiting_for_source = False
            log.info("SYNED source loaded: %s", path)
            self._add_msg("assistant",
                          f"Source file loaded: {os.path.basename(path)}\n\n"
                          "Now describe your experiment — technique, energy range, "
                          "required resolution or focal spot size — and I will design "
                          "the beamline layout."
                          )
        except _json.JSONDecodeError as e:
            self._add_msg("assistant",
                          f"The file at:\n  {path}\n"
                          f"is not valid JSON:\n  {e}\n\n"
                          "Please provide a valid SYNED JSON file."
                          )
        except Exception as e:
            self._add_msg("assistant",
                          f"Could not read the file:\n  {e}\n\nPlease try again."
                          )

    # ── Messages ─────────────────────────────────────────────────────────

    def _add_msg(self, role: str, text: str, beamline: Optional[Dict] = None) -> None:
        tag = ""
        if beamline:
            n   = len(beamline.get("nodes", []))
            tag = (f"{beamline.get('engine','?')} · {n} widgets · "
                   f"{beamline.get('title','')}")
        w = _Bubble(role, text, tag, parent=self._msg_w)
        self._msg_layout.insertWidget(self._msg_layout.count() - 1, w)
        QTimer.singleShot(
            40, lambda: self._scroll.verticalScrollBar().setValue(
                self._scroll.verticalScrollBar().maximum()
            )
        )

    # ── Send / receive ───────────────────────────────────────────────────

    def _on_send(self) -> None:
        text = self._input.toPlainText().strip()
        if not text: return

        self._input.clear()
        self._add_msg("user", text)

        # ── Waiting for the SYNED file path ──────────────────────────────
        if self._waiting_for_source:
            self._load_source_from_path(text)
            return

        # ── Normal chat flow ──────────────────────────────────────────────
        if self._prompt is None: self._refresh_prompt()

        self._conversation.append({"role": "user", "content": text})
        self._send_btn.setEnabled(False)
        self._thinking.setVisible(True)

        self._worker = _Worker(
            list(self._conversation),
            self._prompt,
            catalog=_Registry.catalog(),
            source_json=self._source_json_content,
            parent=self,
        )

        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.done.connect(lambda _: self._worker.deleteLater())
        self._worker.error.connect(lambda _: self._worker.deleteLater())
        self._worker.start()

    def _on_done(self, parsed: Dict) -> None:
        self._thinking.setVisible(False)
        self._send_btn.setEnabled(True)

        text     = parsed.get("text", "")
        beamline = parsed.get("beamline")

        if isinstance(beamline, list): beamline = beamline[0] if beamline else None

        self._add_msg("assistant", text, beamline)
        self._conversation.append({
            "role": "assistant",
            "content": json.dumps({"text": text, "beamline": beamline},
                                  ensure_ascii=False),
        })
        if beamline:
            self._beamline = beamline
            self._draw_btn.setVisible(True)
            self._draw_btn.setText(
                f"⊕  Draw on Canvas  [{beamline.get('engine','?')} · "
                f"{len(beamline.get('nodes',[]))} widgets]"
            )

    def _on_error(self, msg: str) -> None:
        self._thinking.setVisible(False)
        self._send_btn.setEnabled(True)
        self._add_msg("assistant", f"API error:\n{msg}")

    # ── Draw on canvas ───────────────────────────────────────────────────

    def _draw_on_canvas(self) -> None:
        if not self._beamline:
            return
        try:
            result = _Injector.inject(self._beamline)
        except RuntimeError as e:
            self._add_msg("assistant", f"Canvas error:\n{e}")
            return

        na = result["nodes_added"]
        la = result["links_added"]
        sk = result["skipped"]
        msg = f"Drew {na} widgets and {la} links on the canvas."
        if sk:
            msg += (f"\n\nNot found in registry (add-on not installed?):\n"
                    + "\n".join(f"  • {q}" for q in sk))
        self._add_msg("assistant", msg)