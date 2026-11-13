# Estimacion del movimiento global de camara (paneo, inclinacion y zoom) entre dos fotogramas.
# Se usa flujo optico disperso (Lucas-Kanade) sobre una version reducida en grises y una
# transformacion de similitud robusta (RANSAC), de modo que vehiculos y peatones en movimiento
# no arrastren la estimacion. Sirve para mover las cajas de los semaforos junto con la camara.
from typing import NamedTuple, Optional

import cv2
import numpy as np

SMALL_WIDTH = 640
MIN_POINTS = 12
# Diferencia media de grises (0-255) a partir de la cual, si el flujo falla, se considera un corte
# de escena (p. ej. un video de prueba que vuelve a empezar con la camara en otra posicion).
CUT_MEAN_DIFF = 22.0

_LK_PARAMS = dict(
    winSize=(21, 21),
    maxLevel=4,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
)


class SmallGray(NamedTuple):
    gray: np.ndarray
    scale: float  # factor reducido / original


class MotionResult(NamedTuple):
    matrix: Optional[np.ndarray]  # afin 2x3 (similitud) en pixeles originales: origen -> destino
    cut: bool  # la escena cambio por completo: las posiciones anteriores ya no sirven


def to_small_gray(frame: np.ndarray, width: int = SMALL_WIDTH) -> SmallGray:
    h, w = frame.shape[:2]
    scale = min(1.0, width / float(w))
    small = cv2.resize(frame, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA) if scale < 1.0 else frame
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) if small.ndim == 3 else small
    return SmallGray(gray, scale)


def _mean_diff(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape != b.shape:
        return 255.0
    return float(np.mean(cv2.absdiff(a, b)))


def estimate_motion(src: SmallGray, dst: SmallGray) -> MotionResult:
    """Transformacion de similitud que lleva puntos de `src` a `dst`, o None si no es confiable."""
    if src.gray.shape != dst.gray.shape:
        return MotionResult(None, True)

    pts = cv2.goodFeaturesToTrack(src.gray, maxCorners=400, qualityLevel=0.01, minDistance=7, blockSize=7)
    if pts is None or len(pts) < MIN_POINTS:
        return MotionResult(None, _mean_diff(src.gray, dst.gray) > CUT_MEAN_DIFF)

    nxt, st, _ = cv2.calcOpticalFlowPyrLK(src.gray, dst.gray, pts, None, **_LK_PARAMS)
    if nxt is None:
        return MotionResult(None, _mean_diff(src.gray, dst.gray) > CUT_MEAN_DIFF)
    back, st2, _ = cv2.calcOpticalFlowPyrLK(dst.gray, src.gray, nxt, None, **_LK_PARAMS)
    fb_err = np.linalg.norm((pts - back).reshape(-1, 2), axis=1)
    good = (st.reshape(-1) == 1) & (st2.reshape(-1) == 1) & (fb_err < 1.5)
    if int(good.sum()) < MIN_POINTS:
        return MotionResult(None, _mean_diff(src.gray, dst.gray) > CUT_MEAN_DIFF)

    p0 = pts.reshape(-1, 2)[good]
    p1 = nxt.reshape(-1, 2)[good]
    matrix, inliers = cv2.estimateAffinePartial2D(
        p0, p1, method=cv2.RANSAC, ransacReprojThreshold=2.0, maxIters=600, confidence=0.98
    )
    if matrix is None or inliers is None:
        return MotionResult(None, _mean_diff(src.gray, dst.gray) > CUT_MEAN_DIFF)
    n_in = int(inliers.sum())
    if n_in < max(10, int(0.30 * len(p0))):
        return MotionResult(None, _mean_diff(src.gray, dst.gray) > CUT_MEAN_DIFF)

    zoom = float(np.sqrt(abs(np.linalg.det(matrix[:, :2]))))
    if not 0.80 <= zoom <= 1.25:
        return MotionResult(None, False)

    full = matrix.astype(np.float64).copy()
    full[:, 2] /= src.scale
    return MotionResult(full, False)


def motion_zoom(matrix: np.ndarray) -> float:
    return float(np.sqrt(abs(np.linalg.det(matrix[:, :2]))))


def apply_motion_to_box(
    box: tuple[float, float, float, float],
    matrix: Optional[np.ndarray],
    frame_shape: Optional[tuple[int, int]] = None,
) -> tuple[float, float, float, float]:
    """Mueve el centro de la caja con la transformacion y escala su tamano con el zoom de camara."""
    if matrix is None:
        return box
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) * 0.5, (y1 + y2) * 0.5
    w, h = x2 - x1, y2 - y1
    ncx = matrix[0, 0] * cx + matrix[0, 1] * cy + matrix[0, 2]
    ncy = matrix[1, 0] * cx + matrix[1, 1] * cy + matrix[1, 2]
    zoom = motion_zoom(matrix)
    nw, nh = w * zoom, h * zoom
    nx1, ny1, nx2, ny2 = ncx - nw * 0.5, ncy - nh * 0.5, ncx + nw * 0.5, ncy + nh * 0.5
    if frame_shape is not None:
        fh, fw = frame_shape
        nx1 = max(-nw * 0.5, min(float(fw) - 2.0, nx1))
        ny1 = max(-nh * 0.5, min(float(fh) - 2.0, ny1))
        nx2 = nx1 + nw
        ny2 = ny1 + nh
    return (float(nx1), float(ny1), float(nx2), float(ny2))
