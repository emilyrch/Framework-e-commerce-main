"""Fábrica exclusiva de testes; o runtime normal não aceita relógio por ambiente."""
import os
from datetime import datetime

from foundation.application import create_app as application


def create_app():
    fixed = datetime.fromisoformat(os.environ['TEST_CLOCK'])
    return application('orders', clock=lambda: fixed)
