"""Entrada de teste: clock fixo e escolha de worker só na fábrica de teste."""
import os
from datetime import datetime

from foundation.application import create_app as application


def create_app():
    fixed = datetime.fromisoformat(os.environ['TEST_CLOCK'])
    return application('orders', clock=lambda: fixed, start_worker=os.environ.get('TEST_WORKER') == '1')
