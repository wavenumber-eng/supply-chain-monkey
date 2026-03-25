from pathlib import Path

from supply_chain_monkey.env import get_env_file_path, load_env_file


def test_get_env_file_path_prefers_nearest_env(tmp_path, monkeypatch) -> None:
    repo_like = tmp_path / "repo"
    nested = repo_like / "nested" / "deeper"
    nested.mkdir(parents=True)
    env_file = repo_like / ".env"
    env_file.write_text("DIGIKEY_CLIENT_ID=abc123\n", encoding="utf-8")

    monkeypatch.chdir(nested)

    assert get_env_file_path() == env_file


def test_load_env_file_parses_values_and_quotes(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DIGIKEY_CLIENT_ID='client-id'\n"
        "DIGIKEY_CLIENT_SECRET=\"client-secret\"\n"
        "MOUSER_API_KEY=mouser-key\n",
        encoding="utf-8",
    )

    values = load_env_file(path=env_file)

    assert values["DIGIKEY_CLIENT_ID"] == "client-id"
    assert values["DIGIKEY_CLIENT_SECRET"] == "client-secret"
    assert values["MOUSER_API_KEY"] == "mouser-key"


def test_env_template_exists_at_member_root() -> None:
    member_root = Path(__file__).resolve().parents[2]
    assert (member_root / ".env.template").exists()
