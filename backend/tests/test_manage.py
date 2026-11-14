import pytest
from app.manage import prompt_password, prompt_username


def mock_passwords(monkeypatch, values):
    entries = iter(values)
    monkeypatch.setattr('app.manage.getpass.getpass', lambda prompt: next(entries))


def test_short_password_explains_reason_and_retries(monkeypatch, capsys):
    mock_passwords(monkeypatch, ['short', 'valid-password-123', 'valid-password-123'])
    assert prompt_password() == 'valid-password-123'
    output = capsys.readouterr().out
    assert 'too short' in output
    assert 'do not match' not in output
    assert 'valid-password-123' not in output


def test_confirmation_mismatch_retries_both_entries(monkeypatch, capsys):
    mock_passwords(monkeypatch, ['valid-password-123', 'different-password', 'replacement-123', 'replacement-123'])
    assert prompt_password() == 'replacement-123'
    assert 'do not match' in capsys.readouterr().out


def test_password_limit_matches_login_schema(monkeypatch, capsys):
    mock_passwords(monkeypatch, ['x' * 201, 'x' * 200, 'x' * 200])
    assert len(prompt_password()) == 200
    assert 'too long' in capsys.readouterr().out


def test_password_whitespace_is_preserved(monkeypatch):
    mock_passwords(monkeypatch, [' padded-password ', ' padded-password '])
    assert prompt_password() == ' padded-password '


def test_invalid_username_retries_before_password(monkeypatch, capsys):
    entries = iter(['  ', 'a' * 61, ' Admin '])
    monkeypatch.setattr('builtins.input', lambda prompt: next(entries))
    assert prompt_username() == 'admin'
    output = capsys.readouterr().out
    assert 'empty' in output
    assert 'too long' in output
