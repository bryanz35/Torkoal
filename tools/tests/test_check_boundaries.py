import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "check_boundaries", Path(__file__).resolve().parent.parent / "check_boundaries.py"
)
assert _spec is not None and _spec.loader is not None
check_boundaries = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_boundaries)


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def messages(root: Path) -> list[str]:
    return [v.message for v in check_boundaries.check(root)]


def test_empty_repository_passes(tmp_path: Path) -> None:
    assert messages(tmp_path) == []


@pytest.mark.parametrize("header", ["pico/stdlib.h", "hardware/pwm.h", "tusb.h"])
def test_sdk_header_rejected_in_portable_common(tmp_path: Path, header: str) -> None:
    write(tmp_path, "firmware/common/safety/state.c", f"#include <{header}>\n")
    assert messages(tmp_path) == [
        f"SDK header <{header}> outside firmware/platform or firmware/hal"
    ]


def test_sdk_header_allowed_in_platform_and_hal(tmp_path: Path) -> None:
    write(tmp_path, "firmware/platform/pico/timer.c", '#include "pico/time.h"\n')
    write(tmp_path, "firmware/hal/pwm.c", '#include "hardware/pwm.h"\n')
    assert messages(tmp_path) == []


def test_module_may_not_include_another_module(tmp_path: Path) -> None:
    write(tmp_path, "firmware/modules/claw/claw.h", "")
    write(tmp_path, "firmware/modules/drive/drive.c", '#include "../claw/claw.h"\n')
    assert messages(tmp_path) == ["module 'drive' includes module 'claw' (../claw/claw.h)"]


def test_api_may_not_import_transport_even_relatively(tmp_path: Path) -> None:
    write(tmp_path, "host/src/robot_host/api/routes.py", "from ..transport import serial\n")
    assert "robot_host.api imports robot_host.transport" in messages(tmp_path)


def test_driver_may_not_open_serial_ports(tmp_path: Path) -> None:
    write(tmp_path, "host/src/robot_host/modules/drive.py", "import serial_asyncio\n")
    assert messages(tmp_path) == ["robot_host.modules imports serial_asyncio"]


def test_serial_allowed_only_in_transport(tmp_path: Path) -> None:
    write(tmp_path, "host/src/robot_host/transport/serial.py", "import serial_asyncio\n")
    write(tmp_path, "host/src/robot_host/telemetry/recorder.py", "import serial\n")
    assert messages(tmp_path) == ["serial imported outside robot_host.transport"]
