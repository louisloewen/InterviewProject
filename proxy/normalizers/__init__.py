"""Normalizers (Seam 3).

Pure, HTTP-free functions mapping each provider's raw record to the canonical
Employee model. Kept separate from the clients so they're testable with raw
fixtures alone (no mock transport).
"""
