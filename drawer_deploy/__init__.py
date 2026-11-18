"""Run a trained policy (or the scripted fallback) on a robot backend.

The same loop drives the MuJoCo "rehearsal" backend and the real Kinova Gen3 Lite, so
everything except the last hop to the hardware is exercised in simulation first.
"""
