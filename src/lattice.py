"""Lattice geometry: site indexing and nearest-neighbour bond enumeration.

Convention (research/01-stage1-conventions.md): row-major site index
    n = y * Lx + x,   0 <= x < Lx,   0 <= y < Ly.
Square geometry (Stage 1) and triangular geometry (Stage 3, the frustrated main
focus) are both provided; the TFIM operator/Trotter/observable code is
geometry-agnostic and consumes whichever bond list it is given.
"""

from __future__ import annotations

from typing import List, Tuple


def site_index(x: int, y: int, Lx: int) -> int:
    """Row-major flat index for grid coordinate (x, y)."""
    return y * Lx + x


def coord(n: int, Lx: int) -> Tuple[int, int]:
    """Inverse of site_index: flat index -> (x, y)."""
    return (n % Lx, n // Lx)


def square_bonds(
    Lx: int, Ly: int, boundary: str = "open"
) -> List[Tuple[int, int]]:
    """Nearest-neighbour bonds of an Lx x Ly square lattice.

    Each bond is an ordered pair (i, j) with i < j, listed once. For periodic
    boundaries the wrap bonds are added per direction; the degenerate wrap when
    Lx == 2 (or Ly == 2) is skipped so a bond is never double-counted.

    Why the skip matters physically: at length 2 the forward neighbour and the
    wrap-around neighbour are the same pair, so adding both would put a coupling
    of 2J on that edge and silently change the Hamiltonian. Each unordered pair
    must appear exactly once; the invariant is len(bonds) == 2N for a fully
    periodic lattice with every side > 2.
    """
    if boundary not in ("open", "periodic"):
        raise ValueError(f"unknown boundary: {boundary!r}")

    bonds: List[Tuple[int, int]] = []
    periodic = boundary == "periodic"

    for y in range(Ly):
        for x in range(Lx):
            n = site_index(x, y, Lx)

            # Horizontal (+x) neighbour
            if x + 1 < Lx:
                bonds.append((n, site_index(x + 1, y, Lx)))
            elif periodic and Lx > 2:
                bonds.append(_ordered(n, site_index(0, y, Lx)))

            # Vertical (+y) neighbour
            if y + 1 < Ly:
                bonds.append((n, site_index(x, y + 1, Lx)))
            elif periodic and Ly > 2:
                bonds.append(_ordered(n, site_index(x, 0, Lx)))

    return bonds


def _ordered(i: int, j: int) -> Tuple[int, int]:
    return (i, j) if i < j else (j, i)


def triangular_bonds(
    Lx: int, Ly: int, boundary: str = "periodic"
) -> List[Tuple[int, int]]:
    """Nearest-neighbour bonds of an Lx x Ly triangular lattice (Stage 3).

    Realized as a square grid plus one diagonal: each site (x, y) connects along
    three primitive directions
        d1 = (+1, 0),  d2 = (0, +1),  d3 = (+1, +1),
    giving interior coordination number 6 (±d1, ±d2, ±d3). The diagonal d3 is
    what distinguishes this from the square lattice: it closes the three sites
    {(x,y), (x+1,y), (x+1,y+1)} into an elementary triangle, so an
    antiferromagnetic coupling cannot be satisfied on all three edges at once —
    this is the geometric frustration that is the point of Stage 3
    (research/03-stage3-triangular.md). The default boundary is "periodic" to
    match the reproduction target (arXiv:2503.20870, triangular lattice with
    periodic BC).

    Each undirected edge is returned exactly once as an ordered pair (i, j), i<j.
    De-duplication uses a set because on small or periodic lattices several of the
    three directions (and their wraps) can land on the same pair — e.g. Lx or Ly
    small, or a site joined to the same neighbour by two different primitive
    directions. The set guarantees no edge is double-counted, which would
    otherwise put a spurious extra J on that bond. Self-loops (a site mapping to
    itself under a wrap, possible when Lx or Ly == 1) are dropped.

    Invariant: for a fully periodic lattice with Lx, Ly >= 3, every site has
    exactly 6 neighbours and len(bonds) == 3N (N = Lx*Ly). The 3N count follows
    from enumerating only the three forward directions once per site: each
    undirected edge is generated from exactly one of its endpoints, so the six
    neighbours per site collapse to three edges per site.
    """
    if boundary not in ("open", "periodic"):
        raise ValueError(f"unknown boundary: {boundary!r}")
    periodic = boundary == "periodic"
    directions = ((1, 0), (0, 1), (1, 1))

    edges = set()
    for y in range(Ly):
        for x in range(Lx):
            n = site_index(x, y, Lx)
            for (dx, dy) in directions:
                nx, ny = x + dx, y + dy
                if periodic:
                    nx %= Lx
                    ny %= Ly
                elif nx >= Lx or ny >= Ly:
                    continue
                m = site_index(nx, ny, Lx)
                if m != n:
                    edges.add(_ordered(n, m))

    return sorted(edges)

