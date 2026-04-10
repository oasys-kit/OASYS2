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
import re
from typing import Optional, List, Dict

import requests

from AnyQt.QtCore import (
    Qt, QThread, pyqtSignal, QObject, QTimer, QSettings,
    QPoint, QEvent
)
from AnyQt.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton, QScrollArea, QFrame,
    QSizeGrip
)

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
TEST_CLAUDE_ANSWER = r"""
{
  "id": "msg_01Nj4GmSXB32ezdUCbNzYAsv",
  "type": "message",
  "role": "assistant",
  "model": "claude-haiku-4-5-20251001",
  "content": [
    {
      "type": "text",
      "text": "<scratchpad>\nLet me analyze the requirements systematically:\n\n**User Requirements:**\n- Powder diffraction beamline (XRPD)\n- 45 meters long total\n- Energy resolution ~0.1%\n- Focusing: 20 μm (H) × 10 μm (V) spot size\n\n**From SYNED Source File:**\n- Undulator U2.5 source (vertical undulator)\n- Electron beam energy: 6 GeV\n- Emittance (H): εx ~ 2.19e-10 m·rad\n- Emittance (V): εy ~ 1.37e-11 m·rad (much lower, good for horizontal focusing)\n- Undulator: K_v = 1.120664, period = 21 mm, 219 periods\n- This is a relatively low-K vertical undulator\n\n**Technique Analysis - XRPD:**\n- Powder diffraction requires high angular resolution (not energy)\n- But 0.1% energy resolution is achievable with Si(111) DCM\n- Synchrotron allows small sample, good resolution\n- Spot size of 20×10 μm suggests moderate focusing (not nanofocusing)\n- This is a typical high-resolution diffraction beamline\n\n**Source Characteristics:**\n- The undulator is primarily vertical, so it's optimized for horizontal polarization\n- At 6 GeV and K~1.12, the fundamental peak wavelength will be in the hard X-ray range (8-20 keV region)\n- For powder diffraction, typically operate at 15-21 keV for good penetration and resolution\n\n**Energy and Harmonic Selection:**\n- For 0.1% resolution, need a channel-cut Si(111) DCM or Si(333) or Si(999) for higher orders\n- Si(111) at ~17 keV would give ~50 eV bandwidth with modest detuning\n- Need to reject harmonics (3rd order from undulator), so first mirror should have energy bandwidth cutoff\n\n**Beamline Layout (45 m total):**\n1. **Undulator (0 m)**: Source location, ~5 m effective length\n2. **First Mirror M1 (5 m)**: Collimating mirror, vertical focusing in vertical direction, rejects harmonics\n   - Purpose: Collimate and harmonic rejection\n   - Shape: Plane mirror (typical for collimation)\n   - Coating: Rh or Pt for good reflectivity in hard X-ray\n   - Angle: Small grazing angle (~3-4 mrad) for harmonic rejection\n   \n3. **Slit S1 (7 m)**: Define aperture after M1\n   \n4. **DCM (Double Crystal Monochromator) (9 m)**: Si(111) symmetric cut\n   - Two channel-cut crystals or separate crystals\n   - Energy resolution ~50 eV bandwidth\n   \n5. **Second Mirror M2 (12 m)**: Post-DCM focusing mirror\n   - Purpose: Horizontal focusing to sample (Kirk-Patrick-Baez or toroidal)\n   - Need to focus from large source (undulator) to 20 μm spot\n   \n6. **Slit S2 (14 m)**: Guard slits after M2\n   \n7. **Slit S3 (18 m)**: Define sample aperture\n   \n8. **Sample Position (18-20 m)**: Diffraction setup\n   \n9. **Detector (beyond 20 m)**: Detection arms for powder diffraction\n\nWait, this is only ~20 m used and we have 45 m available. Let me reconsider:\n\nActually, for high-resolution powder diffraction with good collimation, we might want:\n- Longer collimation section (better collimation of undulator beam)\n- Longer distance between sample and detector for detector coverage (powder rings)\n\nLet me revise:\n\n**Better Layout (45 m):**\n1. **Undulator source (0 m)** \n2. **First Harmonic Rejection Mirror M1 (6 m)**: Vertical collimating, plane mirror\n   - Rejects 3rd harmonic\n3. **Slit S1 (8 m)**: Aperture definition\n4. **DCM (10 m)**: Si(111) symmetrical, E ~ 17 keV\n5. **Second Mirror M2 - Horizontal focusing (15 m)**: Elliptical mirror\n   - Focus horizontal beam to 20 μm at sample\n   - Vertical beam stays ~large (10 μm defined separately)\n6. **Guard Slits S2 (17 m)**: Collimate divergence after M2\n7. **Sample Position (18 m)**: Powder diffraction geometry\n8. **Large detector space**: 18-45 m for detector positioning\n\n**Key Physics Decisions:**\n- Use Shadow4 for ray-tracing (geometric optics, flux, aberrations)\n- Use SRW for coherence and undulator radiation properties\n- Use XOPPY for DCM reflectivity and crystal optics\n- Could use Hybrid to correct focusing aberrations if needed\n- High-resolution diffraction doesn't need full coherence, so geometry matters most\n\n**Energy Estimate:**\n- With K_v = 1.12 and λ_u = 0.021 m, at E_beam = 6 GeV\n- Resonance energy E_res = (Ec²·2γ²)/(1+K²/2) where γ = E/m_e\n- γ = 6000/0.511 = 11,740\n- Ec = (e·B·c)/(2π·m_e·c²) where B relates to K\n- For a vertical undulator, K = 0.93·B·λ_u (B in Tesla)\n- K = 1.12 → B ~ 0.054 T\n- This is a low-field undulator good for medium energies\n\n- For Si(111) at E ~ 17 keV: θ_B ~ 8.05°, gives good angular acceptance\n\n**Beam Size Calculation:**\n- At sample (18 m from source):\n  - Horizontal focus: need to reduce large undulator beam to 20 μm\n  - Vertical: use the small emittance and drift + slits to get 10 μm\n  - M2 should be elliptical in horizontal direction\n  - Vertical can be plane or minimal focusing (natural emittance)\n\nThis layout is reasonable and achievable.\n</scratchpad>\n\n<answer>\n```json\n{\n  \"text\": \"High-resolution powder X-ray diffraction (XRPD) beamline design for the APS U2.5 undulator. The 45-meter layout uses a vertical undulator source (6 GeV, K_v=1.12) to produce tuneable hard X-rays (15–21 keV range). A two-mirror scheme (harmonic rejection + horizontal focusing) combined with a Si(111) DCM achieves <0.1% energy resolution. The design delivers a 20 μm (H) × 10 μm (V) focal spot at 18 m from source, suitable for high-resolution Bragg diffraction. Ray-tracing with Shadow4 will model flux and aberrations; SRW characterizes coherence and undulator spectrum; XOPPY calculates crystal reflectivity and harmonic content. The remaining ~27 m allows detector arm rotation for full powder ring coverage (high 2θ angles to 150° or more).\",\n  \n  \"beamline\": {\n    \"title\": \"45-m High-Resolution Powder Diffraction Beamline (U2.5 Undulator)\",\n    \"engine\": \"Shadow4\",\n    \"description\": \"Vertical undulator source → harmonic rejection mirror → Si(111) DCM → horizontal focusing mirror → sample position (18 m), with detector space extending to 45 m for powder ring collection.\",\n    \n    \"source_specification\": {\n      \"SOURCE_TYPE\": \"Undulator\",\n      \"SOURCE_NAME\": \"U2.5\",\n      \"ELECTRON_BEAM_ENERGY_GeV\": 6.0,\n      \"ELECTRON_BEAM_CURRENT_mA\": 0.2,\n      \"K_VERTICAL\": 1.120664,\n      \"K_HORIZONTAL\": 0.0,\n      \"UNDULATOR_PERIOD_mm\": 21.0,\n      \"NUMBER_OF_PERIODS\": 219.0,\n      \"EMITTANCE_H_nm_rad\": 0.219,\n      \"EMITTANCE_V_nm_rad\": 0.01369,\n      \"SOURCE_ENERGY_RANGE_keV\": \"15–21 (tunable, optimized for 17 keV)\",\n      \"EXPECTED_UNDULATOR_PEAK_ENERGY_keV\": 17.5,\n      \"HORIZONTAL_SOURCE_SIZE_μm\": 45,\n      \"VERTICAL_SOURCE_SIZE_μm\": 12\n    },\n\n    \"nodes\": [\n      {\n        \"id\": 0,\n        \"name\": \"Undulator U2.5 Source\",\n        \"type\": \"source\",\n        \"qualified_name\": \"orangecontrib.srw.widgets.light_sources.ow_srw_undulator.OWSRWUndulator\",\n        \"label\": \"Undulator @0 m\",\n        \"x\": 60,\n        \"y\": 300,\n        \"description\": \"6 GeV electron beam, vertical undulator with K=1.12, 219 periods, 21 mm period length. Produces highly brilliant hard X-rays, fundamental peak ~17.5 keV.\"\n      },\n\n      {\n        \"id\": 1,\n        \"name\": \"First Mirror - Harmonic Rejection and Vertical Collimation (M1)\",\n        \"type\": \"mirror\",\n        \"qualified_name\": \"orangecontrib.shadow4.widgets.optics.ow_mirror.OWMirror\",\n        \"label\": \"M1: HR Mirror @6 m\",\n        \"x\": 240,\n        \"y\": 300,\n        \"description\": \"Plane mirror for harmonic rejection and vertical collimation. High-order rejector with controlled cutoff energy.\",\n        \"parameters\": {\n          \"MIRROR_1_POSITION_m\": 6.0,\n          \"MIRROR_1_TYPE\": \"plane\",\n          \"MIRROR_1_LENGTH_mm\": 200,\n          \"MIRROR_1_WIDTH_mm\": 30,\n          \"MIRROR_1_GRAZING_ANGLE_mrad\": 3.5,\n          \"MIRROR_1_GRAZING_ANGLE_deg\": 0.20,\n          \"MIRROR_1_COATING\": \"Platinum (Pt)\",\n          \"MIRROR_1_ORIENTATION\": \"horizontal deflection (vertical acceptance)\",\n          \"MIRROR_1_PURPOSE\": \"Harmonic rejection (rejects 3rd order), vertical collimation\",\n          \"MIRROR_1_ENERGY_CUTOFF_keV\": 22.0\n        }\n      },\n\n      {\n        \"id\": 2,\n        \"name\": \"Slit 1 - Primary Aperture\",\n        \"type\": \"aperture\",\n        \"qualified_name\": \"orangecontrib.shadow4.widgets.optics.ow_screen_slits.OWScreenSlits\",\n        \"label\": \"S1: Primary @8 m\",\n        \"x\": 420,\n        \"y\": 300,\n        \"description\": \"Define primary aperture after harmonic rejection mirror. Reduces divergence and defines acceptance.\",\n        \"parameters\": {\n          \"SLIT_1_POSITION_m\": 8.0,\n          \"SLIT_1_H_OPENING_mm\": 2.0,\n          \"SLIT_1_V_OPENING_mm\": 0.8,\n          \"SLIT_1_PURPOSE\": \"Aperture definition, reduce angular divergence for DCM acceptance\"\n        }\n      },\n\n      {\n        \"id\": 3,\n        \"name\": \"Double Crystal Monochromator - Si(111)\",\n        \"type\": \"crystal\",\n        \"qualified_name\": \"orangecontrib.shadow4.widgets.optics.ow_crystal.OWCrystal\",\n        \"label\": \"DCM Si(111) @10 m\",\n        \"x\": 600,\n        \"y\": 300,\n        \"description\": \"Symmetric cut Si(111) DCM for high energy resolution (~50 eV at 17 keV, ΔE/E ~ 0.3% natural width, narrowed to 0.1% by detuning). Channel-cut or separate crystals.\",\n        \"parameters\": {\n          \"CRYSTAL_POSITION_m\": 10.0,\n          \"CRYSTAL_MATERIAL\": \"Silicon\",\n          \"CRYSTAL_PLANES\": \"111\",\n          \"CRYSTAL_CUT\": \"symmetric (Bragg)\",\n          \"BRAGG_ANGLE_deg\": 8.05,\n          \"OPERATIONAL_ENERGY_keV\": 17.0,\n          \"CRYSTAL_LENGTH_mm\": 100,\n          \"CRYSTAL_WIDTH_mm\": 10,\n          \"DETUNING_RATIO_C\": \"~0.5 (for 0.1% resolution)\",\n          \"ENERGY_RESOLUTION_ΔE_eV\": 17,\n          \"ENERGY_RESOLUTION_RELATIVE\": 0.001,\n          \"CRYSTAL_CONFIGURATION\": \"asymmetric geometry optional (α=-30° for horizontal magnification)\"\n        }\n      },\n\n      {\n        \"id\": 4,\n        \"name\": \"Second Mirror - Horizontal Focusing (M2)\",\n        \"type\": \"mirror\",\n        \"qualified_name\": \"orangecontrib.shadow4.widgets.optics.ow_mirror.OWMirror\",\n        \"label\": \"M2: H-Focus @15 m\",\n        \"x\": 960,\n        \"y\": 300,\n        \"description\": \"Elliptical mirror for horizontal beam focusing. Demagnifies large undulator beam (45 μm at 15 m conjugate) to ~20 μm at sample (18 m, magnification ~0.4). Vertical remains uncollimated or weakly focused.\",\n        \"parameters\": {\n          \"MIRROR_2_POSITION_m\": 15.0,\n          \"MIRROR_2_TYPE\": \"elliptical\",\n          \"MIRROR_2_SHAPE\": \"elliptical (horizontal focusing, vertical plane)\",\n          \"MIRROR_2_P_DISTANCE_m\": 5.0,\n          \"MIRROR_2_Q_DISTANCE_m\": 3.0,\n          \"MIRROR_2_MAGNIFICATION_H\": 0.4,\n          \"MIRROR_2_LENGTH_mm\": 150,\n          \"MIRROR_2_WIDTH_mm\": 25,\n          \"MIRROR_2_GRAZING_ANGLE_mrad\": 3.5,\n          \"MIRROR_2_COATING\": \"Rhodium (Rh)\",\n          \"MIRROR_2_FOCAL_LENGTH_H_m\": 3.0,\n          \"MIRROR_2_FOCAL_SPOT_AT_SAMPLE_H_μm\": 20,\n          \"MIRROR_2_PURPOSE\": \"Horizontal focusing, demagnification to sample\"\n        }\n      },\n\n      {\n        \"id\": 5,\n        \"name\": \"Guard Slits - Post-Mirror\",\n        \"type\": \"aperture\",\n        \"qualified_name\": \"orangecontrib.shadow4.widgets.optics.ow_screen_slits.OWScreenSlits\",\n        \"label\": \"S2: Guard @17 m\",\n        \"x\": 1140,\n        \"y\": 300,\n        \"description\": \"Guard slits to remove aberrated rays and define final divergence before sample.\",\n        \"parameters\": {\n          \"SLIT_2_POSITION_m\": 17.0,\n          \"SLIT_2_H_OPENING_mm\": 0.3,\n          \"SLIT_2_V_OPENING_mm\": 0.3,\n          \"SLIT_2_PURPOSE\": \"Remove tails, define final divergence and aperture\"\n        }\n      },\n\n      {\n        \"id\": 6,\n        \"name\": \"Sample Slits and Sample Position\",\n        \"type\": \"screen\",\n        \"qualified_name\": \"orangecontrib.shadow4.widgets.optics.ow_screen_slits.OWScreenSlits\",\n        \"label\": \"Sample @18 m\",\n        \"x\": 1320,\n        \"y\": 300,\n        \"description\": \"Powder diffraction sample at 18 m from source. Beam characteristics optimized for high-resolution Bragg geometry.\",\n        \"parameters\": {\n          \"SAMPLE_POSITION_m\": 18.0,\n          \"SAMPLE_SLIT_H_μm\": 20,\n          \"SAMPLE_SLIT_V_μm\": 10,\n          \"BEAM_SIZE_AT_SAMPLE_H_μm\": 20,\n          \"BEAM_SIZE_AT_SAMPLE_V_μm\": 10,\n          \"BEAM_DIVERGENCE_H_μrad\": 2.0,\n          \"BEAM_DIVERGENCE_V_μrad\": 1.5,\n          \"EXPECTED_FLUX_photons_s\": 1e12,\n          \"COHERENCE_H\": \"partial (coherence length ~0.5 μm)\",\n          \"COHERENCE_V\": \"high (coherence length ~5 μm)\",\n          \"GEOMETRY\": \"Standard Bragg geometry (θ-2θ or θ-θ), tunable energy\"\n        }\n      },\n\n      {\n        \"id\": 7,\n        \"name\": \"Detector Arm - Extended Range\",\n        \"type\": \"screen\",\n        \"qualified_name\": \"orangecontrib.shadow4.widgets.tools.ow_plot_xy.PlotXY\",\n        \"label\": \"Detector Zone\",\n        \"x\": 1500,\n        \"y\": 300,\n        \"description\": \"Detector positioning volume from 18 m to 45 m (27 m available). Allows rotation of detector arm for powder diffraction rings (up to ~150° 2θ for hard X-rays). Can accommodate area detectors (Pilatus, PerkinElmer) or scintillation detectors.\",\n        \"parameters\": {\n          \"DETECTOR_ARM_LENGTH_m\": 27.0,\n          \"AVAILABLE_2THETA_RANGE_deg\": \"up to 150°\",\n          \"SAMPLE_TO_DETECTOR_TYPICAL_m\": 0.5,\n          \"DETECTOR_COVERAGE_AREA\": \"Area detector (2D) or point detector with rotation\"\n        }\n      }\n    ],\n\n    \"links\": [\n      {\n        \"id\": 0,\n        \"source_node_id\": 0,\n        \"sink_node_id\": 1,\n        \"source_channel\": \"SRW Data\",\n        \"sink_channel\": \"SRW Data\"\n      },\n      {\n        \"id\": 1,\n        \"source_node_id\": 1,\n        \"sink_node_id\": 2,\n        \"source_channel\": \"Shadow Data\",\n        \"sink_channel\": \"Shadow Data\"\n      },\n      {\n        \"id\": 2,\n        \"source_node_id\": 2,\n        \"sink_node_id\": 3,\n        \"source_channel\": \"Shadow Data\",\n        \"sink_channel\": \"Shadow Data\"\n      },\n      {\n        \"id\": 3,\n        \"source_node_id\": 3,\n        \"sink_node_id\": 4,\n        \"source_channel\": \"Shadow Data\",\n        \"sink_channel\": \"Shadow Data\"\n      },\n      {\n        \"id\": 4,\n        \"source_node_id\": 4,\n        \"sink_node_id\": 5,\n        \"source_channel\": \"Shadow Data\",\n        \"sink_channel\": \"Shadow Data\"\n      },\n      {\n        \"id\": 5,\n        \"source_node_id\": 5,\n        \"sink_node_id\": 6,\n        \"source_channel\": \"Shadow Data\",\n        \"sink_channel\": \"Shadow Data\"\n      },\n      {\n        \"id\": 6,\n        \"source_node_id\": 6,\n        \"sink_node_id\": 7,\n        \"source_channel\": \"Shadow Data\",\n        \"sink_channel\": \"Shadow Data\"\n      }\n    ]\n  },\n\n  \"oasys_simulation_guidance\": {\n    \"workflow_strategy\": \"Multi-stage hybrid approach\",\n    \n    \"stage_1_source_characterization\": {\n      \"tool\": \"SRW (Synchrotron Radiation Workshop)\",\n      \"purpose\": \"Model undulator radiation spectrum, brilliance, and coherence properties\",\n      \"steps\": [\n        \"1. Use SRW Undulator widget with parameters from SYNED file (K_v=1.12, period=21 mm, 219 periods)\",\n        \"2. Generate radiation at E = 17 keV (fundamental peak ~17.5 keV), scan ±10% around resonance\",\n        \"3. Calculate far-field intensity distribution and angular acceptance\",\n        \"4. Extract coherence properties (coherence length, degree of coherence) for both H and V directions\",\n        \"5. Export SRW data for compatibility with Shadow4 ray-tracing\"\n      ],\n      \"key_metrics\": [\n        \"Brilliance (photons/s/mm²/mrad² at 0.1% BW)\",\n        \"Coherence lengths: λc_H ≈ 0.5 μm, λc_V ≈ 5 μm\",\n        \"Angular divergence: σ_H ≈ 1.5 μrad, σ_V ≈ 0.3 μrad\",\n        \"Harmonic content (1st, 3rd, 5th orders)\"\n      ]\n    },\n\n    \"stage_2_harmonic_rejection_and_collimation\": {\n      \"tool\": \"Shadow4 (ray tracing) + XOPPY (reflectivity database)\",\n      \"purpose\": \"Design and optimize harmonic rejection mirror (M1) and collimation section\",\n      \"steps\": [\n        \"1. Calculate Pt reflectivity curve vs. energy at 3.5 mrad grazing angle using XOPPY/PREREFL\",\n        \"2. Determine reflectivity envelope and harmonic cutoff (should suppress 3rd harmonic ~52 keV to <5%)\",\n        \"3. Use Shadow4 Geometrical Source or connect SRW output to trace rays through M1\",\n        \"4. Optimize mirror length (200 mm) and grazing angle (3.5 mrad) for:\",\n        \"   - Maximum 1st harmonic transmission (>95% assumed at Pt, 17 keV, 3.5 mrad)\",\n        \"   - Vertical collimation (divergence reduction from ~0.3 μrad natural to <0.1 μrad)\",\n        \"5. Post-mirror divergence should be limited by slit S1 (0.8 mm vertical opening at 8 m → ~0.1 mrad)\"\n      ],\n      \"key_metrics\": [\n        \"1st harmonic reflectivity at 17 keV: >95%\",\n        \"3rd harmonic (52 keV) reflectivity: <5%\",\n        \"Vertical divergence after M1: <0.1 mrad\",\n        \"Integrated flux after M1: >90% of incident\"\n      ]\n    },\n\n    \"stage_3_monochromator_energy_resolution\": {\n      \"tool\": \"XOPPY (Crystal optics - CRYSTAL widget) + Shadow4\",\n      \"purpose\": \"Design and verify Si(111) DCM for 0.1% energy resolution\",\n      \"steps\": [\n        \"1. Use XOPPY CRYSTAL widget to compute Si(111) Darwin curve at 17 keV:\",\n        \"   - Input: E=17 keV, crystal=Si, reflection 111, T=293 K\",\n        \"   - Output: Bragg angle (θ_B ≈ 8.05°), Darwin width (~6 arcsec ≈ 0.03 mrad)\",\n        \"2. Calculate energy bandwidth from Darwin width and temperature factors\",\n        \"3. Assess symmetric Bragg geometry: natural bandwidth ΔE/E ≈ 0.3% (too broad)\",\n        \"4. Apply detuning: use partial backscatter geometry or asymmetric cut (C parameter ~0.5)\",\n        \"   - This reduces bandwidth to ~0.1% while accepting small incident divergence\",\n        \"5. Simulate with Shadow4: ray-trace incident beam (from S1) through both crystals\",\n        \"   - Monitor energy spread of transmitted rays\",\n        \"   - Optimize crystal separation and orientation for symmetric/asymmetric geometry\",\n        \"6. Verify crystal aperture (100 mm length × 10 mm width) accepts collimated beam without clipping\"\n      ],\n      \"key_metrics\": [\n        \"Energy resolution ΔE/E: 0.1% (ΔE ≈ 17 eV at 17 keV)\",\n        \"Energy bandwidth: ~3× Darwin width by detuning\",\n        \"Angular acceptance: ±10 μrad (compatible with S1 divergence)\",\n        \"Transmitted flux: >70% (2 crystals × ~95% each ≈ 90%, minus Darwin curve shape losses)\"\n      ]\n    },\n\n    \"stage_4_focusing_and_aberration_correction\": {\n      \"tool\": \"Shadow4 (primary) + Hybrid (aberration correction if needed)\",\n      \"purpose\": \"Design horizontal focusing mirror (M2) to achieve 20 μm spot at sample\",\n      \"steps\": [\n        \"1. Compute undulator/source size at M2 conjugate (15 m from source):\",\n        \"   - Horizontal size ≈ σ_src_H + (p × σ_H_angle) ≈ 22 μm + (15 m × 1.5 μrad) ≈ 45 μm\",\n        \"2. Design elliptical mirror M2 for demagnification M_H ≈ 0.4:\",\n        \"   - Source distance p = 5.0 m (actual optical distance, accounting for grazing angle deflection)\",\n        \"   - Image distance q = 3.0 m (from M2 at 15 m to sample at 18 m)\",\n        \"   - Focal length calculation: 1/f = (1/p + 1/q) / sin(grazing_angle) ≈ 1/3 m\",\n        \"   - Ellipse semi-axes computed from p, q, and mirror length L=150 mm\",\n        \"3. Use Rh coating (better reflectivity than Pt in hard X-ray, smooth surface)\",\n        \"4. Simulate with Shadow4:\",\n        \"   - Ray-trace collimated beam from DCM through M2\",\n        \"   - Monitor spot size at sample plane (should converge to ~20 μm H × natural V)\",\n        \"5. If aberrations (spherical, coma) cause spot enlargement >20%, use Hybrid mode:\",\n        \"   - Apply wave-optics correction (WOFRY or SRW) at M2 to compensate diffraction-limited aberrations\",\n        \"   - Typically not needed for this geometry (low NA, geometric optics sufficient)\"\n      ],\n      \"key_metrics\": [\n        \"Horizontal focal spot: 20 μm (FWHM or 80% enclosed energy)\",\n        \"Vertical spot: natural divergence + slit (effectively 10 μm from S2 overlap)\",\n        \"M2 figure tolerance: <0.1 μm RMS slope error (achievable with modern mirrors)\",\n        \"Demagnification: M_H = q/p ≈ 0.4 reduces source size from 45 μm to ~18 μm focal spot\",\n        \"Aberrations (spherical, coma): <2 μm contribution at focus\"\n      ]\n    },\n\n    \"stage_5_sample_and_detector_integration\": {\n      \"tool\": \"Shadow4 (beam characterization) + experimental station setup\",\n      \"purpose\": \"Define sample position, scattering geometry, and detector placement\",\n      \"steps\": [\n        \"1. Place sample at 18 m from source:\",\n        \"   - Horizontal slit: 20 μm (defines sample footprint or reduces beam)\",\n        \"   - Vertical slit: 10 μm (guard slit S2 already at 17 m, reduces tails)\",\n        \"2. Use Bragg geometry (θ-2θ typical for powder diffraction):\",\n        \"   - θ (incident angle) ≈ θ_B for the DCM energy (8.05° for Si(111) at 17 keV)\",\n        \"   - Sample rotated in θ, detector at 2θ\",\n        \"3. Detector placement:\",\n        \"   - Primary diffraction rings: 2θ ≈ 30° to 150° (requires 0.5–2 m sample-to-detector distance)\",\n        \"   - Use area detector (e.g., Pilatus 100K, Dectris) for full powder rings, or\",\n        \"   - Point detector on θ-2θ stage for line scans and high resolution\",\n        \"4. Verify no vignetting or obstruction by optical elements in scattering plane\",\n        \"5. Include guard collimation (post-sample slits) if needed to protect detector from direct beam\"\n      ],\n      \"key_metrics\": [\n        \"Sample position: 18 m from source\",\n        \"Incident beam FWHM: 20 μm (H) × 10 μm (V)\",\n        \"Bragg angle: 8.05° (for Si(111) at 17 keV, tunable with energy)\",\n        \"Scattering geometry: standard laboratory frame, θ-2θ or θ-θ\",\n        \"Detector Q-resolution: ΔQ/Q ≈ 1e-4 (limited by energy resolution and angular acceptance)\"\n      ]\n    },\n\n    \"stage_6_validation_and_optimization\": {\n      \"tool\": \"Shadow4 end-to-end simulation, comparison with known beamline parameters\",\n      \"purpose\": \"Validate complete beamline design before commissioning\",\n      \"steps\": [\n        \"1. Run full end-to-end Shadow4 simulation:\",\n        \"   - Start from Grid Source or SRW output (from Stage 1)\",\n        \"   - Ray-trace through M1, S1, DCM (two crystals), M2, S2, to sample/detector plane\",\n        \"   - Monitor: flux at each optical element, beam size, divergence, energy spectrum\",\n        \"2. Compare results to ESRF ID31 or similar high-resolution XRPD beamlines:\",\n        \"   - Expected flux at sample: ~1e12 photons/s in 0.1% BW (depends on DCM transmission)\",\n        \"   - Spot size: 20×10 μm (design target)\",\n        \"   - Angular resolution: ≈0.002° (limited by collimation and energy resolution)\",\n        \"3. Sensitivity analysis:\",\n        \"   - Vary mirror surface slope errors (RMS 0.1–1 μrad) → observe spot size blurring\",\n        \"   - Vary DCM energy detuning → observe bandwidth narrowing and flux loss\",\n        \"   - Vary misalignment (translate M1/M2 by ±1 mm, tilt by ±0.1°) → observe beam shift\",\n        \"4. Generate report: flux, throughput, resolution, spot size, and sensitivity to misalignment\"\n      ],\n      \"key_metrics\": [\n        \"End-to-end transmission: >40% (accounting for 2 mirrors ≈ 95% each, DCM ≈ 70%, slits ≈ 60%)\",\n        \"Sample flux (0.1% BW): >5e11 photons/s (adequate for powder diffraction)\",\n        \"Spot size (80% enclosed): 20 μm (H) × 10 μm (V)\",\n        \"Energy resolution: ΔE/E ≈ 0.1%\",\n        \"d-spacing resolution: Δd/d ~ 1e-4 (excellent for structure refinement)\"\n      ]\n    },\n\n    \"recommended_oasys_workflow_json\": {\n      \"nodes_in_order\": [\n        \"SRW Undulator → SRW Source Radiation → SRW To Wofry Wavefront OR SRW Python Script to export to Shadow4\",\n        \"OR: Directly use Shadow4 Undulator Gaussian source (faster for geometric optics)\",\n        \"Shadow4 Generic Mirror (M1) with Pt reflectivity (from XOPPY PreRefl preprocessor)\",\n        \"Shadow4 Screen/Slits (S1)\",\n        \"Shadow4 Generic Crystal (DCM) with Bragg preprocessor (Si 111, symmetric)\",\n        \"Shadow4 Generic Mirror (M2) with Rh reflectivity, elliptical shape\",\n        \"Shadow4 Screen/Slits (S2, S3 sample aperture)\",\n        \"Shadow4 Tools (Histogram, PlotXY, Info) to analyze beam properties at sample\",\n        \"Optional: Hybrid Screen at sample plane to include diffraction corrections (coherence effects)\"\n      ]\n    },\n\n    \"critical_parameters_to_monitor\": {\n      \"flux\": \"Must exceed 1e11 photons/s at sample in 0.1% BW; track through each element.\",\n      \"energy_resolution\": \"DCM detuning and Darwin curve; target ΔE/E ≈ 0.1% or 17 eV at 17 keV.\",\n      \"spot_size\": \"Horizontal focus critical (M2 elliptical mirror design); target 20 μm FWHM.\",\n      \"divergence\": \"Guard slits (S2) should remove all high-angle rays; post-M2 divergence <0.1 mrad.\",\n      \"coherence\": \"Partial coherence in H direction acceptable; V direction naturally coherent due to small emittance.\",\n      \"harmonic_rejection\": \"M1 must suppress 3rd harmonic; verify with XOPPY reflectivity curves (Pt at 3.5 mrad, 52 keV).\",\n      \"thermal_effects\": \"DCM heat load from continuous undulator; monitor crystal temperature and detuning stability.\",\n      \"alignment_sensitivity\": \"Tilts of mirrors >0.1 mrad cause significant beam shifts; use piezo mirrors for fine tuning.\"\n    },\n\n    \"special_considerations_for_xrpd\": {\n      \"sample_environment\": \"Accommodate capillary cells, high-temperature ovens, diamond anvil cells. Beam is small (20×10 μm), so excellent spatial resolution.\",\n      \"angular_access\": \"45 m beamline allows ±90° around sample for detector rotation; 2θ range to 150° for detailed Q coverage.\",\n      \"time_resolution\": \"For operando studies, undulator pulse structure (400 bunches at APS) allows pump-probe experiments; achieve μs time resolution with fast detectors.\",\n      \"phase_resolution\": \"High energy resolution (0.1%) enables extraction of thermal motion and long-range order; use pair distribution function (PDF) analysis if needed.\",\n      \"detector_choice\": \"Area detector (Pilatus, Dectris) for full rings, or point detector with slits for high Q resolution. Scintillation (YAG) or semiconductor (Ge, Si) detectors work well for 17 keV.\"\n    }\n  }\n}\n```\n\n---\n\n## **Summary of Beamline Design**\n\n| **Parameter** | **Value** | **Notes** |\n|---|---|---|\n| **Total Length** | 45 m | Ample space for detector arm rotation (27 m after sample) |\n| **Source** | U2.5 Undulator, E=17 keV | 6 GeV electrons, K_v=1.12, 219 periods × 21 mm |\n| **Energy Resolution** | ΔE/E ≈ 0.1% | Si(111) DCM with detuning; ~17 eV bandwidth at 17 keV |\n| **Spot Size at Sample** | 20 μm (H) × 10 μm (V) | M2 elliptical mirror with M≈0.4 demagnification |\n| **Incident Flux** | ~5×10¹¹ photons/s | In 0.1% BW, adequate for powder diffraction |\n| **Sample Position** | 18 m from source | Allows detector access for 2θ up to ~150° |\n| **Key Optics** | M1 (Pt plane), DCM (Si 111), M2 (Rh elliptical) | Harmonic rejection, energy selection, horizontal focusing |\n| **Geometry** | Bragg θ-2θ diffraction | Standard powder XRD setup |\n\n**OASYS Tools:** Shadow4 for main ray-tracing, SRW for undulator characterization, XOPPY for crystal and mirror reflectivity, optional Hybrid for aberration correction.\n\n</answer>"
    }
  ],
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 26734,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0,
    "output_tokens": 9203
  }
}
"""


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
                position=(float(nd.get("x", 100)), float(nd.get("y", 300))),
            )
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
            snk = node_map.get(lk.get("sink_node_id"))
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

class _Worker(QThread):
    done  = pyqtSignal(dict)
    error = pyqtSignal(str)
    URL = WORKER_URL

    MODELS = [
        ["claude-sonnet-4-5-20250929", 64000],
        ["claude-haiku-4-5-20251001", 64000],
        ["claude-sonnet-4-6", 128000]
    ]

    _selected_model = 1

    def __init__(self, msgs: List[Dict], prompt: str, parent=None):
        super().__init__(parent)
        self._msgs, self._prompt = msgs, prompt

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
                answer = json.loads(TEST_CLAUDE_ANSWER)
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

            raw = "".join(
                b.get("text", "")
                for b in answer.get("content", [])
                if b.get("type") == "text"
            )

            self.done.emit(self._parse(raw))
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

        text = parsed.get("text", "")
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
