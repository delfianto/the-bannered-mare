"""Tests for persistence utilities"""

from src.core.persistence import gen_id, gen_short_id


def test_gen_id_length():
    """Test gen_id produces IDs of correct length"""
    assert len(gen_id()) == 12
    assert len(gen_id(size=10)) == 10


def test_gen_id_uniqueness():
    """Test gen_id produces unique IDs (basic check)"""
    ids = {gen_id() for _ in range(100)}
    assert len(ids) == 100


def test_gen_short_id_length():
    """Test gen_short_id produces IDs of correct length"""
    assert len(gen_short_id()) == 8
    assert len(gen_short_id(size=5)) == 5
