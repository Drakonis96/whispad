import pytest
from backend import OPENROUTER_FREE_MODELS, OPENROUTER_PAID_MODELS

def test_paid_models_include_free_variants():
    for free_model in OPENROUTER_FREE_MODELS:
        paid_variant = free_model.replace(':free', '')
        assert paid_variant in OPENROUTER_PAID_MODELS
