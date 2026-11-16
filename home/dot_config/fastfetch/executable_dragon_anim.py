#!/usr/bin/env python3
"""
High-Detail Subpixel Braille & TrueColor Animated Dragon for Fastfetch.

Inspired by the terminal engineering of:
- Gentleman-Programming/gentle-shell (Braille subpixel art, calligraphic path-stroke
  ignition with tip/fresh/ink states, sinusoidal scale & rose pulse, specular glint
  sweeps, and quality/performance/potato animation policies).
- GitHub Copilot CLI (Semantic material role layering, dynamic runtime shaders,
  and ANSI run-length segment batching).

Renders an 88x108 square-subpixel canvas (44x27 terminal cells) at 30 FPS.
"""

import math
import os
import re
import select
import shutil
import signal
import subprocess
import sys
import termios
import time
import tty

W = 44
H = 27
PW = W * 2  # 88 horizontal subpixels
PH = H * 4  # 108 vertical subpixels (1:1 square aspect ratio!)
GAP = "   "

RESET = "\x1b[0m"
BRAILLE_BITS = (
    (0x01, 0x08),
    (0x02, 0x10),
    (0x04, 0x20),
    (0x40, 0x80),
)

# Semantic Material Roles (Copilot CLI layered architecture)
MAT_EMPTY = 0
MAT_CLOUD = 1
MAT_FAR_MTN_SHADOW = 2
MAT_FAR_MTN_ROCK = 3
MAT_FAR_MTN_SNOW = 4
MAT_NEAR_MTN_SHADOW = 5
MAT_NEAR_MTN_ROCK = 6
MAT_NEAR_MTN_SNOW = 7
MAT_PINE = 8
MAT_MIST = 9
MAT_MOON = 10

MAT_DRG_WING_FAR = 11
MAT_DRG_WING_FAR_BONE = 12
MAT_DRG_WING_MEMBRANE = 13
MAT_DRG_BODY = 14
MAT_DRG_BELLY = 15
MAT_DRG_WING_BONE = 16
MAT_DRG_HEAD = 17
MAT_DRG_HORN = 18
MAT_DRG_EYE = 19

MAT_FIRE_OUTER = 20
MAT_FIRE_MID = 21
MAT_FIRE_CORE = 22
MAT_FIRE_SPARK = 23

# Base Palette (Rosé Pine / Catppuccin Mocha fantasy dusk)
MAT_STYLE: dict[int, tuple[int, int, int, bool]] = {
    MAT_CLOUD:             (118, 112, 150, False),
    MAT_FAR_MTN_SHADOW:    (96,  82,  130, False),
    MAT_FAR_MTN_ROCK:      (148, 126, 178, False),
    MAT_FAR_MTN_SNOW:      (228, 226, 248, True),
    MAT_NEAR_MTN_SHADOW:   (50,  96,  116, False),
    MAT_NEAR_MTN_ROCK:     (88,  152, 166, False),
    MAT_NEAR_MTN_SNOW:     (168, 222, 232, True),
    MAT_PINE:              (45,  118, 144, True),
    MAT_MIST:              (156, 207, 216, False),
    MAT_MOON:              (252, 212, 138, True),
    MAT_DRG_WING_FAR:      (152, 74,  96,  False),
    MAT_DRG_WING_FAR_BONE: (198, 128, 78,  False),
    MAT_DRG_WING_MEMBRANE: (228, 142, 56,  False),
    MAT_DRG_BODY:          (238, 106, 144, True),
    MAT_DRG_BELLY:         (246, 196, 122, True),
    MAT_DRG_WING_BONE:     (252, 202, 108, True),
    MAT_DRG_HEAD:          (244, 116, 152, True),
    MAT_DRG_HORN:          (254, 222, 152, True),
    MAT_DRG_EYE:           (110, 250, 255, True),
    MAT_FIRE_OUTER:        (242, 75,  85,  True),
    MAT_FIRE_MID:          (255, 152, 28,  True),
    MAT_FIRE_CORE:         (255, 250, 210, True),
    MAT_FIRE_SPARK:        (255, 215, 95,  True),
}

# Subpixel importance weights so fine anatomical features (eye, horns, bones, belly scutes, snow ridges) pop
MAT_WEIGHT: dict[int, float] = {
    MAT_DRG_EYE:           12.0,
    MAT_FIRE_SPARK:         4.5,
    MAT_FIRE_CORE:          3.0,
    MAT_DRG_HORN:           2.6,
    MAT_DRG_WING_BONE:      2.4,
    MAT_DRG_BELLY:          2.2,
    MAT_FIRE_MID:           1.8,
    MAT_NEAR_MTN_SNOW:      1.8,
    MAT_FAR_MTN_SNOW:       1.8,
    MAT_MOON:               2.5,
}

STARS = [
    (0, 3, "✦"), (0, 16, "·"), (0, 31, "+"),
    (1, 8, "·"), (1, 28, "✧"), (2, 2, "+"),
    (2, 33, "·"), (3, 1, "·"), (4, 3, "✦"),
    (8, 2, "·"), (9, 39, "+"), (10, 6, "·"),
    (10, 33, "✧"), (11, 19, "·"), (11, 41, "+"),
]


def precompute_mountain_profile(peaks: list[tuple[float, float, float, float]], period_px: int, base_y: int) -> tuple[list[int], list[float]]:
    heights = [base_y] * period_px
    slopes = [0.0] * period_px
    for wx in range(period_px):
        best_y = float(base_y)
        best_slope = 0.0
        for pk_x, pk_y, pk_w, asym in peaks:
            dx = wx - pk_x
            if dx > period_px * 0.5:
                dx -= period_px
            elif dx < -period_px * 0.5:
                dx += period_px
            w = pk_w * (1.15 if dx > 0 else asym)
            dist_norm = abs(dx) / w
            if dist_norm < 1.0:
                crag = 1.1 * math.sin(wx * 0.45 + pk_x) + 0.6 * math.cos(wx * 0.9 - pk_y)
                y_val = pk_y + (base_y - pk_y) * (dist_norm ** 1.18) + crag * dist_norm
                if y_val < best_y:
                    best_y = y_val
                    best_slope = 1.0 if dx < 0 else -1.0
        heights[wx] = int(round(best_y))
        slopes[wx] = best_slope
    return heights, slopes


FAR_PERIOD = 120
FAR_PEAKS = [(18.0, 52.0, 22.0, 0.9), (54.0, 46.0, 28.0, 0.85), (95.0, 54.0, 24.0, 0.95)]
FAR_HEIGHTS, FAR_SLOPES = precompute_mountain_profile(FAR_PEAKS, FAR_PERIOD, 88)

NEAR_PERIOD = 120
NEAR_PEAKS = [(10.0, 68.0, 18.0, 0.9), (38.0, 63.0, 22.0, 0.85), (70.0, 66.0, 20.0, 0.9), (102.0, 64.0, 22.0, 0.9)]
NEAR_HEIGHTS, NEAR_SLOPES = precompute_mountain_profile(NEAR_PEAKS, NEAR_PERIOD, 99)


def dist_to_segment(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> tuple[float, float]:
    dx, dy = x2 - x1, y2 - y1
    if dx == 0.0 and dy == 0.0:
        return math.hypot(px - x1, py - y1), 0.0
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t_clamped = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return math.hypot(px - (x1 + t_clamped * dx), py - (y1 + t_clamped * dy)), t_clamped


def eval_bezier(pts: list[tuple[float, float]], t: float) -> tuple[float, float]:
    tmp = list(pts)
    n = len(tmp) - 1
    for k in range(1, n + 1):
        for i in range(n - k + 1):
            tmp[i] = (
                (1.0 - t) * tmp[i][0] + t * tmp[i + 1][0],
                (1.0 - t) * tmp[i][1] + t * tmp[i + 1][1],
            )
    return tmp[0]


def sample_bezier(pts: list[tuple[float, float]], steps: int = 12) -> list[tuple[float, float]]:
    return [eval_bezier(pts, s / steps) for s in range(steps + 1)]


def draw_thick_segment(grid: list[list[int]], x1: float, y1: float, x2: float, y2: float, r1: float, r2: float, mat: int) -> None:
    max_r = max(r1, r2)
    min_x = max(0, int(min(x1, x2) - max_r - 1))
    max_x = min(PW - 1, int(max(x1, x2) + max_r + 1))
    min_y = max(0, int(min(y1, y2) - max_r - 1))
    max_y = min(PH - 1, int(max(y1, y2) + max_r + 1))
    for py in range(min_y, max_y + 1):
        row = grid[py]
        for px in range(min_x, max_x + 1):
            d, t = dist_to_segment(px, py, x1, y1, x2, y2)
            if d <= r1 + (r2 - r1) * t:
                row[px] = mat


def draw_bezier_stroke(
    grid: list[list[int]],
    pts: list[tuple[float, float]],
    radii: list[float],
    mat: int,
    steps: int = 16,
    carve_border: float = 0.0,
    belly_mat: int | None = None,
    spine_mat: int | None = None,
) -> None:
    sampled = []
    nr = len(radii) - 1
    for s in range(steps + 1):
        t = s / steps
        bx, by = eval_bezier(pts, t)
        r_idx = t * nr
        i0 = int(r_idx)
        i1 = min(nr, i0 + 1)
        rt = r_idx - i0
        r = radii[i0] * (1.0 - rt) + radii[i1] * rt
        sampled.append((bx, by, r))

    if carve_border > 0.0:
        for i in range(steps):
            x1, y1, r1 = sampled[i]
            x2, y2, r2 = sampled[i + 1]
            draw_thick_segment(grid, x1, y1, x2, y2, r1 + carve_border, r2 + carve_border, MAT_EMPTY)

    for i in range(steps):
        x1, y1, r1 = sampled[i]
        x2, y2, r2 = sampled[i + 1]
        max_r = max(r1, r2)
        min_x = max(0, int(min(x1, x2) - max_r - 1))
        max_x = min(PW - 1, int(max(x1, x2) + max_r + 1))
        min_y = max(0, int(min(y1, y2) - max_r - 1))
        max_y = min(PH - 1, int(max(y1, y2) + max_r + 1))
        dx, dy = x2 - x1, y2 - y1
        seg_len = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / seg_len, dx / seg_len
        if ny < 0.0:
            nx, ny = -nx, -ny
        for py in range(min_y, max_y + 1):
            row = grid[py]
            for px in range(min_x, max_x + 1):
                d, t_seg = dist_to_segment(px, py, x1, y1, x2, y2)
                r = r1 + (r2 - r1) * t_seg
                if d <= r:
                    if belly_mat is not None or spine_mat is not None:
                        cx = x1 + t_seg * dx
                        cy = y1 + t_seg * dy
                        proj = (px - cx) * nx + (py - cy) * ny
                        if belly_mat is not None and r > 1.3 and proj > r * 0.25:
                            row[px] = belly_mat if int((i + t_seg) * 1.4) % 2 == 0 else mat
                        elif spine_mat is not None and proj < -r * 0.55 and int((i + t_seg) * 1.2) % 2 == 0:
                            row[px] = spine_mat
                        else:
                            row[px] = mat
                    else:
                        row[px] = mat


def draw_curved_wing_panel(
    grid: list[list[int]],
    curve_a: list[tuple[float, float]],
    curve_b: list[tuple[float, float]],
    wrist: tuple[float, float],
    mat_membrane: int,
    is_far: bool = False,
) -> None:
    tip_a = curve_a[-1]
    tip_b = curve_b[-1]
    wx, wy = wrist
    pull = 0.26 if not is_far else 0.22
    mx = (tip_a[0] + tip_b[0]) * 0.5 * (1.0 - pull) + wx * pull
    my = (tip_a[1] + tip_b[1]) * 0.5 * (1.0 - pull) + wy * pull
    scallop = sample_bezier([tip_a, (mx, my), tip_b], steps=8)

    poly = list(curve_a) + scallop[1:-1] + list(reversed(curve_b))
    n = len(poly)
    min_y = max(0, int(min(p[1] for p in poly)))
    max_y = min(PH - 1, int(max(p[1] for p in poly)))

    for py in range(min_y, max_y + 1):
        nodes = []
        j = n - 1
        for i in range(n):
            yi = poly[i][1]
            yj = poly[j][1]
            if (yi < py and yj >= py) or (yj < py and yi >= py):
                xi = poly[i][0]
                xj = poly[j][0]
                nodes.append(xi + (py - yi) / (yj - yi) * (xj - xi))
            j = i
        nodes.sort()
        row = grid[py]
        for k in range(0, len(nodes) - 1, 2):
            x_start = max(0, int(math.ceil(nodes[k])))
            x_end = min(PW - 1, int(math.floor(nodes[k + 1])))
            for px in range(x_start, x_end + 1):
                if is_far:
                    row[px] = mat_membrane if (px + py) % 2 == 0 else MAT_EMPTY
                else:
                    row[px] = mat_membrane if (px + py * 2) % 3 != 0 else MAT_EMPTY

    for i in range(len(scallop) - 1):
        draw_thick_segment(grid, scallop[i][0], scallop[i][1], scallop[i + 1][0], scallop[i + 1][1], 0.55, 0.55, mat_membrane)


def draw_mountains_fast(
    grid: list[list[int]],
    heights: list[int],
    slopes: list[float],
    scroll_px: int,
    period_px: int,
    base_y: int,
    mat_snow: int,
    mat_rock: int,
    mat_shadow: int,
    snow_depth: int,
    is_near: bool,
) -> None:
    for px in range(PW):
        wx = (px + scroll_px) % period_px
        top_y = heights[wx]
        slope = slopes[wx]
        if is_near and 0 <= top_y - 1 < PH:
            grid[top_y - 1][px] = MAT_EMPTY
            if 0 <= top_y - 2 < PH and px % 2 == 0:
                grid[top_y - 2][px] = MAT_EMPTY

        snow_lim = snow_depth + ((px * 3) % 3)
        for py in range(max(0, top_y), min(PH, base_y)):
            depth = py - top_y
            if depth <= 1 or (depth < snow_lim and slope > 0.0):
                grid[py][px] = mat_snow
            elif slope > 0.0:
                grid[py][px] = mat_rock if (px + py * 2) % 6 != 0 else MAT_EMPTY
            else:
                if depth == 2 and px % 2 == 0:
                    grid[py][px] = MAT_EMPTY
                else:
                    grid[py][px] = mat_shadow if (px + py) % 2 == 0 else MAT_EMPTY


def draw_pines_and_mist(grid: list[list[int]], scroll_px: int, frame_idx: int) -> None:
    period = 120
    for px in range(PW):
        wx = (px + int(scroll_px * 1.4)) % period
        tree_idx = wx // 8
        local_x = (wx % 8) - 3.5
        tree_h = 9 + (tree_idx * 29) % 5
        top_y = 100 - tree_h
        for py in range(top_y, 100):
            rel_y = py - top_y
            tier = rel_y % 3
            max_w = 0.5 + rel_y * 0.26 + (0.45 if tier == 2 else 0.0)
            if abs(local_x) <= max_w + 0.7:
                grid[py][px] = MAT_EMPTY if (abs(local_x) > max_w or rel_y == 0) else MAT_PINE

    for py in range(99, PH):
        row = grid[py]
        if py in (99, 103, 106):
            for px in range(PW):
                row[px] = MAT_EMPTY
            continue
        for px in range(PW):
            wave = math.sin(px * 0.16 - frame_idx * 0.22 + py * 0.7) + 0.5 * math.cos(px * 0.31 + frame_idx * 0.15)
            if wave > -0.1 and ((px + py) % 2 == 0 or wave > 0.55):
                row[px] = MAT_MIST
            else:
                row[px] = MAT_EMPTY


def draw_moon_and_clouds(grid: list[list[int]], frame_idx: int) -> None:
    clouds = [
        (11.0, 3.0, 7.5, 1.4),
        (73.0, 41.0, 9.5, 1.5),
    ]
    for cx0, cy0, cw, ch in clouds:
        cx = (cx0 - frame_idx * 0.25) % (PW + 18) - 9
        min_x = max(0, int(cx - cw))
        max_x = min(PW - 1, int(cx + cw))
        min_y = max(0, int(cy0 - ch - 1))
        max_y = min(PH - 1, int(cy0 + ch + 1))
        for py in range(min_y, max_y + 1):
            for px in range(min_x, max_x + 1):
                nx = (px - cx) / cw
                ny = (py - (cy0 + 0.5 * math.sin(px * 0.3))) / ch
                if nx * nx + ny * ny <= 1.0 and (px + py) % 2 == 0:
                    grid[py][px] = MAT_CLOUD

    # Sculpted Braille Crescent Moon at upper right (px=78.5, py=6.2)
    for py in range(0, 13):
        for px in range(71, 86):
            d_outer = math.hypot(px - 78.5, py - 6.2)
            d_inner = math.hypot(px - 75.7, py - 5.0)
            if d_outer <= 5.4 and d_inner > 4.5:
                grid[py][px] = MAT_MOON


def draw_dragon_and_fire(grid: list[list[int]], phase: float, frame_idx: int) -> None:
    flap = math.cos(phase)       # +1 upstroke peak, -1 downstroke peak
    flap_vel = -math.sin(phase)  # wingtip flexibility lag
    bob_y = -2.0 * flap

    # 1. FAR WING (3D perspective behind neck and near wing)
    far_shoulder = (45.0, 28.0 + bob_y)
    far_wrist = (51.5, 12.0 + bob_y - 6.5 * flap + 1.5 * flap_vel)
    f_curve1 = sample_bezier([far_shoulder, (48.0, 19.0 + bob_y - 4.0 * flap), far_wrist], steps=10)
    f_f1 = sample_bezier([far_wrist, (45.0, 7.0 + bob_y - 8.0 * flap), (36.0, 7.0 + bob_y - 9.0 * flap + 2.5 * flap_vel)], steps=10)
    f_f2 = sample_bezier([far_wrist, (46.0, 13.0 + bob_y - 6.0 * flap), (39.0, 16.0 + bob_y - 6.5 * flap + 2.0 * flap_vel)], steps=10)
    f_f3 = sample_bezier([far_wrist, (46.0, 20.0 + bob_y - 3.0 * flap), (43.0, 25.0 + bob_y)], steps=10)

    draw_curved_wing_panel(grid, f_f1, f_f2, far_wrist, MAT_DRG_WING_FAR, is_far=True)
    draw_curved_wing_panel(grid, f_f2, f_f3, far_wrist, MAT_DRG_WING_FAR, is_far=True)
    for c_pts in (f_curve1, f_f1, f_f2):
        draw_bezier_stroke(grid, c_pts, [0.8, 0.55], MAT_DRG_WING_FAR_BONE, steps=10)

    # 2. NEAR WING GEOMETRY
    shoulder = (40.0, 30.5 + bob_y)
    elbow = (34.0, 24.5 + bob_y - 6.5 * flap)
    wrist = (39.5, 19.5 + bob_y - 12.5 * flap + 2.0 * flap_vel)

    finger1 = sample_bezier([
        wrist,
        (25.0, 18.5 + bob_y - 14.0 * flap + 3.0 * flap_vel),
        (9.0,  24.5 + bob_y - 14.5 * flap + 4.5 * flap_vel),
    ], steps=14)
    finger2 = sample_bezier([
        wrist,
        (26.0, 25.0 + bob_y - 12.5 * flap + 2.5 * flap_vel),
        (12.5, 32.0 + bob_y - 13.0 * flap + 3.8 * flap_vel),
    ], steps=14)
    finger3 = sample_bezier([
        wrist,
        (29.5, 29.5 + bob_y - 9.5 * flap + 2.0 * flap_vel),
        (20.5, 37.5 + bob_y - 10.5 * flap + 2.8 * flap_vel),
    ], steps=12)
    finger4 = sample_bezier([
        wrist,
        (34.0, 32.0 + bob_y - 6.0 * flap + 1.2 * flap_vel),
        (29.5, 38.0 + bob_y - 6.0 * flap + 1.5 * flap_vel),
    ], steps=12)
    flank_curve = sample_bezier([wrist, (38.0, 27.5 + bob_y - 5.5 * flap), (36.5, 34.0 + bob_y)], steps=10)

    def render_near_wing() -> None:
        draw_bezier_stroke(grid, [shoulder, elbow, wrist], [1.9, 1.8, 1.7], MAT_EMPTY, steps=12)
        draw_bezier_stroke(grid, finger1, [1.7, 1.4, 1.0], MAT_EMPTY, steps=14)

        draw_curved_wing_panel(grid, finger1, finger2, wrist, MAT_DRG_WING_MEMBRANE, is_far=False)
        draw_curved_wing_panel(grid, finger2, finger3, wrist, MAT_DRG_WING_MEMBRANE, is_far=False)
        draw_curved_wing_panel(grid, finger3, finger4, wrist, MAT_DRG_WING_MEMBRANE, is_far=False)
        draw_curved_wing_panel(grid, finger4, flank_curve, wrist, MAT_DRG_WING_MEMBRANE, is_far=False)
        draw_curved_wing_panel(
            grid,
            sample_bezier([wrist, elbow, shoulder], steps=10),
            flank_curve,
            wrist,
            MAT_DRG_WING_MEMBRANE,
            is_far=False,
        )

        for f_pts in (finger2, finger3, finger4):
            draw_bezier_stroke(grid, f_pts, [1.3, 1.1, 0.85], MAT_EMPTY, steps=12)

        draw_bezier_stroke(grid, [shoulder, elbow, wrist], [1.35, 1.25, 1.15], MAT_DRG_WING_BONE, steps=12)
        draw_bezier_stroke(grid, finger1, [1.15, 0.95, 0.65], MAT_DRG_WING_BONE, steps=14)
        draw_bezier_stroke(grid, finger2, [0.85, 0.70, 0.50], MAT_DRG_WING_BONE, steps=14)
        draw_bezier_stroke(grid, finger3, [0.80, 0.65, 0.50], MAT_DRG_WING_BONE, steps=12)
        draw_bezier_stroke(grid, finger4, [0.75, 0.60, 0.45], MAT_DRG_WING_BONE, steps=12)
        claw_dy = -3.0 if flap >= 0.0 else 3.0
        draw_thick_segment(grid, wrist[0], wrist[1], wrist[0] + 2.8, wrist[1] + claw_dy, 0.85, 0.35, MAT_DRG_HORN)

    if flap >= 0.0:
        render_near_wing()

    # 3. SINUOUS WHIP-TAIL, MUSCULAR TORSO, S-NECK & DORSAL SPINES
    t0 = (3.5, 30.0 + bob_y + 4.0 * math.sin(phase - 2.3))
    t1 = (10.5, 42.0 + bob_y + 3.2 * math.sin(phase - 1.5))
    t2 = (19.5, 37.0 + bob_y + 1.8 * math.sin(phase - 0.8))
    hip = (28.5, 35.5 + bob_y)
    chest = (43.0, 33.0 + bob_y)
    neck_mid = (52.5, 24.5 + bob_y)
    head_base = (57.5, 17.5 + bob_y * 0.7)

    draw_bezier_stroke(grid, [t0, t1, t2, hip], [0.55, 0.95, 1.45, 2.0], MAT_DRG_BODY, steps=20, carve_border=0.9)
    draw_thick_segment(grid, t0[0] - 2.5, t0[1] - 0.8, t0[0] + 1.5, t0[1] - 2.4, 0.7, 0.9, MAT_DRG_HORN)
    draw_thick_segment(grid, t0[0] - 2.5, t0[1] - 0.8, t0[0] + 1.2, t0[1] + 2.2, 0.7, 0.9, MAT_DRG_HORN)

    draw_bezier_stroke(
        grid,
        [hip, (36.0, 36.5 + bob_y), chest, neck_mid, head_base],
        [2.0, 2.9, 3.4, 2.4, 2.0],
        MAT_DRG_BODY,
        steps=24,
        carve_border=1.0,
        belly_mat=MAT_DRG_BELLY,
        spine_mat=MAT_DRG_HORN,
    )

    # Hind leg & talons
    knee = (34.0, 40.5 + bob_y)
    ankle = (28.5, 44.0 + bob_y)
    draw_thick_segment(grid, hip[0] + 2.0, hip[1] + 1.0, knee[0], knee[1], 1.6, 1.15, MAT_DRG_BODY)
    draw_thick_segment(grid, knee[0], knee[1], ankle[0], ankle[1], 1.1, 0.8, MAT_DRG_BODY)
    draw_thick_segment(grid, ankle[0], ankle[1], ankle[0] + 3.2, ankle[1] + 2.5, 0.65, 0.35, MAT_DRG_HORN)
    draw_thick_segment(grid, ankle[0], ankle[1], ankle[0] + 1.2, ankle[1] + 3.2, 0.65, 0.35, MAT_DRG_HORN)
    draw_thick_segment(grid, ankle[0], ankle[1], ankle[0] - 1.6, ankle[1] + 2.2, 0.55, 0.35, MAT_DRG_HORN)

    if flap < 0.0:
        render_near_wing()

    # 4. SCULPTED DRAGON HEAD, TWIN HORNS, ROARING JAWS & GLOWING EYE
    hx, hy = head_base
    draw_thick_segment(grid, hx - 1.0, hy - 1.0, hx + 9.0, hy + 1.0, 3.6, 2.8, MAT_EMPTY)

    draw_bezier_stroke(
        grid,
        [(hx + 0.5, hy - 1.5), (hx - 4.5, hy - 5.5), (hx - 11.5, hy - 6.5)],
        [1.15, 0.85, 0.4],
        MAT_DRG_HORN,
        steps=12,
    )
    draw_bezier_stroke(
        grid,
        [(hx - 0.5, hy + 0.2), (hx - 4.5, hy - 2.0), (hx - 9.0, hy - 2.5)],
        [0.85, 0.65, 0.35],
        MAT_DRG_HORN,
        steps=10,
    )

    draw_thick_segment(grid, hx - 0.5, hy - 0.8, hx + 8.8, hy - 0.8, 1.75, 1.05, MAT_DRG_HEAD)
    draw_thick_segment(grid, hx + 7.5, hy - 1.5, hx + 9.2, hy - 3.2, 0.65, 0.35, MAT_DRG_HORN)
    draw_thick_segment(grid, hx + 0.2, hy + 1.0, hx + 7.5, hy + 4.2, 1.2, 0.7, MAT_DRG_HEAD)
    draw_thick_segment(grid, hx + 2.5, hy + 0.9, hx + 8.5, hy + 2.1, 0.85, 1.1, MAT_EMPTY)

    ex, ey = int(round(hx + 2.0)), int(round(hy - 1.2))
    for dy in range(2):
        for dx in range(2):
            if 0 <= ex + dx < PW and 0 <= ey + dy < PH:
                grid[ey + dy][ex + dx] = MAT_DRG_EYE

    # 5. VOLUMETRIC FIRE BREATH
    mouth_x = hx + 7.5
    mouth_y = hy + 1.6
    for px in range(int(mouth_x), PW):
        dist = px - mouth_x
        t = dist / max(1.0, (PW - 1 - mouth_x))
        wave = (
            math.sin(dist * 0.38 - frame_idx * 0.85) * (1.0 + 2.4 * t)
            + 0.5 * math.cos(dist * 0.75 - frame_idx * 1.3) * t
        )
        center_y = mouth_y + 1.0 * t + wave * 0.55
        spread = 1.1 + 5.0 * (t ** 0.85)

        for py in range(max(0, int(center_y - spread - 2)), min(PH, int(center_y + spread + 3))):
            dy = abs(py - center_y)
            flutter = 0.75 * math.sin(px * 0.6 + py * 0.5 - frame_idx * 0.9)
            eff_d = dy + flutter
            if eff_d <= spread * 0.36 and t < 0.78:
                grid[py][px] = MAT_FIRE_CORE
            elif eff_d <= spread * 0.68 and t < 0.92:
                grid[py][px] = MAT_FIRE_MID
            elif eff_d <= spread:
                if (px + py + frame_idx) % 2 == 0 or eff_d <= spread * 0.82:
                    grid[py][px] = MAT_FIRE_OUTER
            elif dist > 6.0 and eff_d > spread + 0.5 and eff_d <= spread + 2.2 and ((px * 7 + py * 13 + frame_idx * 5) % 19 == 0):
                grid[py][px] = MAT_FIRE_SPARK


def clamp8(v: float, quantize: int = 4) -> int:
    iv = 0 if v < 0.0 else (255 if v > 255.0 else int(v))
    if quantize > 1 and iv < 252:
        iv = (iv // quantize) * quantize
    return iv


def render_scene_frame(frame_idx: int, is_final: bool = False) -> list[str]:
    phase = 0.0 if is_final else (frame_idx / 20.0) * (2.0 * math.pi)
    grid = [[MAT_EMPTY for _ in range(PW)] for _ in range(PH)]

    scroll_far = 0 if is_final else (frame_idx // 2)
    scroll_near = 0 if is_final else frame_idx

    draw_moon_and_clouds(grid, 0 if is_final else frame_idx)
    draw_mountains_fast(
        grid, FAR_HEIGHTS, FAR_SLOPES, scroll_far, FAR_PERIOD, 88,
        MAT_FAR_MTN_SNOW, MAT_FAR_MTN_ROCK, MAT_FAR_MTN_SHADOW, 11, False
    )
    draw_mountains_fast(
        grid, NEAR_HEIGHTS, NEAR_SLOPES, scroll_near, NEAR_PERIOD, 99,
        MAT_NEAR_MTN_SNOW, MAT_NEAR_MTN_ROCK, MAT_NEAR_MTN_SHADOW, 9, True
    )
    draw_pines_and_mist(grid, scroll_near, 0 if is_final else frame_idx)
    draw_dragon_and_fire(grid, phase, 0 if is_final else frame_idx)

    star_map: dict[tuple[int, int], tuple[str, int, int, int, bool]] = {}
    for idx, (sr, sc, sch) in enumerate(STARS):
        sc_pos = sc if is_final else (sc - frame_idx // 8) % W
        twinkle = 0.5 + 0.5 * math.sin(frame_idx * 0.45 + idx * 1.9) if not is_final else (1.0 if sch in "✦+" else 0.6)
        if twinkle > 0.78:
            glyph = "✦" if sch in ("✦", "+") else "✧"
            star_map[(sr, sc_pos)] = (glyph, 240, 236, 255, True)
        elif twinkle < 0.25:
            star_map[(sr, sc_pos)] = ("·", 120, 102, 148, False)
        else:
            star_map[(sr, sc_pos)] = (sch, 165, 145, 195, False)

    # Path-Stroke Calligraphic Intro (Gentle Shell startup-banner technique)
    intro_frames = 18
    in_intro = (not is_final) and (frame_idx < intro_frames)
    intro_prog = (frame_idx + 1) / intro_frames if in_intro else 1.0
    flash_phase = max(0.0, 1.0 - (frame_idx - intro_frames) / 8.0) if (not is_final and intro_frames <= frame_idx < intro_frames + 8) else 0.0

    # Periodic Specular Glint sweeping across the dragon
    glint_cycle = frame_idx % 45
    glint_active = (not is_final) and (20 <= glint_cycle <= 34)
    glint_x = ((glint_cycle - 20) / 14.0) * W if glint_active else -99.0

    fire_power = 1.0 if is_final else (0.82 + 0.18 * math.sin(frame_idx * 0.9))
    fire_cx, fire_cy = 36.5, 4.5

    lines: list[str] = []
    for r in range(H):
        py0 = r * 4
        row_cells: list[tuple[str, int, int, int, bool]] = []

        for c in range(W):
            px0 = c * 2
            mask = 0
            counts: dict[int, float] = {}
            has_spark = False

            for dy in range(4):
                row_slice = grid[py0 + dy]
                for dx in range(2):
                    m = row_slice[px0 + dx]
                    if m != MAT_EMPTY:
                        mask |= BRAILLE_BITS[dy][dx]
                        w = MAT_WEIGHT.get(m, 1.0)
                        counts[m] = counts.get(m, 0.0) + w
                        if m == MAT_FIRE_SPARK:
                            has_spark = True

            if mask == 0:
                if (r, c) in star_map:
                    ch, sr_c, sg_c, sb_c, s_bold = star_map[(r, c)]
                    if in_intro and (c / W) > intro_prog:
                        row_cells.append((" ", 0, 0, 0, False))
                    else:
                        row_cells.append((ch, sr_c, sg_c, sb_c, s_bold))
                else:
                    row_cells.append((" ", 0, 0, 0, False))
                continue

            dom_mat = max(counts.items(), key=lambda kv: kv[1])[0]

            if r < 12:
                stroke_pos = (c / W) * 0.88 + (abs(r - 5) / 12.0) * 0.12
            else:
                stroke_pos = (c / W) * 0.82 + ((r - 12) / 15.0) * 0.18

            if in_intro and stroke_pos > intro_prog:
                row_cells.append((" ", 0, 0, 0, False))
                continue

            if has_spark and counts.get(MAT_FIRE_SPARK, 0.0) >= max(counts.values()):
                ch = "✦" if (c + r + frame_idx) % 3 == 0 else ("•" if (c + frame_idx) % 2 == 0 else "·")
            else:
                ch = chr(0x2800 + mask)

            base_r, base_g, base_b, bold = MAT_STYLE[dom_mat]
            rf, gf, bf = float(base_r), float(base_g), float(base_b)

            if dom_mat in (MAT_DRG_BODY, MAT_DRG_HEAD, MAT_DRG_WING_MEMBRANE, MAT_DRG_WING_BONE):
                pulse = 0.93 + 0.07 * math.sin(c * 0.35 + r * 0.55 - frame_idx * 0.3)
                rf *= pulse
                gf *= pulse
                bf *= pulse

                if glint_active and abs((c + r * 0.6) - glint_x) <= 1.35:
                    rf = rf * 0.35 + 255.0 * 0.65
                    gf = gf * 0.35 + 242.0 * 0.65
                    bf = bf * 0.35 + 250.0 * 0.65
                    bold = True

            elif dom_mat in (MAT_FAR_MTN_ROCK, MAT_FAR_MTN_SHADOW):
                elev = max(0.0, min(1.0, (r - 11) / 10.0))
                rf *= (1.05 - 0.20 * elev)
                gf *= (1.05 - 0.18 * elev)
                bf *= (1.08 - 0.12 * elev)

            elif dom_mat in (MAT_NEAR_MTN_ROCK, MAT_NEAR_MTN_SHADOW):
                elev = max(0.0, min(1.0, (r - 15) / 9.0))
                rf *= (1.08 - 0.22 * elev)
                gf *= (1.06 - 0.18 * elev)
                bf *= (1.05 - 0.15 * elev)

            elif dom_mat == MAT_MIST:
                mist_wave = 0.88 + 0.12 * math.sin(c * 0.25 - frame_idx * 0.2)
                rf *= mist_wave
                gf *= mist_wave
                bf *= mist_wave

            # Dynamic Fire Point-Light Illumination
            if dom_mat not in (MAT_FIRE_CORE, MAT_FIRE_MID, MAT_FIRE_OUTER, MAT_FIRE_SPARK, MAT_DRG_EYE):
                dist_sq = ((c - fire_cx) * 0.9) ** 2 + ((r - fire_cy) * 1.6) ** 2
                glow = (fire_power * 14.0) / (dist_sq + 10.0)
                if glow > 0.04:
                    rf += 255.0 * glow * 0.45
                    gf += 155.0 * glow * 0.35
                    bf += 40.0 * glow * 0.15

            # Gentle-Shell Path-Stroke Tip & Fresh Ink Shader during Intro
            if in_intro:
                delta = intro_prog - stroke_pos
                if delta <= 0.075:
                    rf, gf, bf, bold = 255.0, 245.0, 252.0, True
                elif delta <= 0.18:
                    rf = min(255.0, rf * 1.25 + 30.0)
                    gf = min(255.0, gf * 1.15 + 20.0)
                    bf = min(255.0, bf * 1.20 + 25.0)
                    bold = True
            elif flash_phase > 0.01:
                f = flash_phase ** 0.6
                rf = rf + (255.0 - rf) * f * 0.55
                gf = gf + (235.0 - gf) * f * 0.55
                bf = bf + (245.0 - bf) * f * 0.55

            row_cells.append((ch, clamp8(rf, 6), clamp8(gf, 6), clamp8(bf, 6), bold))

        # ANSI Run-Length Segment Batching (GitHub Copilot CLI technique)
        out_parts: list[str] = []
        cur_style: tuple[int, int, int, bool] | None = None
        for ch, cr, cg, cb, cbold in row_cells:
            if ch == " ":
                if cur_style is not None:
                    out_parts.append(RESET)
                    cur_style = None
                out_parts.append(" ")
            else:
                style = (cr, cg, cb, cbold)
                if style != cur_style:
                    prefix = "\x1b[1;38;2;" if cbold else "\x1b[38;2;"
                    out_parts.append(f"{prefix}{cr};{cg};{cb}m")
                    cur_style = style
                out_parts.append(ch)
        if cur_style is not None:
            out_parts.append(RESET)
        lines.append("".join(out_parts))

    return lines


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def clamp_ansi_line(line: str, max_visible_cols: int) -> str:
    """Truncate a line containing ANSI codes so its visible width <= max_visible_cols."""
    if max_visible_cols <= 0:
        return ""
    out = []
    vis = 0
    pos = 0
    for m in ANSI_ESCAPE_RE.finditer(line):
        start, end = m.span()
        segment = line[pos:start]
        for ch in segment:
            if vis >= max_visible_cols:
                return "".join(out) + RESET
            out.append(ch)
            vis += 1
        out.append(m.group(0))
        pos = end
    for ch in line[pos:]:
        if vis >= max_visible_cols:
            return "".join(out) + RESET
        out.append(ch)
        vis += 1
    return "".join(out)


def get_fastfetch_lines() -> list[str]:
    raw = os.environ.get("FASTFETCH_INFO")
    if not raw:
        try:
            raw = subprocess.check_output(
                ["fastfetch", "--logo-type", "none", "--pipe", "false"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            raw = ""
    lines = [l.rstrip("\r") for l in raw.splitlines()]
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def combine_frame(scene_lines: list[str], info_lines: list[str], term_cols: int) -> list[str]:
    total_rows = max(len(scene_lines), len(info_lines))
    blank_left = " " * W
    combined = []
    for r in range(total_rows):
        left = scene_lines[r] if r < len(scene_lines) else blank_left
        right = info_lines[r] if r < len(info_lines) else ""
        if right:
            line = f"{left}{GAP}{right}{RESET}"
        else:
            line = f"{left}{RESET}"
        combined.append(clamp_ansi_line(line, term_cols - 1))
    return combined


def resolve_animation_mode() -> str:
    """Resolve animation policy (quality | performance | potato) like gentle-shell."""
    for arg in sys.argv[1:]:
        if arg.startswith("--mode="):
            val = arg.split("=", 1)[1].strip().lower()
            if val in ("quality", "performance", "potato"):
                return val
    env_mode = os.environ.get("FASTFETCH_ANIM_MODE", "quality").strip().lower()
    return env_mode if env_mode in ("quality", "performance", "potato") else "quality"


def main() -> None:
    if "--static-logo" in sys.argv:
        for line in render_scene_frame(0, is_final=True):
            print(line)
        return

    mode = resolve_animation_mode()
    info_lines = get_fastfetch_lines()

    if not sys.stdout.isatty() or mode == "potato":
        term_cols = shutil.get_terminal_size((120, 30)).columns
        final_lines = combine_frame(render_scene_frame(0, is_final=True), info_lines, term_cols)
        print("\n".join(final_lines))
        return

    fps = 30 if mode == "quality" else 10
    step_ticks = 1 if mode == "quality" else 3
    duration_sec = 4.0
    total_steps = int(fps * duration_sec)

    interrupted = False

    def handle_sigint(signum, frame):
        nonlocal interrupted
        interrupted = True

    old_sigint = signal.signal(signal.SIGINT, handle_sigint)

    stdin_fd = None
    old_termios = None
    if sys.stdin.isatty():
        try:
            stdin_fd = sys.stdin.fileno()
            old_termios = termios.tcgetattr(stdin_fd)
            tty.setcbreak(stdin_fd)
        except Exception:
            stdin_fd = None
            old_termios = None

    total_rows = max(H, len(info_lines))
    sys.stdout.write("\x1b[?25l\x1b[?7l")
    sys.stdout.flush()

    try:
        for s in range(total_steps):
            if interrupted:
                break
            t0 = time.monotonic()
            logical_frame = s * step_ticks
            term_cols = shutil.get_terminal_size((120, 30)).columns
            scene = render_scene_frame(logical_frame, is_final=False)
            frame_lines = combine_frame(scene, info_lines, term_cols)

            buf = []
            if s > 0:
                buf.append(f"\x1b[{total_rows}A\r")
            for line in frame_lines:
                buf.append(f"\x1b[2K{line}\n")

            sys.stdout.write("\x1b[?2026h" + "".join(buf) + "\x1b[?2026l")
            sys.stdout.flush()

            elapsed = time.monotonic() - t0
            wait = max(0.0, (1.0 / fps) - elapsed)
            if stdin_fd is not None:
                rlist, _, _ = select.select([stdin_fd], [], [], wait)
                if rlist:
                    try:
                        os.read(stdin_fd, 32)
                    except Exception:
                        pass
                    break
            else:
                time.sleep(wait)

        term_cols = shutil.get_terminal_size((120, 30)).columns
        final_scene = render_scene_frame(0, is_final=True)
        final_lines = combine_frame(final_scene, info_lines, term_cols)
        buf = [f"\x1b[{total_rows}A\r"]
        for line in final_lines:
            buf.append(f"\x1b[2K{line}\n")
        sys.stdout.write("\x1b[?2026h" + "".join(buf) + "\x1b[?2026l")
        sys.stdout.flush()

    finally:
        if stdin_fd is not None and old_termios is not None:
            try:
                termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_termios)
            except Exception:
                pass
        signal.signal(signal.SIGINT, old_sigint)
        sys.stdout.write("\x1b[?7h\x1b[?25h")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
