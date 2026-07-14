"""Outbound notifications (Phase 41) — the retention loop.

A research tool people visit once is a demo. A weekly email that tells them what
changed in the companies they watch is a product. Guarded end to end: with no
``RESEND_API_KEY`` every send is a logged no-op, so nothing breaks and no mail
escapes in development.
"""
