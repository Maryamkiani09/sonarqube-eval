"""Configuration - contains FAKE secrets so the secrets analyzer has work to do.

The AWS values below are Amazon's public documentation examples, not real
credentials. Never commit real secrets.
"""

AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

API_URL = "http://api.shopflow.example/v1"  # clear-text protocol (python:S5332)
VERIFY_TLS = False  # certificate validation disabled (python:S4830)
