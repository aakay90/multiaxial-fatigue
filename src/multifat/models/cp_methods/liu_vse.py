# multifat/models/cp_methods/liu_vse.py
"""Virtual strain energy (VSE) parameters after Liu (1993), ASTM STP 1191:67-84, doi:10.1520/STP24796S
(roadmap G15), Eqs. (7)-(11).

For a given plane, the Mohr stress ranges (Delta sigma_n, Delta tau) combined with the strain ranges
(Delta eps_n, Delta gamma/2) yield Delta W = Delta W_n + Delta W_s = Delta sigma_n Delta eps_n
+ Delta tau . Delta(gamma/2), i.e. the dot product 2(OA).2(O'A') shown in Fig. 4.
  Mode I (Eq. 8): the plane chosen is the one making the tensile contribution Delta W_n largest, and the
      damage there is Delta W_n + Delta W_s;
  Mode II (Eq. 9): the plane chosen is the one making the shear contribution Delta W_s largest (Type A),
      with damage Delta W_n + Delta W_s.
Taking the maximum of the total over all planes gives the ``_ext`` variant, which is Eq. (7) read
literally; Eq. (8) instead follows the paper's decomposition, and the two do not coincide in general.
A single registered model, VSE, uses mode I unless the parameter ``vse_mode = 2`` selects mode II.
Under uniaxial loading Delta W reduces to Delta sigma Delta eps (Eq. 11), while in torsion the two modes
coincide (p.73). The paper offers no criterion for picking the mode (it depends on material and
temperature) and instead fits the life curve, Eq. (6), to the data. Ranges here are endpoint differences
of the repository cycle, applying the longest-chord rule to harmonic shear (Liu's out-of-phase rules,
pp.80-81, are stated verbally only: this is a documented adaptation). Since the workbook strains are
elastic, the plastic term of Eq. (6) does not appear.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np
from multifat.models.utils.batch import check_planes

from ..base import CPPlaneResult


def _energy_parts(S0r, E0r, S1r, E1r):
    d_sigma_n = S0r[:, 2, 2] - S1r[:, 2, 2]
    d_eps_n = E0r[:, 2, 2] - E1r[:, 2, 2]
    dW_n = np.abs(d_sigma_n * d_eps_n)
    dW_s = np.abs(
        (S0r[:, 0, 2] - S1r[:, 0, 2]) * (E0r[:, 0, 2] - E1r[:, 0, 2])
        + (S0r[:, 1, 2] - S1r[:, 1, 2]) * (E0r[:, 1, 2] - E1r[:, 1, 2])
    )
    return dW_n, dW_s


class LiuVSE:
    """VSE critical-plane method; Eq. (8) (mode I) is used unless
    ``params['vse_mode'] = 2`` requests Eq. (9) (mode II)."""

    name = "VSE"
    optional_params = {"vse_mode": "1 (mode I, Eq. 8); 2 = mode II (Eq. 9)"}
    np_shear_rule = "longest_chord"

    def required_params(self) -> set[str]:
        return set()

    def evaluate_on_plane(self, *, S0r, E0r, S1r, E1r, params: Mapping[str, float]):
        damage, metric = self.evaluate_on_planes(
            S0r=np.asarray(S0r, float)[None],
            E0r=np.asarray(E0r, float)[None],
            S1r=np.asarray(S1r, float)[None],
            E1r=np.asarray(E1r, float)[None],
            params=params,
        )
        return CPPlaneResult(damage=float(damage[0]), metric=float(metric[0]))

    def evaluate_on_planes(
        self,
        *,
        S0r,
        E0r,
        S1r,
        E1r,
        params: Mapping[str, float],
        tau_max=None,
        strain_ranges=None,
    ):
        check_planes(S0r, E0r, S1r, E1r)
        mode = params.get("vse_mode", None)
        mode = 1 if mode is None else int(mode)
        if mode not in (1, 2):
            raise ValueError(f"VSE: vse_mode must be 1 or 2, got {mode}")
        dW_n, dW_s = _energy_parts(S0r, E0r, S1r, E1r)
        return dW_n + dW_s, (dW_n if mode == 1 else dW_s)
