"""High-contrast 300 PPI E-Ink SVG + 8-bit grayscale PNG renderer (Portrait & Native Landscape)."""

from __future__ import annotations

import html
import math
import os
import subprocess
import textwrap
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from quotes import Quote, ZenBuddy
from weather import HourlyPoint, WeatherData


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def moon_disc_svg(cycle: float, cx: float, cy: float, r: float = 11.0, fg: str = "#111111", bg: str = "#FFFFFF") -> str:
    """Render an astronomically accurate vector moon disc for lunar phase `cycle` in [0, 1)."""
    c = cycle % 1.0
    # Outer disc filled dark (shadow), then lit portion drawn in `bg` (paper white), outlined in `fg`
    if c < 0.03 or c > 0.97:
        # New moon: dark circle
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fg}" stroke="{fg}" stroke-width="1.8"/>'
    if 0.47 <= c <= 0.53:
        # Full moon: bright paper circle
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{bg}" stroke="{fg}" stroke-width="1.8"/>'

    # Terminator horizontal radius rx varies from +r to -r
    if c < 0.5:
        # Waxing: right side is lit
        k = math.cos(2.0 * math.pi * c)  # +1 at new -> 0 at first quarter -> -1 at full
        rx = abs(k) * r
        sweep_term = 0 if k > 0 else 1
        lit_path = (
            f"M {cx:.2f} {cy - r:.2f} "
            f"A {r:.2f} {r:.2f} 0 0 1 {cx:.2f} {cy + r:.2f} "
            f"A {rx:.2f} {r:.2f} 0 0 {sweep_term} {cx:.2f} {cy - r:.2f} Z"
        )
    else:
        # Waning: left side is lit
        k = math.cos(2.0 * math.pi * c)  # -1 at full -> 0 at last quarter -> +1 at new
        rx = abs(k) * r
        sweep_term = 1 if k > 0 else 0
        lit_path = (
            f"M {cx:.2f} {cy - r:.2f} "
            f"A {r:.2f} {r:.2f} 0 0 0 {cx:.2f} {cy + r:.2f} "
            f"A {rx:.2f} {r:.2f} 0 0 {sweep_term} {cx:.2f} {cy - r:.2f} Z"
        )

    return (
        f'<g>'
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fg}"/>'
        f'<path d="{lit_path}" fill="{bg}"/>'
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="none" stroke="{fg}" stroke-width="1.8"/>'
        f'</g>'
    )


def weather_icon_svg(
    icon_key: str,
    cx: float,
    cy: float,
    size: float = 120.0,
    fg: str = "#111111",
    bg: str = "#FAFAFA",
) -> str:
    """Return crisp E-Ink vector weather illustration centered at (cx, cy) scaled to `size` (base 100x100)."""
    scale = size / 100.0
    tx = cx - 50.0 * scale
    ty = cy - 50.0 * scale
    sw = 3.6

    if icon_key == "sun":
        rays = []
        for deg in range(0, 360, 30):
            rad = math.radians(deg)
            r1 = 29
            r2 = 41 if deg % 60 == 0 else 36
            x1, y1 = 50 + r1 * math.cos(rad), 50 + r1 * math.sin(rad)
            x2, y2 = 50 + r2 * math.cos(rad), 50 + r2 * math.sin(rad)
            rays.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>'
            )
        body = (
            f'<circle cx="50" cy="50" r="21" fill="{bg}" stroke="{fg}" stroke-width="{sw + 0.4}"/>'
            + "".join(rays)
        )
    elif icon_key == "moon_stars":
        body = f"""
        <path d="M58 20 A28 28 0 1 0 82 62 A22 22 0 1 1 58 20 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <path d="M26 28 L28 22 L30 28 L36 30 L30 32 L28 38 L26 32 L20 30 Z" fill="{fg}"/>
        <circle cx="74" cy="28" r="2.6" fill="{fg}"/>
        <circle cx="22" cy="52" r="2.2" fill="{fg}"/>
        """
    elif icon_key == "partly_cloudy":
        body = f"""
        <circle cx="38" cy="38" r="15" fill="{bg}" stroke="{fg}" stroke-width="{sw}"/>
        <line x1="38" y1="14" x2="38" y2="19" stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>
        <line x1="14" y1="38" x2="19" y2="38" stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>
        <line x1="21" y1="21" x2="25" y2="25" stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>
        <line x1="55" y1="21" x2="51" y2="25" stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>
        <path d="M28 74 H74 A14 14 0 0 0 76 46 A19 19 0 0 0 40 42 A15 15 0 0 0 28 74 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        """
    elif icon_key == "cloud_night":
        body = f"""
        <path d="M64 18 A16 16 0 1 0 80 42 A13 13 0 1 1 64 18 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw - 0.3}" stroke-linejoin="round"/>
        <path d="M24 74 H72 A14 14 0 0 0 74 46 A19 19 0 0 0 38 42 A15 15 0 0 0 24 74 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        """
    elif icon_key == "cloudy":
        body = f"""
        <path d="M34 56 H78 A12 12 0 0 0 79 33 A16 16 0 0 0 48 30 A13 13 0 0 0 34 56 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw - 0.5}" opacity="0.65"/>
        <path d="M20 74 H70 A14 14 0 0 0 72 46 A19 19 0 0 0 36 42 A15 15 0 0 0 20 74 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        """
    elif icon_key == "fog":
        body = f"""
        <path d="M24 54 H74 A13 13 0 0 0 75 29 A18 18 0 0 0 40 26 A14 14 0 0 0 24 54 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <line x1="20" y1="65" x2="80" y2="65" stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>
        <line x1="26" y1="75" x2="74" y2="75" stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>
        <line x1="34" y1="85" x2="66" y2="85" stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>
        """
    elif icon_key in ("drizzle", "rain"):
        drops = (
            f'<line x1="34" y1="68" x2="29" y2="82" stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>'
            f'<line x1="50" y1="68" x2="45" y2="85" stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>'
            f'<line x1="66" y1="68" x2="61" y2="82" stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>'
        )
        body = f"""
        <path d="M22 60 H74 A14 14 0 0 0 76 33 A19 19 0 0 0 39 29 A15 15 0 0 0 22 60 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        {drops}
        """
    elif icon_key == "storm":
        body = f"""
        <path d="M22 58 H74 A14 14 0 0 0 76 31 A19 19 0 0 0 39 27 A15 15 0 0 0 22 58 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <polyline points="52,58 42,74 53,74 45,90" fill="none" stroke="{fg}" stroke-width="{sw + 0.4}" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="31" y1="66" x2="27" y2="78" stroke="{fg}" stroke-width="{sw - 0.3}" stroke-linecap="round"/>
        <line x1="67" y1="66" x2="63" y2="78" stroke="{fg}" stroke-width="{sw - 0.3}" stroke-linecap="round"/>
        """
    else:  # snow
        body = f"""
        <path d="M22 58 H74 A14 14 0 0 0 76 31 A19 19 0 0 0 39 27 A15 15 0 0 0 22 58 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <circle cx="35" cy="72" r="3.5" fill="{fg}"/>
        <circle cx="50" cy="78" r="3.5" fill="{fg}"/>
        <circle cx="65" cy="72" r="3.5" fill="{fg}"/>
        """

    return f'<g transform="translate({tx:.1f},{ty:.1f}) scale({scale:.3f})">{body}</g>'


def zen_buddy_svg(
    buddy_key: str,
    cx: float,
    cy: float,
    size: float = 104.0,
    fg: str = "#111111",
    bg: str = "#FFFFFF",
) -> str:
    """12 adorable, ultra-crisp kawaii/zen line-art companions centered at (cx, cy)."""
    scale = size / 100.0
    tx = cx - 50.0 * scale
    ty = cy - 50.0 * scale
    sw = 3.1

    sparkle = (
        f'<path d="M11 23 L13 17 L15 23 L21 25 L15 27 L13 33 L11 27 L5 25 Z" fill="{fg}"/>'
        f'<circle cx="89" cy="21" r="2.2" fill="{fg}"/>'
    )

    if buddy_key == "capybara":
        # Chill capybara in hot spring ripples with a tiny yuzu citrus on its head!
        art = f"""
        {sparkle}
        <!-- Yuzu orange on head -->
        <ellipse cx="50" cy="25" rx="9.5" ry="7.5" fill="{bg}" stroke="{fg}" stroke-width="2.7"/>
        <path d="M50 17 C54 12 60 14 55 18 Z" fill="{fg}"/>
        <!-- Little ears -->
        <ellipse cx="29" cy="36" rx="5.5" ry="4.5" transform="rotate(-25 29 36)" fill="{bg}" stroke="{fg}" stroke-width="2.8"/>
        <ellipse cx="71" cy="36" rx="5.5" ry="4.5" transform="rotate(25 71 36)" fill="{bg}" stroke="{fg}" stroke-width="2.8"/>
        <!-- Round capybara head/shoulders -->
        <path d="M21 76 C21 44 30 32 50 32 C70 32 79 44 79 76 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <!-- Serene closed eyes -->
        <path d="M33 50 Q37 53 41 50" fill="none" stroke="{fg}" stroke-width="2.7" stroke-linecap="round"/>
        <path d="M59 50 Q63 53 67 50" fill="none" stroke="{fg}" stroke-width="2.7" stroke-linecap="round"/>
        <!-- Cute snout patch & nostrils/mouth -->
        <ellipse cx="50" cy="59" rx="11" ry="9" fill="{bg}" stroke="{fg}" stroke-width="2.3"/>
        <circle cx="46.5" cy="56" r="1.6" fill="{fg}"/>
        <circle cx="53.5" cy="56" r="1.6" fill="{fg}"/>
        <path d="M50 58 V63 M46 63 Q50 66 54 63" fill="none" stroke="{fg}" stroke-width="2.2" stroke-linecap="round"/>
        <!-- Hot spring water ripples -->
        <path d="M13 77 Q32 82 50 77 Q68 72 87 77" fill="none" stroke="{fg}" stroke-width="2.7" stroke-linecap="round"/>
        <path d="M22 85 Q50 90 78 85" fill="none" stroke="{fg}" stroke-width="2.2" stroke-linecap="round"/>
        """
    elif buddy_key == "bonsai":
        art = f"""
        {sparkle}
        <!-- Foliage clouds -->
        <ellipse cx="36" cy="36" rx="16" ry="10" fill="{bg}" stroke="{fg}" stroke-width="2.8"/>
        <ellipse cx="64" cy="38" rx="15" ry="9.5" fill="{bg}" stroke="{fg}" stroke-width="2.8"/>
        <ellipse cx="50" cy="24" rx="18" ry="11" fill="{bg}" stroke="{fg}" stroke-width="{sw}"/>
        <!-- Sculpted trunk -->
        <path d="M45 58 C44 47 40 42 36 38 M55 58 C54 48 58 44 63 40 M50 58 C50 45 49 38 50 34" fill="none" stroke="{fg}" stroke-width="3.4" stroke-linecap="round"/>
        <!-- Smiling bonsai pot -->
        <path d="M25 58 H75 L69 82 H31 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <line x1="22" y1="58" x2="78" y2="58" stroke="{fg}" stroke-width="3.4" stroke-linecap="round"/>
        <circle cx="43" cy="69" r="2.3" fill="{fg}"/>
        <circle cx="57" cy="69" r="2.3" fill="{fg}"/>
        <path d="M46 74 Q50 78 54 74" fill="none" stroke="{fg}" stroke-width="2.4" stroke-linecap="round"/>
        """
    elif buddy_key == "boba":
        art = f"""
        {sparkle}
        <!-- Chunky diagonal boba straw -->
        <path d="M54 32 L61 10 L68 12 L61 32" fill="{bg}" stroke="{fg}" stroke-width="2.8" stroke-linejoin="round"/>
        <!-- Dome lid & cup -->
        <path d="M28 34 H72 L66 84 H34 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <line x1="24" y1="34" x2="76" y2="34" stroke="{fg}" stroke-width="3.5" stroke-linecap="round"/>
        <!-- Cute face -->
        <path d="M39 51 Q42 47 45 51" fill="none" stroke="{fg}" stroke-width="2.7" stroke-linecap="round"/>
        <path d="M55 51 Q58 47 61 51" fill="none" stroke="{fg}" stroke-width="2.7" stroke-linecap="round"/>
        <path d="M47 57 Q50 61 53 57" fill="none" stroke="{fg}" stroke-width="2.6" stroke-linecap="round"/>
        <!-- Tapioca pearls -->
        <circle cx="40" cy="75" r="3.6" fill="{fg}"/>
        <circle cx="50" cy="77" r="3.6" fill="{fg}"/>
        <circle cx="60" cy="75" r="3.6" fill="{fg}"/>
        <circle cx="45" cy="69" r="3.2" fill="{fg}"/>
        <circle cx="56" cy="69" r="3.2" fill="{fg}"/>
        """
    elif buddy_key == "shiba":
        art = f"""
        {sparkle}
        <!-- Pointy shiba ears + round cheeks -->
        <path d="M24 44 L20 18 L40 30 Q50 27 60 30 L80 18 L76 44 C83 56 77 78 50 78 C23 78 17 56 24 44 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <!-- Shiba eyebrow dots -->
        <ellipse cx="40" cy="43" rx="3.2" ry="2.0" fill="{fg}"/>
        <ellipse cx="60" cy="43" rx="3.2" ry="2.0" fill="{fg}"/>
        <!-- Happy eyes & nose -->
        <circle cx="38" cy="52" r="2.8" fill="{fg}"/>
        <circle cx="62" cy="52" r="2.8" fill="{fg}"/>
        <polygon points="50,59 46,55 54,55" fill="{fg}"/>
        <path d="M43 63 Q46.5 67 50 62 Q53.5 67 57 63" fill="none" stroke="{fg}" stroke-width="2.6" stroke-linecap="round"/>
        <line x1="29" y1="59" x2="33" y2="59" stroke="{fg}" stroke-width="2.1" stroke-linecap="round"/>
        <line x1="67" y1="59" x2="71" y2="59" stroke="{fg}" stroke-width="2.1" stroke-linecap="round"/>
        """
    elif buddy_key == "teacup":
        art = f"""
        {sparkle}
        <path d="M37 26 Q33 18 38 10" fill="none" stroke="{fg}" stroke-width="2.5" stroke-linecap="round"/>
        <path d="M49 23 Q45 14 50 6" fill="none" stroke="{fg}" stroke-width="2.5" stroke-linecap="round"/>
        <path d="M61 26 Q57 18 62 10" fill="none" stroke="{fg}" stroke-width="2.5" stroke-linecap="round"/>
        <path d="M23 36 H73 V55 A25 25 0 0 1 23 55 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <path d="M73 42 H80 A8 8 0 0 1 80 58 H72" fill="none" stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>
        <ellipse cx="48" cy="82" rx="29" ry="5" fill="{bg}" stroke="{fg}" stroke-width="2.8"/>
        <path d="M35 52 Q38.5 47.5 42 52" fill="none" stroke="{fg}" stroke-width="2.8" stroke-linecap="round"/>
        <path d="M54 52 Q57.5 47.5 61 52" fill="none" stroke="{fg}" stroke-width="2.8" stroke-linecap="round"/>
        <path d="M44 59 Q48 64 52 59" fill="none" stroke="{fg}" stroke-width="2.8" stroke-linecap="round"/>
        <line x1="30" y1="58" x2="34" y2="57" stroke="{fg}" stroke-width="2.0" stroke-linecap="round"/>
        <line x1="62" y1="57" x2="66" y2="58" stroke="{fg}" stroke-width="2.0" stroke-linecap="round"/>
        """
    elif buddy_key == "kitty":
        art = f"""
        {sparkle}
        <path d="M23 45 L21 19 L40 32 Q50 29 60 32 L79 19 L77 45 A28 25 0 1 1 23 45 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <path d="M35 53 Q39.5 48 44 53" fill="none" stroke="{fg}" stroke-width="2.8" stroke-linecap="round"/>
        <path d="M56 53 Q60.5 48 65 53" fill="none" stroke="{fg}" stroke-width="2.8" stroke-linecap="round"/>
        <path d="M45 60 Q47.5 64 50 60 Q52.5 64 55 60" fill="none" stroke="{fg}" stroke-width="2.6" stroke-linecap="round"/>
        <line x1="12" y1="54" x2="26" y2="56" stroke="{fg}" stroke-width="2.3" stroke-linecap="round"/>
        <line x1="12" y1="62" x2="26" y2="61" stroke="{fg}" stroke-width="2.3" stroke-linecap="round"/>
        <line x1="88" y1="54" x2="74" y2="56" stroke="{fg}" stroke-width="2.3" stroke-linecap="round"/>
        <line x1="88" y1="62" x2="74" y2="61" stroke="{fg}" stroke-width="2.3" stroke-linecap="round"/>
        <circle cx="50" cy="42" r="2.2" fill="{fg}"/>
        """
    elif buddy_key == "lotus":
        art = f"""
        {sparkle}
        <path d="M50 74 C67 68 83 53 79 33 C65 37 56 51 50 74 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <path d="M50 74 C33 68 17 53 21 33 C35 37 44 51 50 74 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <path d="M50 18 C64 36 66 59 50 75 C34 59 36 36 50 18 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <path d="M24 80 Q50 88 76 80" fill="none" stroke="{fg}" stroke-width="2.8" stroke-linecap="round"/>
        <circle cx="45" cy="51" r="2.3" fill="{fg}"/>
        <circle cx="55" cy="51" r="2.3" fill="{fg}"/>
        <path d="M46 57 Q50 61 54 57" fill="none" stroke="{fg}" stroke-width="2.5" stroke-linecap="round"/>
        """
    elif buddy_key == "frog":
        art = f"""
        {sparkle}
        <ellipse cx="50" cy="60" rx="30" ry="22" fill="{bg}" stroke="{fg}" stroke-width="{sw}"/>
        <circle cx="34" cy="38" r="10.5" fill="{bg}" stroke="{fg}" stroke-width="{sw}"/>
        <circle cx="66" cy="38" r="10.5" fill="{bg}" stroke="{fg}" stroke-width="{sw}"/>
        <circle cx="34" cy="38" r="3.8" fill="{fg}"/>
        <circle cx="66" cy="38" r="3.8" fill="{fg}"/>
        <circle cx="32.5" cy="36.5" r="1.2" fill="{bg}"/>
        <circle cx="64.5" cy="36.5" r="1.2" fill="{bg}"/>
        <path d="M40 58 Q50 66 60 58" fill="none" stroke="{fg}" stroke-width="2.8" stroke-linecap="round"/>
        <line x1="28" y1="57" x2="33" y2="57" stroke="{fg}" stroke-width="2.2" stroke-linecap="round"/>
        <line x1="67" y1="57" x2="72" y2="57" stroke="{fg}" stroke-width="2.2" stroke-linecap="round"/>
        <path d="M16 83 Q50 91 84 83" fill="none" stroke="{fg}" stroke-width="2.6" stroke-linecap="round"/>
        """
    elif buddy_key == "turtle":
        art = f"""
        {sparkle}
        <path d="M20 65 A26 24 0 0 1 72 65 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <path d="M72 58 Q88 49 87 62 Q85 69 71 65" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <circle cx="80" cy="58" r="2.4" fill="{fg}"/>
        <path d="M78 63 Q82 65 84 62" fill="none" stroke="{fg}" stroke-width="2.0" stroke-linecap="round"/>
        <path d="M28 65 L24 77 M62 65 L66 77" stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>
        <path d="M46 41 V25" stroke="{fg}" stroke-width="2.6" stroke-linecap="round"/>
        <path d="M46 28 C36 20 32 29 46 34 C60 29 56 20 46 28 Z" fill="{bg}" stroke="{fg}" stroke-width="2.5"/>
        <path d="M33 55 Q46 46 59 55" fill="none" stroke="{fg}" stroke-width="2.3"/>
        """
    elif buddy_key == "cloud":
        art = f"""
        {sparkle}
        <path d="M22 71 H76 A15 15 0 0 0 77 42 A21 21 0 0 0 37 38 A16 16 0 0 0 22 71 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <path d="M38 55 Q41.5 50.5 45 55" fill="none" stroke="{fg}" stroke-width="2.8" stroke-linecap="round"/>
        <path d="M56 55 Q59.5 50.5 63 55" fill="none" stroke="{fg}" stroke-width="2.8" stroke-linecap="round"/>
        <path d="M47 61 Q50.5 65 54 61" fill="none" stroke="{fg}" stroke-width="2.8" stroke-linecap="round"/>
        """
    elif buddy_key == "sprout":
        art = f"""
        {sparkle}
        <path d="M30 56 H70 L64 83 H36 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <rect x="26" y="49" width="48" height="8" rx="3" fill="{bg}" stroke="{fg}" stroke-width="{sw}"/>
        <path d="M50 49 V27" stroke="{fg}" stroke-width="{sw}" stroke-linecap="round"/>
        <path d="M50 34 C33 21 27 34 50 40" fill="{bg}" stroke="{fg}" stroke-width="2.8" stroke-linejoin="round"/>
        <path d="M50 31 C67 18 73 31 50 37" fill="{bg}" stroke="{fg}" stroke-width="2.8" stroke-linejoin="round"/>
        <circle cx="43" cy="67" r="2.5" fill="{fg}"/>
        <circle cx="57" cy="67" r="2.5" fill="{fg}"/>
        <path d="M46 73 Q50 77 54 73" fill="none" stroke="{fg}" stroke-width="2.6" stroke-linecap="round"/>
        """
    else:  # moon
        art = f"""
        {sparkle}
        <path d="M58 18 A30 30 0 1 0 84 64 A23 23 0 1 1 58 18 Z" fill="{bg}" stroke="{fg}" stroke-width="{sw}" stroke-linejoin="round"/>
        <path d="M35 50 Q39 54 43 50" fill="none" stroke="{fg}" stroke-width="2.6" stroke-linecap="round"/>
        <path d="M41 60 Q45 63 49 60" fill="none" stroke="{fg}" stroke-width="2.5" stroke-linecap="round"/>
        <text x="66" y="34" font-family="Noto Sans, sans-serif" font-size="14" font-weight="700" fill="{fg}">z</text>
        <text x="75" y="24" font-family="Noto Sans, sans-serif" font-size="11" font-weight="700" fill="{fg}">z</text>
        """

    return f'<g transform="translate({tx:.1f},{ty:.1f}) scale({scale:.3f})">{art}</g>'


def hourly_curve_svg(
    points: list[HourlyPoint],
    x_left: float,
    x_right: float,
    y_top: float,
    y_bottom: float,
    fg: str,
    fg_muted: str,
    card_bg: str,
    rule_soft: str,
    compact: bool = False,
) -> str:
    """Render a smooth cubic Bezier temperature curve with large, bold dual °C / °F labels."""
    if len(points) < 2:
        return ""

    pts = points[:4] if compact else points[:5]
    n = len(pts)
    temps = [p.temp_c for p in pts]
    t_min, t_max = min(temps), max(temps)
    span = max(2.0, float(t_max - t_min))

    pad_x = 76.0 if compact else 88.0
    x0 = x_left + pad_x
    x1 = x_right - pad_x
    step_x = (x1 - x0) / max(1, (n - 1))

    curve_top = y_top + (56.0 if compact else 44.0)
    curve_bot = y_bottom - (48.0 if compact else 40.0)

    coords: list[tuple[float, float]] = []
    for i, p in enumerate(pts):
        px = x0 + i * step_x
        norm = (p.temp_c - t_min) / span
        py = curve_bot - norm * (curve_bot - curve_top)
        coords.append((px, py))

    # Smooth cubic Bezier path through points
    d_parts = [f"M {coords[0][0]:.1f} {coords[0][1]:.1f}"]
    for i in range(n - 1):
        cx1 = coords[i][0] + step_x * 0.42
        cy1 = coords[i][1]
        cx2 = coords[i + 1][0] - step_x * 0.42
        cy2 = coords[i + 1][1]
        d_parts.append(f"C {cx1:.1f} {cy1:.1f}, {cx2:.1f} {cy2:.1f}, {coords[i + 1][0]:.1f} {coords[i + 1][1]:.1f}")

    temp_fs = 25 if compact else 21
    time_fs = 23 if compact else 19

    # Subtle baseline guide + bold E-Ink curve
    elems = [
        f'<line x1="{x0:.1f}" y1="{curve_bot + 8:.1f}" x2="{x1:.1f}" y2="{curve_bot + 8:.1f}" stroke="{rule_soft}" stroke-width="1.4" stroke-dasharray="5,5"/>',
        f'<path d="{" ".join(d_parts)}" fill="none" stroke="{fg}" stroke-width="4.0" stroke-linecap="round"/>',
    ]

    for i, (p, (px, py)) in enumerate(zip(pts, coords)):
        r_dot = 7.0 if i == 0 else 5.8
        fill_dot = fg if i == 0 else card_bg
        elems.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r_dot}" fill="{fill_dot}" stroke="{fg}" stroke-width="3.2"/>'
        )
        elems.append(
            f'<text x="{px:.1f}" y="{py - 17:.1f}" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="{temp_fs}" font-weight="800" fill="{fg}" stroke="{card_bg}" stroke-width="6" stroke-linejoin="round" paint-order="stroke">{p.temp_c}°/{p.temp_f}°F</text>'
        )
        elems.append(
            f'<text x="{px:.1f}" y="{y_bottom - 11:.1f}" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="{time_fs}" font-weight="800" letter-spacing="1.0" fill="{fg_muted}">{_esc(p.label)}</text>'
        )

    return "".join(elems)


def _mini_lotus_svg(cx: float, cy: float, fg: str) -> str:
    return f"""
    <g transform="translate({cx - 12:.1f},{cy - 12:.1f}) scale(0.24)">
      <path d="M50 74 C67 68 83 53 79 33 C65 37 56 51 50 74 Z" fill="none" stroke="{fg}" stroke-width="5.5" stroke-linejoin="round"/>
      <path d="M50 74 C33 68 17 53 21 33 C35 37 44 51 50 74 Z" fill="none" stroke="{fg}" stroke-width="5.5" stroke-linejoin="round"/>
      <path d="M50 18 C64 36 66 59 50 75 C34 59 36 36 50 18 Z" fill="none" stroke="{fg}" stroke-width="5.5" stroke-linejoin="round"/>
    </g>
    """


def _greeting_for_hour(hour: int) -> str:
    if 5 <= hour < 12:
        return "GOOD MORNING  ✦"
    if 12 <= hour < 17:
        return "GOOD AFTERNOON  ✦"
    if 17 <= hour < 21:
        return "GOOD EVENING  ✦"
    return "QUIET NIGHT  ☾"


def _wrap_quote(text: str, narrow: bool = False) -> tuple[list[str], int, int]:
    """Return (wrapped_lines, font_size_px, line_height_px) with large, bold, glasses-free sizing."""
    n = len(text)
    if narrow:
        if n <= 55:
            return textwrap.wrap(text, width=22), 46, 58
        if n <= 105:
            return textwrap.wrap(text, width=26), 40, 51
        if n <= 155:
            return textwrap.wrap(text, width=30), 35, 45
        return textwrap.wrap(text, width=33)[:7], 32, 41

    if n <= 55:
        return textwrap.wrap(text, width=24), 48, 60
    if n <= 115:
        return textwrap.wrap(text, width=31), 40, 50
    if n <= 175:
        return textwrap.wrap(text, width=36), 35, 44
    return textwrap.wrap(text, width=40)[:6], 31, 39


def _palette(theme: str, hour: int) -> dict[str, str]:
    effective_dark = (not (6 <= hour < 20)) if theme == "auto" else (theme == "dark")
    if effective_dark:
        return {
            "bg": "#080808",
            "card_bg": "#121212",
            "fg": "#FFFFFF",
            "fg_2": "#EAEAEA",
            "fg_muted": "#CCCCCC",
            "rule_strong": "#F2F2F2",
            "rule_soft": "#4E4E4E",
            "quote_mark": "#555555",
        }
    return {
        "bg": "#FFFFFF",
        "card_bg": "#F9F9F9",
        "fg": "#000000",
        "fg_2": "#141414",
        "fg_muted": "#2C2C2C",
        "rule_strong": "#0A0A0A",
        "rule_soft": "#AEAEAE",
        "quote_mark": "#B8B8B8",
    }


def render_svg(
    weather: WeatherData,
    quote: Quote,
    buddy: ZenBuddy,
    now: datetime | None = None,
    tz_name: str = "America/Los_Angeles",
    short_location: str = "PASADENA · CALIFORNIA",
    theme: str = "light",
    use_24h: bool = False,
    orientation: str = "portrait",
) -> str:
    """Build either a 1072×1448 Portrait SVG or a native 1448×1072 Landscape SVG for 300 PPI E-Ink."""
    dt = now or datetime.now(ZoneInfo(tz_name))
    pal = _palette(theme, dt.hour)
    if orientation.startswith("landscape"):
        return _render_landscape_svg(weather, quote, buddy, dt, short_location, pal, use_24h)
    return _render_portrait_svg(weather, quote, buddy, dt, short_location, pal, use_24h)


def _render_portrait_svg(
    weather: WeatherData,
    quote: Quote,
    buddy: ZenBuddy,
    dt: datetime,
    short_location: str,
    pal: dict[str, str],
    use_24h: bool,
) -> str:
    bg, card_bg = pal["bg"], pal["card_bg"]
    fg, fg_2, fg_muted = pal["fg"], pal["fg_2"], pal["fg_muted"]
    rule_strong, rule_soft, quote_mark_col = pal["rule_strong"], pal["rule_soft"], pal["quote_mark"]

    w, h = 1072, 1448

    if use_24h:
        time_str, ampm_str = dt.strftime("%H:%M"), ""
    else:
        time_str, ampm_str = dt.strftime("%-I:%M"), dt.strftime("%p")

    date_str = dt.strftime("%A, %B %-d").upper()
    year_str = dt.strftime("%Y")
    sync_str = dt.strftime("%-I:%M %p" if not use_24h else "%H:%M")
    greeting = _greeting_for_hour(dt.hour)
    clock_font_size = 176 if len(time_str) <= 4 else 158

    ampm_tspan = ""
    if ampm_str:
        ampm_tspan = (
            f'<tspan dx="18" dy="-72" font-family="Noto Sans, sans-serif" font-size="38" font-weight="700" letter-spacing="2.5" fill="{fg_2}">'
            f"{_esc(ampm_str)}</tspan>"
        )

    aqi_disp = f"{weather.us_aqi} · {weather.aqi_status}" if weather.us_aqi is not None else "—"
    uv_disp = f"{weather.uv_index:.1f}"
    sun_disp = f"{weather.sunrise.replace(' AM', 'a').replace(' PM', 'p')} – {weather.sunset.replace(' AM', 'a').replace(' PM', 'p')}"

    # 5-column metrics strip across x=76..996 (920px / 5 = 184px per cell)
    metrics = [
        ("HUMIDITY", f"{weather.humidity}%"),
        ("BREEZE", f"{weather.wind_mph} mph · {weather.wind_kmh} km/h"),
        ("PASADENA AQI", aqi_disp),
        ("UV INDEX", uv_disp),
        ("DAYLIGHT", sun_disp),
    ]
    metric_svg = []
    for idx, (m_lbl, m_val) in enumerate(metrics):
        mx = 76 + idx * 184
        mcx = mx + 92
        if idx > 0:
            metric_svg.append(f'<line x1="{mx}" y1="596" x2="{mx}" y2="644" stroke="{rule_soft}" stroke-width="1.2"/>')
        metric_svg.append(
            f'<text x="{mcx}" y="611" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="13" font-weight="700" letter-spacing="1.6" fill="{fg_muted}">{_esc(m_lbl)}</text>'
        )
        metric_svg.append(
            f'<text x="{mcx}" y="637" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="18" font-weight="700" fill="{fg}">{_esc(m_val)}</text>'
        )

    # 4-Day Forecast (y=784..936)
    fc_parts: list[str] = []
    for i, fc in enumerate(weather.forecast[:4]):
        col_x = 76 + i * 230
        col_cx = col_x + 115
        if i > 0:
            fc_parts.append(
                f'<line x1="{col_x}" y1="798" x2="{col_x}" y2="924" stroke="{rule_soft}" stroke-width="1.4"/>'
            )
        fc_parts.append(
            f'<text x="{col_cx}" y="816" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="19" font-weight="700" letter-spacing="2.4" fill="{fg}">{_esc(fc.day_label)}</text>'
        )
        fc_parts.append(weather_icon_svg(fc.icon_key, col_cx, 852, size=44, fg=fg, bg=card_bg))
        fc_parts.append(
            f'<text x="{col_cx}" y="897" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="20" font-weight="700" fill="{fg}">{fc.high_c}°C · {fc.high_f}°F</text>'
        )
        fc_parts.append(
            f'<text x="{col_cx}" y="921" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="17" font-weight="500" fill="{fg_muted}">{fc.low_c}°C · {fc.low_f}°F</text>'
        )

    # Quote wrapping inside y=995..1230
    q_lines, q_size, q_lh = _wrap_quote(quote.text, narrow=False)
    total_q_h = len(q_lines) * q_lh
    q_start_y = max(1008, int(1096 - total_q_h / 2))
    q_tspans = []
    for idx, line in enumerate(q_lines):
        ly = q_start_y + idx * q_lh
        prefix = "“" if idx == 0 else ""
        suffix = "”" if idx == len(q_lines) - 1 else ""
        q_tspans.append(
            f'<text x="536" y="{ly}" text-anchor="middle" font-family="Noto Serif, Georgia, serif" font-size="{q_size}" font-weight="600" fill="{fg}">{_esc(prefix + line + suffix)}</text>'
        )

    author_y = q_start_y + (len(q_lines) - 1) * q_lh + 44
    source_svg = ""
    if quote.source:
        source_svg = f'<text x="536" y="{author_y + 25}" text-anchor="middle" font-family="Noto Serif, Georgia, serif" font-style="italic" font-size="18" fill="{fg_muted}">{_esc(quote.source)}</text>'

    stale_badge = " · CACHED" if weather.stale else ""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <rect x="0" y="0" width="{w}" height="{h}" fill="{bg}"/>
  <rect x="34" y="34" width="{w - 68}" height="{h - 68}" rx="12" fill="none" stroke="{rule_soft}" stroke-width="1.5"/>

  <!-- Top Masthead with Live Moon Phase -->
  <text x="76" y="84" font-family="Noto Sans, sans-serif" font-size="20" font-weight="700" letter-spacing="3.6" fill="{fg}">{_esc(short_location)}</text>
  {moon_disc_svg(weather.moon_cycle, 456, 77, r=9.5, fg=fg, bg=bg)}
  <text x="473" y="83" font-family="Noto Sans, sans-serif" font-size="15" font-weight="600" letter-spacing="1.2" fill="{fg_muted}">{_esc(weather.moon_name.upper())} · {weather.moon_illum}%</text>
  <text x="996" y="84" text-anchor="end" font-family="Noto Sans, sans-serif" font-size="19" font-weight="600" letter-spacing="2.2" fill="{fg_2}">{_esc(greeting)}</text>

  <!-- Double Editorial Rule -->
  <line x1="76" y1="103" x2="996" y2="103" stroke="{rule_strong}" stroke-width="2.6"/>
  <line x1="76" y1="110" x2="996" y2="110" stroke="{rule_strong}" stroke-width="1.0"/>

  <!-- Date & Hero Clock -->
  <text x="536" y="154" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="25" font-weight="600" letter-spacing="3.5" fill="{fg_2}">{_esc(date_str)} · {_esc(year_str)}</text>

  <text x="546" y="314" text-anchor="middle" fill="{fg}">
    <tspan font-family="Noto Serif, Georgia, serif" font-size="{clock_font_size}" font-weight="700">{_esc(time_str)}</tspan>{ampm_tspan}
  </text>

  <!-- Ornamental Diamond Divider -->
  <line x1="346" y1="355" x2="508" y2="355" stroke="{rule_soft}" stroke-width="1.5"/>
  <polygon points="536,346 545,355 536,364 527,355" fill="{fg}"/>
  <line x1="564" y1="355" x2="726" y2="355" stroke="{rule_soft}" stroke-width="1.5"/>

  <!-- Pasadena Dual-Scale Weather & Almanac Card -->
  <rect x="76" y="382" width="920" height="556" rx="24" fill="{card_bg}" stroke="{rule_strong}" stroke-width="2.4"/>

  <!-- Hero Weather Illustration + Condition -->
  {weather_icon_svg(weather.icon_key, 196, 472, size=118, fg=fg, bg=card_bg)}
  <text x="196" y="562" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="22" font-weight="700" fill="{fg}">{_esc(weather.condition)}</text>

  <line x1="316" y1="410" x2="316" y2="570" stroke="{rule_soft}" stroke-width="1.5"/>

  <!-- Dual Scale Hero Temperatures -->
  <text x="656" y="426" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="17" font-weight="700" letter-spacing="2.8" fill="{fg_muted}">PASADENA · CELSIUS &amp; FAHRENHEIT{_esc(stale_badge)}</text>

  <text x="502" y="518" text-anchor="middle" font-family="Noto Serif, Georgia, serif" font-size="82" font-weight="700" fill="{fg}">{weather.temp_c}°C</text>
  <line x1="656" y1="452" x2="656" y2="526" stroke="{rule_soft}" stroke-width="2.4"/>
  <text x="810" y="518" text-anchor="middle" font-family="Noto Serif, Georgia, serif" font-size="82" font-weight="700" fill="{fg}">{weather.temp_f}°F</text>

  <text x="656" y="564" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="20" font-weight="600" fill="{fg_2}">Feels {weather.feels_c}°C / {weather.feels_f}°F   ·   H {weather.high_c}°C / {weather.high_f}°F   ·   L {weather.low_c}°C / {weather.low_f}°F</text>

  <!-- 5-Column Metrics Strip -->
  <line x1="76" y1="586" x2="996" y2="586" stroke="{rule_soft}" stroke-width="1.5"/>
  {"".join(metric_svg)}
  <line x1="76" y1="652" x2="996" y2="652" stroke="{rule_soft}" stroke-width="1.5"/>

  <!-- 12-Hour Smooth Temperature Curve -->
  {hourly_curve_svg(weather.hourly, 76, 996, 654, 784, fg=fg, fg_muted=fg_muted, card_bg=card_bg, rule_soft=rule_soft)}
  <line x1="76" y1="786" x2="996" y2="786" stroke="{rule_soft}" stroke-width="1.5"/>

  <!-- 4-Day Pasadena Forecast -->
  {"".join(fc_parts)}

  <!-- Contemplative Quote Sanctuary -->
  <text x="536" y="984" text-anchor="middle" font-family="Noto Serif, Georgia, serif" font-size="56" fill="{quote_mark_col}">❦</text>
  {"".join(q_tspans)}
  <text x="536" y="{author_y}" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="21" font-weight="700" letter-spacing="3.2" fill="{fg}">— {_esc(quote.author.upper())} —</text>
  {source_svg}

  <!-- Symmetrical Cute Zen Companion Vignette -->
  <g>
    <line x1="106" y1="1294" x2="306" y2="1294" stroke="{rule_soft}" stroke-width="1.4"/>
    {zen_buddy_svg(buddy.key, 382, 1290, size=100, fg=fg, bg=bg)}
    <rect x="451" y="1260" width="290" height="64" rx="32" fill="{card_bg}" stroke="{rule_strong}" stroke-width="2.0"/>
    <text x="596" y="1288" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="20" font-weight="700" letter-spacing="1.0" fill="{fg}">✦  {_esc(buddy.label)}  ✦</text>
    <text x="596" y="1313" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="18" font-weight="600" fill="{fg_2}">{_esc(buddy.kaomoji)}</text>
    <line x1="766" y1="1294" x2="966" y2="1294" stroke="{rule_soft}" stroke-width="1.4"/>
  </g>

  <!-- Quiet Footer -->
  <line x1="76" y1="1358" x2="996" y2="1358" stroke="{rule_soft}" stroke-width="1.4"/>
  {_mini_lotus_svg(90, 1383, fg_muted)}
  <text x="112" y="1390" font-family="Noto Sans, sans-serif" font-size="17" font-weight="600" letter-spacing="2.4" fill="{fg_muted}">BREATHE IN · BREATHE OUT</text>
  <text x="996" y="1390" text-anchor="end" font-family="Noto Sans, sans-serif" font-size="17" font-weight="600" letter-spacing="2.0" fill="{fg_muted}">SYNCED {_esc(sync_str)}  ✦</text>
</svg>
"""


def _render_landscape_svg(
    weather: WeatherData,
    quote: Quote,
    buddy: ZenBuddy,
    dt: datetime,
    short_location: str,
    pal: dict[str, str],
    use_24h: bool,
) -> str:
    """Native 1448×1072 high-legibility two-column layout tuned for effortless reading without glasses."""
    bg, card_bg = pal["bg"], pal["card_bg"]
    fg, fg_2, fg_muted = pal["fg"], pal["fg_2"], pal["fg_muted"]
    rule_strong, rule_soft, quote_mark_col = pal["rule_strong"], pal["rule_soft"], pal["quote_mark"]

    w, h = 1448, 1072

    if use_24h:
        time_str, ampm_str = dt.strftime("%H:%M"), ""
    else:
        time_str, ampm_str = dt.strftime("%-I:%M"), dt.strftime("%p")

    date_str = dt.strftime("%A, %b %-d, %Y").upper()
    sync_str = dt.strftime("%-I:%M %p" if not use_24h else "%H:%M")
    greeting = _greeting_for_hour(dt.hour)
    clock_font_size = 196 if len(time_str) <= 4 else 172

    ampm_tspan = ""
    if ampm_str:
        ampm_tspan = (
            f'<tspan dx="14" dy="-84" font-family="Noto Sans, sans-serif" font-size="44" font-weight="800" letter-spacing="2.0" fill="{fg_2}">'
            f"{_esc(ampm_str)}</tspan>"
        )

    # Left Column (x=42..702, width=660, center=372): Giant Clock + Bold Quote + Cute Buddy
    q_lines, q_size, q_lh = _wrap_quote(quote.text, narrow=True)
    span_q_h = max(0, len(q_lines) - 1) * q_lh
    q_start_y = max(448, int(582 - span_q_h / 2))
    q_tspans = []
    for idx, line in enumerate(q_lines):
        ly = q_start_y + idx * q_lh
        prefix = "“" if idx == 0 else ""
        suffix = "”" if idx == len(q_lines) - 1 else ""
        q_tspans.append(
            f'<text x="372" y="{ly}" text-anchor="middle" font-family="Noto Serif, Georgia, serif" font-size="{q_size}" font-weight="600" fill="{fg}">{_esc(prefix + line + suffix)}</text>'
        )
    author_y = q_start_y + span_q_h + 48
    source_svg = (
        f'<text x="372" y="{author_y + 30}" text-anchor="middle" font-family="Noto Serif, Georgia, serif" font-style="italic" font-size="22" font-weight="600" fill="{fg_muted}">{_esc(quote.source)}</text>'
        if quote.source
        else ""
    )

    # Right Column Card (x=736..1406, width=670, y=108..976)
    aqi_disp = f"{weather.us_aqi} {weather.aqi_status}" if weather.us_aqi is not None else "—"
    sun_disp = f"{weather.sunrise.replace(' AM', 'a').replace(' PM', 'p')}–{weather.sunset.replace(' AM', 'a').replace(' PM', 'p')}"
    metrics = [
        ("HUMIDITY", f"{weather.humidity}%"),
        ("WIND", f"{weather.wind_mph} mph"),
        ("AQI", aqi_disp),
        ("SUN", sun_disp),
    ]
    metric_svg = []
    col_w = 670.0 / 4.0
    for idx, (m_lbl, m_val) in enumerate(metrics):
        mx = 736.0 + idx * col_w
        mcx = mx + col_w / 2.0
        val_fs = 23 if len(m_val) > 9 else 29
        if idx > 0:
            metric_svg.append(f'<line x1="{mx:.1f}" y1="378" x2="{mx:.1f}" y2="462" stroke="{rule_soft}" stroke-width="1.5"/>')
        metric_svg.append(
            f'<text x="{mcx:.1f}" y="403" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="19" font-weight="800" letter-spacing="1.4" fill="{fg_muted}">{_esc(m_lbl)}</text>'
        )
        metric_svg.append(
            f'<text x="{mcx:.1f}" y="449" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="{val_fs}" font-weight="800" fill="{fg}">{_esc(m_val)}</text>'
        )

    fc_parts = []
    for i, fc in enumerate(weather.forecast[:4]):
        col_x = 736.0 + i * col_w
        col_cx = col_x + col_w / 2.0
        if i > 0:
            fc_parts.append(f'<line x1="{col_x:.1f}" y1="734" x2="{col_x:.1f}" y2="958" stroke="{rule_soft}" stroke-width="1.5"/>')
        fc_parts.append(
            f'<text x="{col_cx:.1f}" y="766" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="27" font-weight="800" letter-spacing="1.8" fill="{fg}">{_esc(fc.day_label)}</text>'
        )
        fc_parts.append(weather_icon_svg(fc.icon_key, col_cx, 828, size=64, fg=fg, bg=card_bg))
        fc_parts.append(
            f'<text x="{col_cx:.1f}" y="906" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="26" font-weight="800" fill="{fg}">{fc.high_c}° · {fc.high_f}°F</text>'
        )
        fc_parts.append(
            f'<text x="{col_cx:.1f}" y="945" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="24" font-weight="700" fill="{fg_muted}">{fc.low_c}° · {fc.low_f}°F</text>'
        )

    cond_fs = 22 if len(weather.condition) > 12 else 26
    temp_hero_fs = 74 if abs(weather.temp_f) >= 100 else 80
    stale_badge = " · CACHED" if weather.stale else ""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <rect x="0" y="0" width="{w}" height="{h}" fill="{bg}"/>
  <rect x="18" y="18" width="{w - 36}" height="{h - 36}" rx="14" fill="none" stroke="{rule_soft}" stroke-width="1.8"/>

  <!-- Bold Masthead -->
  <text x="44" y="64" font-family="Noto Sans, sans-serif" font-size="24" font-weight="800" letter-spacing="2.8" fill="{fg}">{_esc(short_location)}{_esc(stale_badge)}</text>
  {moon_disc_svg(weather.moon_cycle, 640, 56, r=12.0, fg=fg, bg=bg)}
  <text x="662" y="64" font-family="Noto Sans, sans-serif" font-size="21" font-weight="700" letter-spacing="1.2" fill="{fg_muted}">{_esc(weather.moon_name.upper())} · {weather.moon_illum}%</text>
  <text x="1404" y="64" text-anchor="end" font-family="Noto Sans, sans-serif" font-size="23" font-weight="800" letter-spacing="2.0" fill="{fg_2}">{_esc(greeting)}</text>

  <line x1="44" y1="83" x2="1404" y2="83" stroke="{rule_strong}" stroke-width="2.8"/>
  <line x1="44" y1="90" x2="1404" y2="90" stroke="{rule_strong}" stroke-width="1.2"/>

  <!-- Left Page: Giant Clock + Bold Quote + Zen Buddy -->
  <text x="372" y="142" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="28" font-weight="800" letter-spacing="2.4" fill="{fg_2}">{_esc(date_str)}</text>
  <text x="382" y="318" text-anchor="middle" fill="{fg}">
    <tspan font-family="Noto Serif, Georgia, serif" font-size="{clock_font_size}" font-weight="700">{_esc(time_str)}</tspan>{ampm_tspan}
  </text>

  <line x1="182" y1="358" x2="342" y2="358" stroke="{rule_soft}" stroke-width="1.8"/>
  <polygon points="372,348 382,358 372,368 362,358" fill="{fg}"/>
  <line x1="402" y1="358" x2="562" y2="358" stroke="{rule_soft}" stroke-width="1.8"/>

  {"".join(q_tspans)}
  <text x="372" y="{author_y}" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="25" font-weight="800" letter-spacing="2.4" fill="{fg}">— {_esc(quote.author.upper())} —</text>
  {source_svg}

  <g>
    {zen_buddy_svg(buddy.key, 198, 920, size=106, fg=fg, bg=bg)}
    <rect x="268" y="882" width="356" height="76" rx="38" fill="{card_bg}" stroke="{rule_strong}" stroke-width="2.4"/>
    <text x="446" y="914" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="24" font-weight="800" fill="{fg}">✦  {_esc(buddy.label)}  ✦</text>
    <text x="446" y="944" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="21" font-weight="700" fill="{fg_2}">{_esc(buddy.kaomoji)}</text>
  </g>

  <!-- Center Book Spine -->
  <line x1="718" y1="112" x2="718" y2="972" stroke="{rule_soft}" stroke-width="1.8"/>

  <!-- Right Page: High-Contrast Pasadena Weather & Almanac Card -->
  <rect x="736" y="108" width="670" height="868" rx="24" fill="{card_bg}" stroke="{rule_strong}" stroke-width="2.8"/>

  {weather_icon_svg(weather.icon_key, 841, 212, size=122, fg=fg, bg=card_bg)}
  <text x="841" y="318" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="{cond_fs}" font-weight="800" fill="{fg}">{_esc(weather.condition)}</text>
  <line x1="946" y1="136" x2="946" y2="346" stroke="{rule_soft}" stroke-width="1.6"/>

  <text x="1060" y="226" text-anchor="middle" font-family="Noto Serif, Georgia, serif" font-size="{temp_hero_fs}" font-weight="700" fill="{fg}">{weather.temp_c}°C</text>
  <line x1="1174" y1="154" x2="1174" y2="238" stroke="{rule_soft}" stroke-width="2.6"/>
  <text x="1288" y="226" text-anchor="middle" font-family="Noto Serif, Georgia, serif" font-size="{temp_hero_fs}" font-weight="700" fill="{fg}">{weather.temp_f}°F</text>

  <text x="1176" y="284" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="26" font-weight="700" fill="{fg_2}">Feels {weather.feels_c}°C / {weather.feels_f}°F</text>
  <text x="1176" y="329" text-anchor="middle" font-family="Noto Sans, sans-serif" font-size="26" font-weight="800" fill="{fg}">H {weather.high_c}°C / {weather.high_f}°F  ·  L {weather.low_c}°C / {weather.low_f}°F</text>

  <line x1="736" y1="366" x2="1406" y2="366" stroke="{rule_soft}" stroke-width="1.8"/>
  {"".join(metric_svg)}
  <line x1="736" y1="472" x2="1406" y2="472" stroke="{rule_soft}" stroke-width="1.8"/>

  {hourly_curve_svg(weather.hourly, 736, 1406, 480, 714, fg=fg, fg_muted=fg_muted, card_bg=card_bg, rule_soft=rule_soft, compact=True)}
  <line x1="736" y1="720" x2="1406" y2="720" stroke="{rule_soft}" stroke-width="1.8"/>

  {"".join(fc_parts)}

  <!-- Footer -->
  <line x1="44" y1="994" x2="1404" y2="994" stroke="{rule_soft}" stroke-width="1.6"/>
  {_mini_lotus_svg(60, 1022, fg_muted)}
  <text x="84" y="1030" font-family="Noto Sans, sans-serif" font-size="20" font-weight="700" letter-spacing="2.2" fill="{fg_muted}">BREATHE IN · BREATHE OUT</text>
  <text x="1404" y="1030" text-anchor="end" font-family="Noto Sans, sans-serif" font-size="20" font-weight="700" letter-spacing="1.8" fill="{fg_muted}">SYNCED {_esc(sync_str)}  ✦</text>
</svg>
"""


def render_dashboard_files(
    svg_content: str,
    svg_path: Path,
    png_path: Path,
    preview_png_path: Path | None = None,
    width: int = 1072,
    height: int = 1448,
    orientation: str = "portrait",
) -> Path:
    """Write SVG, upright web preview PNG, and Kindle-framebuffer 8-bit grayscale non-interlaced PNG."""
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    tag = f".{os.getpid()}.{threading.get_ident()}"
    tmp_svg = svg_path.with_name(f"{svg_path.name}{tag}.tmp")
    raw_png = png_path.with_name(f"{png_path.stem}{tag}.raw.png")
    tmp_png = png_path.with_name(f"{png_path.stem}{tag}.png")
    tmp_prev = preview_png_path.with_name(f"{preview_png_path.stem}{tag}.png") if preview_png_path is not None else None

    try:
        tmp_svg.write_text(svg_content, encoding="utf-8")

        is_land = orientation.startswith("landscape")
        svg_w = width if not is_land else height
        svg_h = height if not is_land else width

        subprocess.run(
            [
                "rsvg-convert",
                "-w",
                str(svg_w),
                "-h",
                str(svg_h),
                "-b",
                "white",
                "-o",
                str(raw_png),
                str(tmp_svg),
            ],
            check=True,
        )
        os.replace(tmp_svg, svg_path)

        gray_flags = [
            "-background",
            "white",
            "-alpha",
            "remove",
            "-alpha",
            "off",
            "-colorspace",
            "Gray",
            "-depth",
            "8",
            "-define",
            "png:color-type=0",
            "-define",
            "png:bit-depth=8",
            "-strip",
        ]

        if preview_png_path is not None and tmp_prev is not None:
            subprocess.run(["magick", str(raw_png), *gray_flags, str(tmp_prev)], check=True)
            os.replace(tmp_prev, preview_png_path)

        magick_cmd = ["magick", str(raw_png)]
        if orientation == "landscape":
            # 90° CW: Top of dashboard on physical Right edge (USB port on Right when held sideways)
            magick_cmd.extend(["-rotate", "90"])
        elif orientation == "portrait_inverted":
            # 180° CW: Top of dashboard on physical Bottom edge (USB port on Top when standing upright)
            magick_cmd.extend(["-rotate", "180"])
        elif orientation == "landscape_ccw":
            # 270° CW: Top of dashboard on physical Left edge (USB port on Left when held sideways)
            magick_cmd.extend(["-rotate", "270"])
        magick_cmd.extend([*gray_flags, str(tmp_png)])
        subprocess.run(magick_cmd, check=True)
        os.replace(tmp_png, png_path)
    finally:
        for p in (tmp_svg, raw_png, tmp_png, tmp_prev):
            if p is not None:
                p.unlink(missing_ok=True)
    return png_path
