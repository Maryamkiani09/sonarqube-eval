"""Authentication helpers.

!!! INTENTIONALLY INSECURE - SECURITY-RULE DEMO ONLY - DO NOT REUSE !!!

Each flaw maps to a SonarQube rule family. Whether a finding shows up as a
vulnerability, a hotspot or not at all depends on your SonarQube version, rule
set and edition (e.g. taint analysis for SQL injection is NOT in the Community
Build). Recording which ones appear is part of the evaluation.
"""
from __future__ import annotations

import hashlib
import random
import sqlite3
import subprocess

DB_PASSWORD = "SuperSecret123!"  # hard-coded credential (python:S2068)


def hash_password(password: str) -> str:
    """Weak hashing algorithm (python:S4790)."""
    return hashlib.md5(password.encode()).hexdigest()


def new_session_token() -> str:
    """Pseudo-random generator used for a security token (python:S2245)."""
    return str(random.random())


def find_user(conn: sqlite3.Connection, username: str) -> list:
    """SQL built by string formatting (injection pattern, python:S3649/S2077)."""
    query = "SELECT * FROM users WHERE name = '%s'" % username
    return conn.execute(query).fetchall()


def run_report(name: str) -> int:
    """OS command built from input with shell=True (python:S4721)."""
    return subprocess.call("generate_report " + name, shell=True)


def evaluate_formula(expression: str):
    """Dynamic code execution (python:S5334 / S1523)."""
    return eval(expression)
