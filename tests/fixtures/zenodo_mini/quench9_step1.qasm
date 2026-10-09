// SYNTHETIC 3x3-torus circuit in the dataset's gate vocabulary (for read_qasm tests)
OPENQASM 2.0;
include "qelib1.inc";
qreg q[9];
creg c[9];
ry(pi/6) q[0];
ry(-0.17453292519943295) q[1];
rx(0.5) q[0];
rzz(0.5) q[0],q[1];
rzz(0.5) q[1],q[2];
rzz(0.5) q[2],q[0];
rzz(0.5) q[0],q[3];
rx(0.5) q[0];
measure q[0] -> c[0];
