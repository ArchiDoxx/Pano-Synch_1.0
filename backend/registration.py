"""
Transformation between two panoramas.

Affine (6 parameters) — global fit, used for RMSE display and initial transform.
Thin-Plate Spline (TPS)  — local interpolation, used for navigation.
  TPS passes exactly through every reference pair and smoothly interpolates
  between them, handling per-strip stitching offsets that affine cannot model.
"""

import numpy as np
from typing import List, Tuple


# ── Affine ────────────────────────────────────────────────────────────────────

def compute_transform(pairs: List[dict],
                      img_size_a: tuple = None,
                      img_size_b: tuple = None) -> dict:
    if len(pairs) < 3:
        raise ValueError("At least 3 point pairs required for affine transform")

    ax = np.array([p["ax"] for p in pairs], dtype=float)
    ay = np.array([p["ay"] for p in pairs], dtype=float)
    bx = np.array([p["bx"] for p in pairs], dtype=float)
    by = np.array([p["by"] for p in pairs], dtype=float)

    A = np.column_stack([ax, ay, np.ones_like(ax)])

    params_x, _, _, _ = np.linalg.lstsq(A, bx, rcond=None)
    a, b, tx = float(params_x[0]), float(params_x[1]), float(params_x[2])

    params_y, _, _, _ = np.linalg.lstsq(A, by, rcond=None)
    c, d, ty = float(params_y[0]), float(params_y[1]), float(params_y[2])

    bx_pred = a * ax + b * ay + tx
    by_pred = c * ax + d * ay + ty
    errors = np.sqrt((bx - bx_pred) ** 2 + (by - by_pred) ** 2)
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    M = np.array([[a, b, tx], [c, d, ty], [0, 0, 1]], dtype=float)
    try:
        M_inv = np.linalg.inv(M)
        inv_a  = float(M_inv[0,0]); inv_b  = float(M_inv[0,1]); inv_tx = float(M_inv[0,2])
        inv_c  = float(M_inv[1,0]); inv_d  = float(M_inv[1,1]); inv_ty = float(M_inv[1,2])
    except np.linalg.LinAlgError:
        inv_a=1.; inv_b=0.; inv_tx=0.; inv_c=0.; inv_d=1.; inv_ty=0.

    residuals = [float(e) for e in errors]

    # TPS: augment user pairs with virtual corner anchors derived from the
    # calibrated affine. Corners are computed exactly → TPS is constrained at
    # the image borders and interpolates accurately between user pairs.
    tps_ax, tps_ay, tps_bx, tps_by = ax.copy(), ay.copy(), bx.copy(), by.copy()
    if img_size_a and None not in img_size_a:
        w_a, h_a = float(img_size_a[0]), float(img_size_a[1])
        # Dense regular grid over full Pano A extent.
        # Grid density: ~every 1500 px in X, ~every 600 px in Y.
        # Covers every scan strip with at least one anchor on each axis.
        nx = max(10, int(round(w_a / 1500)))
        ny = max(4,  int(round(h_a / 600)))
        gx, gy = np.meshgrid(np.linspace(0, w_a, nx), np.linspace(0, h_a, ny))
        c_ax = gx.ravel()
        c_ay = gy.ravel()
        c_bx = a * c_ax + b * c_ay + tx
        c_by = c * c_ax + d * c_ay + ty
        tps_ax = np.concatenate([tps_ax, c_ax])
        tps_ay = np.concatenate([tps_ay, c_ay])
        tps_bx = np.concatenate([tps_bx, c_bx])
        tps_by = np.concatenate([tps_by, c_by])

    tps = _compute_tps(tps_ax, tps_ay, tps_bx, tps_by) if len(pairs) >= 3 else None

    return dict(a=a, b=b, tx=tx, c=c, d=d, ty=ty,
                inv_a=inv_a, inv_b=inv_b, inv_tx=inv_tx,
                inv_c=inv_c, inv_d=inv_d, inv_ty=inv_ty,
                rmse=rmse, residuals=residuals, tps=tps)


def initial_transform(w_a: int, h_a: int, w_b: int, h_b: int) -> dict:
    sx = w_b / w_a
    sy = h_b / h_a
    return dict(a=sx, b=0., tx=0., c=0., d=sy, ty=0.,
                inv_a=1/sx, inv_b=0., inv_tx=0.,
                inv_c=0., inv_d=1/sy, inv_ty=0.,
                rmse=None, tps=None)


def transform_a_to_b(x: float, y: float, t: dict) -> Tuple[float, float]:
    return t["a"]*x + t["b"]*y + t["tx"], t["c"]*x + t["d"]*y + t["ty"]


def transform_b_to_a(x: float, y: float, t: dict) -> Tuple[float, float]:
    return t["inv_a"]*x + t["inv_b"]*y + t["inv_tx"], t["inv_c"]*x + t["inv_d"]*y + t["inv_ty"]


# ── Thin-Plate Spline ─────────────────────────────────────────────────────────

def _tps_kernel(r2: np.ndarray) -> np.ndarray:
    """TPS radial basis function: U(r) = r² log(r²), U(0) = 0."""
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(r2 < 1e-12, 0.0, r2 * np.log(np.maximum(r2, 1e-12)))


def _fit_tps_axis(sx: np.ndarray, sy: np.ndarray, vals: np.ndarray):
    """
    Fit a 1-D TPS: predict `vals` from source coords (sx, sy).
    Returns (weights w[N], affine a[3]) where a = [a0, a1, a2].
    """
    n = len(sx)
    dx = sx[:, None] - sx[None, :]
    dy = sy[:, None] - sy[None, :]
    K = _tps_kernel(dx**2 + dy**2)

    P = np.column_stack([np.ones(n), sx, sy])   # N × 3

    M = np.zeros((n + 3, n + 3))
    M[:n, :n] = K
    M[:n, n:] = P
    M[n:, :n] = P.T

    rhs = np.zeros(n + 3)
    rhs[:n] = vals

    try:
        c = np.linalg.solve(M, rhs)
    except np.linalg.LinAlgError:
        c, _, _, _ = np.linalg.lstsq(M, rhs, rcond=None)

    return c[:n].tolist(), c[n:].tolist()


def _compute_tps(ax, ay, bx, by) -> dict:
    """
    Compute forward (A→B) and inverse (B→A) TPS from matched coordinates.
    Returns a dict of precomputed weights ready for JS evaluation.
    """
    wx,  ax_c  = _fit_tps_axis(ax, ay, bx)
    wy,  ay_c  = _fit_tps_axis(ax, ay, by)
    iwx, iax_c = _fit_tps_axis(bx, by, ax)
    iwy, iay_c = _fit_tps_axis(bx, by, ay)

    return dict(
        # Forward control points (A image coords)
        fwd_cx=ax.tolist(), fwd_cy=ay.tolist(),
        fwd_wx=wx,  fwd_ax=ax_c,   # → x_B
        fwd_wy=wy,  fwd_ay=ay_c,   # → y_B
        # Inverse control points (B image coords)
        inv_cx=bx.tolist(), inv_cy=by.tolist(),
        inv_wx=iwx, inv_ax=iax_c,  # → x_A
        inv_wy=iwy, inv_ay=iay_c,  # → y_A
    )
