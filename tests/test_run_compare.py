"""scripts/run_compare.py (review R-Main-10): `is_synthetic`, the `trusted` gate that protects
data/, and `verify_circuits` with signed (gauge-aware) angle checks (review R-Main-4).

The fixture's QASM sits at tests/fixtures/zenodo_mini/quench9_step1.qasm, not under
circuits/, so these tests build the dataset layout <root>/circuits/quenchN_step1.qasm in
tmp_path. data/ is redirected to tmp_path; nothing here writes the repo's data/.
"""

import importlib.util
import os
import shutil

import numpy as np
import pytest

from config import CONFIG
from src.lattice import square_bonds

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures", "zenodo_mini")

_spec = importlib.util.spec_from_file_location("run_compare", os.path.join(ROOT, "scripts", "run_compare.py"))
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

C = CONFIG.compare
RZZ, RX = 2 * C.J * C.dt, C.h * C.dt          # 0.5, 0.5: the released circuits' magnitudes


def _qasm(theta, s_rzz=1, s_rx=1, s_ry=1, bonds=None, rzz_signs=None, rx2_sign=None):
    """Step-1 circuit in the dataset's vocabulary on the 7x8 row-major torus.
    Signs multiply the released pattern rzz(+0.5), rx(+0.5), ry(+theta)."""
    n = C.data_Lx * C.data_Ly
    bonds = square_bonds(C.data_Lx, C.data_Ly, C.boundary) if bonds is None else bonds
    rzz_signs = [s_rzz] * len(bonds) if rzz_signs is None else rzz_signs
    rx2 = s_rx if rx2_sign is None else rx2_sign
    lines = ["OPENQASM 2.0;", 'include "qelib1.inc";', f"qreg q[{n}];", f"creg c[{n}];"]
    lines += [f"ry({s_ry * theta!r}) q[{q}];" for q in range(n)]
    lines += [f"rx({s_rx * RX!r}) q[{q}];" for q in range(n)]
    lines += [f"rzz({s * RZZ!r}) q[{a}],q[{b}];" for (a, b), s in zip(bonds, rzz_signs)]
    lines += [f"rx({rx2 * RX!r}) q[{q}];" for q in range(n)]
    lines += [f"measure q[{q}] -> c[{q}];" for q in range(n)]
    return "\n".join(lines) + "\n"


def _layout(tmp_path, readme="dataset README (stand-in)\n", circuits=None, name="zd"):
    """Copy the fixture's value files into a dataset-shaped dir with circuits/."""
    d = tmp_path / name
    shutil.copytree(FIX, d)
    os.remove(d / "README.md")
    if readme is not None:
        (d / "README.md").write_text(readme, encoding="utf-8")
    if circuits:
        (d / "circuits").mkdir()
        for q, text in circuits.items():
            (d / "circuits" / f"quench{q}_step1.qasm").write_text(text, encoding="utf-8")
    return d


def _good_circuits(**kw):
    return {q: _qasm(C.theta[q], **kw) for q in C.quenches}


class _Log(list):
    def __call__(self, s=""):
        self.append(s)


# ---------------------------------------------------------------- is_synthetic / gate
def test_is_synthetic(tmp_path):
    assert rc.is_synthetic(FIX)
    assert not rc.is_synthetic(str(tmp_path))                       # no README at all
    (tmp_path / "README.md").write_text("Zenodo record 18487089\n", encoding="utf-8")
    assert not rc.is_synthetic(str(tmp_path))


def test_source_status(tmp_path):
    assert rc.source_status(FIX) == (True, False)
    assert rc.source_status(str(_layout(tmp_path, name="ok"))) == (False, True)
    assert rc.source_status(str(_layout(tmp_path, readme=None, name="noreadme"))) == (False, False)
    # a copy that keeps the SYNTHETIC marker stays synthetic outside tests/fixtures
    with open(os.path.join(FIX, "README.md"), encoding="utf-8") as fh:
        marked = fh.read()
    assert rc.source_status(str(_layout(tmp_path, readme=marked, name="marked"))) == (True, False)


@pytest.fixture
def small_run(monkeypatch, tmp_path):
    """Cheap sizes and a tmp data/ so main() can run end to end on fixture values."""
    monkeypatch.setattr(C, "sizes", ((2, 2), (2, 3)))
    out = tmp_path / "data_out"
    monkeypatch.setattr(CONFIG, "data_dir", str(out))    # absolute: os.path.join(REPO, abs) == abs
    return out / "q1_compare.txt"


def test_trusted_gate_refuses_synthetic_fixture(small_run, capsys):
    assert rc.main(["--data", FIX]) is False
    assert not small_run.exists()
    out = capsys.readouterr()
    assert "NOT written to data/" in out.err
    assert all(l.startswith("[SYNTHETIC FIXTURE] ") for l in out.out.splitlines() if l)


def test_trusted_gate_refuses_synthetic_even_with_valid_circuits(small_run, tmp_path):
    with open(os.path.join(FIX, "README.md"), encoding="utf-8") as fh:
        marked = fh.read()
    d = _layout(tmp_path, readme=marked, circuits=_good_circuits())
    assert rc.main(["--data", str(d)]) is False
    assert not small_run.exists()


@pytest.mark.parametrize("readme,circuits", [
    (None, "good"),          # no dataset README
    ("README\n", None),      # circuits missing -> unverified
    ("README\n", "q1only"),  # one quench unverified
])
def test_trusted_gate_needs_readme_and_every_circuit(small_run, tmp_path, readme, circuits):
    circ = {"good": _good_circuits(), None: None,
            "q1only": {1: _qasm(C.theta[1])}}[circuits]
    d = _layout(tmp_path, readme=readme, circuits=circ)
    assert rc.main(["--data", str(d)]) is False
    assert not small_run.exists()


def test_trusted_gate_opens_only_for_verified_source(small_run, tmp_path):
    d = _layout(tmp_path, circuits=_good_circuits())
    assert rc.main(["--data", str(d)]) is True
    text = small_run.read_text(encoding="utf-8")
    assert not any(l.startswith("[") for l in text.splitlines())    # no SYNTHETIC/UNVERIFIED tag
    assert text.count("signs: literal circuit is (-J,-h,theta)") == len(C.quenches)
    assert "estimator/shots — zne+znr: estimator=zne+znr, shots=not stated" in text


def test_non_gauge_circuit_aborts_and_writes_nothing(small_run, tmp_path):
    d = _layout(tmp_path, circuits=_good_circuits(s_rx=-1))
    with pytest.raises(SystemExit, match="NOT gauge-equivalent"):
        rc.main(["--data", str(d)])
    assert not small_run.exists()


# ---------------------------------------------------------------- verify_circuits
@pytest.mark.parametrize("q", [1, 2])
@pytest.mark.parametrize("signs,label", [
    ((+1, +1, +1), "(-J,-h,theta)"),    # the released data: rzz(+0.5), rx(+0.5), ry(+theta)
    ((-1, -1, +1), "(J,h,theta)"),
    ((+1, -1, -1), "(-J,h,-theta)"),
    ((-1, +1, -1), "(J,-h,-theta)"),
])
def test_verify_accepts_each_gauge_pattern(tmp_path, q, signs, label):
    s_rzz, s_rx, s_ry = signs
    d = _layout(tmp_path, circuits={q: _qasm(C.theta[q], s_rzz, s_rx, s_ry)})
    log = _Log()
    assert rc.verify_circuits(str(d), q, C.theta[q], log) is True
    assert any(f"literal circuit is {label}" in l for l in log)
    assert any("signed angles" in l and f"rzz [{s_rzz * RZZ}]" in l for l in log)   # signs logged


@pytest.mark.parametrize("signs", [(+1, -1, +1), (-1, +1, +1), (+1, +1, -1), (-1, -1, -1)])
def test_verify_rejects_non_gauge_patterns(tmp_path, signs):
    d = _layout(tmp_path, circuits={1: _qasm(C.theta[1], *signs)})
    with pytest.raises(SystemExit, match="NOT gauge-equivalent"):
        rc.verify_circuits(str(d), 1, C.theta[1], _Log())


def test_verify_rejects_bond_non_uniform_rzz_signs(tmp_path):
    bonds = square_bonds(C.data_Lx, C.data_Ly, C.boundary)
    signs = [1] * len(bonds)
    signs[17] = -1                                       # one bond flipped: not a gauge
    d = _layout(tmp_path, circuits={1: _qasm(C.theta[1], rzz_signs=signs)})
    with pytest.raises(SystemExit, match="rzz: mixed signs"):
        rc.verify_circuits(str(d), 1, C.theta[1], _Log())


def test_verify_rejects_rx_half_layers_of_opposite_sign(tmp_path):
    d = _layout(tmp_path, circuits={1: _qasm(C.theta[1], rx2_sign=-1)})
    with pytest.raises(SystemExit, match="rx: mixed signs"):
        rc.verify_circuits(str(d), 1, C.theta[1], _Log())


def test_verify_rejects_wrong_magnitude(tmp_path):
    d = _layout(tmp_path, circuits={2: _qasm(C.theta[1])})   # quench1 theta in the quench2 slot
    with pytest.raises(SystemExit, match="ry"):
        rc.verify_circuits(str(d), 2, C.theta[2], _Log())


def test_verify_accepts_merged_interior_rx(tmp_path):
    text = _qasm(C.theta[1]).replace(f"rx({RX!r})", f"rx({2 * RX!r})", C.data_Lx * C.data_Ly)
    d = _layout(tmp_path, circuits={1: text})
    assert rc.verify_circuits(str(d), 1, C.theta[1], _Log()) is True


def test_verify_bond_mismatch_is_not_trusted(tmp_path):
    open_bonds = square_bonds(C.data_Lx, C.data_Ly, "open")
    d = _layout(tmp_path, circuits={1: _qasm(C.theta[1], bonds=open_bonds)})
    log = _Log()
    assert rc.verify_circuits(str(d), 1, C.theta[1], log) is False
    assert any("matches neither index map" in l for l in log)


def test_verify_missing_circuits_is_unverified():
    log = _Log()
    assert rc.verify_circuits(FIX, 1, C.theta[1], log) is False      # fixture has no circuits/
    assert "[unverified]" in log[0]


def test_verify_runs_on_the_fixture_qasm_and_rejects_it(tmp_path):
    """The fixture circuit (3x3 vocabulary sample, ry(pi/6) and ry(-10 deg) mixed) must not pass."""
    d = _layout(tmp_path)
    (d / "circuits").mkdir()
    shutil.copy(os.path.join(FIX, "quench9_step1.qasm"), d / "circuits" / "quench9_step1.qasm")
    with pytest.raises(SystemExit, match="ry: "):
        rc.verify_circuits(str(d), 9, np.pi / 6, _Log())
