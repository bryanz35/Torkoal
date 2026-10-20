from importlib.metadata import version

import pytest

from robot_host.main import EXIT_NOT_IMPLEMENTED, main


@pytest.mark.parametrize("argv", [[], ["--sim"]])
def test_unimplemented_modes_exit_nonzero_with_reason(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(argv) == EXIT_NOT_IMPLEMENTED
    assert "not implemented yet" in capsys.readouterr().err


def test_version_reports_installed_distribution(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == version("robot-host")
