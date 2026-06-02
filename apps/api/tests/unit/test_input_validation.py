"""Tests for input validation functions that prevent Milvus filter injection."""

import pytest

from app.rag_v3.input_validation import (
    validate_paper_id,
    validate_paper_ids,
    validate_section_path,
    validate_section_paths,
    validate_user_id,
)


class TestValidateUserId:
    """Tests for validate_user_id() - prevents filter injection via user_id."""

    def test_valid_uuid_user_id(self):
        result = validate_user_id("abc123-def456-ghi789")
        assert result == "abc123-def456-ghi789"

    def test_valid_email_style_user_id(self):
        result = validate_user_id("user@example.com")
        assert result == "user@example.com"

    def test_valid_alphanumeric_user_id(self):
        result = validate_user_id("user_123.test")
        assert result == "user_123.test"

    def test_strips_whitespace(self):
        result = validate_user_id("  user123  ")
        assert result == "user123"

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            validate_user_id("")

    def test_rejects_none(self):
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            validate_user_id(None)

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            validate_user_id("   ")

    def test_rejects_too_long(self):
        long_id = "a" * 129
        with pytest.raises(ValueError, match="user_id too long"):
            validate_user_id(long_id)

    def test_accepts_max_length(self):
        max_id = "a" * 128
        result = validate_user_id(max_id)
        assert result == max_id

    def test_rejects_double_quote_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_user_id('user" OR 1==1 --')

    def test_rejects_single_quote_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_user_id("user' OR '1'='1")

    def test_rejects_backslash_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_user_id("user\\x00")

    def test_rejects_semicolon_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_user_id("user; DROP TABLE users;")

    def test_rejects_parenthesis_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_user_id("user(1)")

    def test_rejects_brace_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_user_id("user{1}")

    def test_rejects_bracket_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_user_id("user[1]")

    def test_rejects_pipe_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_user_id("user|admin")

    def test_rejects_ampersand_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_user_id("user&admin")

    def test_rejects_exclamation_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_user_id("user!")

    def test_rejects_angle_bracket_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_user_id("user<script>")


class TestValidatePaperId:
    """Tests for validate_paper_id() - prevents filter injection via paper_id."""

    def test_valid_paper_id(self):
        result = validate_paper_id("v2-p-001")
        assert result == "v2-p-001"

    def test_valid_dotted_paper_id(self):
        result = validate_paper_id("paper.123.test")
        assert result == "paper.123.test"

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="paper_id cannot be empty"):
            validate_paper_id("")

    def test_rejects_double_quote_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_paper_id('paper" OR 1==1 --')

    def test_rejects_single_quote_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_paper_id("paper' OR '1'='1")

    def test_rejects_too_long(self):
        with pytest.raises(ValueError, match="paper_id too long"):
            validate_paper_id("a" * 129)


class TestValidatePaperIds:
    """Tests for validate_paper_ids() - batch validation."""

    def test_validates_multiple_ids(self):
        result = validate_paper_ids(["paper-1", "paper-2", "paper-3"])
        assert result == ["paper-1", "paper-2", "paper-3"]

    def test_drops_invalid_ids(self):
        result = validate_paper_ids(["paper-1", 'paper"inject', "paper-3"])
        assert result == ["paper-1", "paper-3"]

    def test_returns_empty_for_none(self):
        assert validate_paper_ids(None) == []

    def test_returns_empty_for_empty_list(self):
        assert validate_paper_ids([]) == []


class TestValidateSectionPath:
    """Tests for validate_section_path()."""

    def test_valid_section_path(self):
        result = validate_section_path("methods/model")
        assert result == "methods/model"

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="section_path cannot be empty"):
            validate_section_path("")

    def test_rejects_injection(self):
        with pytest.raises(ValueError, match="invalid characters"):
            validate_section_path('path" OR 1==1')


class TestValidateSectionPaths:
    """Tests for validate_section_paths()."""

    def test_validates_multiple_paths(self):
        result = validate_section_paths(["methods", "results"])
        assert result == ["methods", "results"]

    def test_drops_invalid_paths(self):
        result = validate_section_paths(["methods", 'path"inject', "results"])
        assert result == ["methods", "results"]
