from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).parent

_quagga_scanner = components.declare_component(
    "quagga_scanner",
    path=str(_COMPONENT_DIR),
)


def quagga_scanner(
    *,
    readers: list[str] | None = None,
    facing_mode: str = "environment",
    key: str | None = None,
) -> Dict[str, Any] | None:
    """
    Render the QuaggaJS scanner component.

    Parameters
    ----------
    readers:
        Optional list of Quagga decoder readers to enable. Defaults to a mix of common 1D formats.
    facing_mode:
        Camera facing mode hint, typically "environment" for rear camera or "user" for front.
    key:
        Streamlit widget key.
    """

    if readers is None:
        readers = [
            "code_128_reader",
            "ean_reader",
            "ean_8_reader",
            "upc_reader",
            "upc_e_reader",
            "code_39_reader",
            "code_93_reader",
            "codabar_reader",
            "i2of5_reader",
            "2of5_reader",
            "code_128_reader",
            "qr_reader",
        ]

    return _quagga_scanner(
        readers=readers,
        facing_mode=facing_mode,
        key=key,
    )

