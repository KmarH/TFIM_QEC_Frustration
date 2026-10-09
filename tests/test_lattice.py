"""Lattice indexing and bond enumeration tests."""

from src.lattice import coord, site_index, square_bonds


def test_index_roundtrip():
    Lx = 4
    for y in range(3):
        for x in range(Lx):
            n = site_index(x, y, Lx)
            assert coord(n, Lx) == (x, y)


def test_square_bond_count_open():
    # Lx x Ly open square lattice has Lx*(Ly) + Ly*(Lx) interior-edge count:
    # horizontal bonds = (Lx-1)*Ly, vertical bonds = Lx*(Ly-1).
    Lx, Ly = 3, 3
    bonds = square_bonds(Lx, Ly, "open")
    expected = (Lx - 1) * Ly + Lx * (Ly - 1)
    assert len(bonds) == expected
    # all ordered i<j, unique
    assert all(i < j for (i, j) in bonds)
    assert len(set(bonds)) == len(bonds)


def test_square_bond_count_periodic():
    # Periodic (torus) with Lx,Ly > 2: 2 bonds per site, total = 2*N.
    Lx, Ly = 4, 4
    bonds = square_bonds(Lx, Ly, "periodic")
    assert len(bonds) == 2 * Lx * Ly
    assert len(set(bonds)) == len(bonds)


def test_periodic_skips_degenerate_wrap_when_dim_two():
    # With Lx == 2, the wrap bond coincides with the interior bond; must not
    # be double-counted. Row of 2 sites, Ly=1: only 1 horizontal bond total.
    bonds = square_bonds(2, 1, "periodic")
    assert bonds == [(0, 1)]
