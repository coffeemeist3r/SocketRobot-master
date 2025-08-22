import asyncio
import json
import os
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


class BaseRobotController:
    """Abstract motor controller. Real implementation uses gpiozero on the Pi; development uses a mock."""

    def forward(self) -> None:
        raise NotImplementedError

    def backward(self) -> None:
        raise NotImplementedError

    def left(self) -> None:
        raise NotImplementedError

    def right(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError


class MockRobotController(BaseRobotController):
    def __init__(self) -> None:
        self._last_cmd: str = "stop"

    def _log(self, cmd: str) -> None:
        if cmd != self._last_cmd:
            print(f"[MOCK ROBOT] {cmd}")
            self._last_cmd = cmd

    def forward(self) -> None:
        self._log("forward")

    def backward(self) -> None:
        self._log("backward")

    def left(self) -> None:
        self._log("left")

    def right(self) -> None:
        self._log("right")

    def stop(self) -> None:
        self._log("stop")


class GpioZeroRobotController(BaseRobotController):
    def __init__(self, left_forward_pin: int, left_backward_pin: int, right_forward_pin: int, right_backward_pin: int) -> None:
        # Defer import so development machines without gpiozero still run
        import gpiozero as gpio  # type: ignore

        left_motor = gpio.Motor(forward=left_forward_pin, backward=left_backward_pin)
        right_motor = gpio.Motor(forward=right_forward_pin, backward=right_backward_pin)
        self.robot = gpio.Robot(left=left_motor, right=right_motor)

    def forward(self) -> None:
        self.robot.forward()

    def backward(self) -> None:
        self.robot.backward()

    def left(self) -> None:
        self.robot.left()

    def right(self) -> None:
        self.robot.right()

    def stop(self) -> None:
        self.robot.stop()


def create_controller() -> BaseRobotController:
    """Factory that selects the real controller on Pi or mock elsewhere.

    Uses environment variable ROBOT_USE_MOCK=1 to force mock.
    """
    use_mock = os.environ.get("ROBOT_USE_MOCK", "0") == "1"
    if use_mock:
        return MockRobotController()
    try:
        # Quick probe: import gpiozero
        import importlib

        importlib.import_module("gpiozero")
        # Default to pins used in Server/server.py (BCM pins 19, 26, 16, 20)
        return GpioZeroRobotController(
            left_forward_pin=19,
            left_backward_pin=26,
            right_forward_pin=16,
            right_backward_pin=20,
        )
    except Exception as exc:  # noqa: BLE001 - best-effort detection
        print(f"gpiozero not available or failed to init ({exc}); using mock controller")
        return MockRobotController()


app = FastAPI(title="SocketRobot Web Controller")


# Serve static control UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def root_index() -> str:
    index_path = os.path.join(static_dir, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()


class ControlState:
    def __init__(self) -> None:
        self.forward: bool = False
        self.backward: bool = False
        self.left: bool = False
        self.right: bool = False

    def to_dict(self) -> dict:
        return {
            "forward": self.forward,
            "backward": self.backward,
            "left": self.left,
            "right": self.right,
        }


controller: BaseRobotController = create_controller()
state = ControlState()
apply_task: Optional[asyncio.Task] = None


def apply_state() -> None:
    # Simple conflict resolution: forward/backward have priority, left/right only if no forward/backward
    if state.forward and not state.backward:
        controller.forward()
    elif state.backward and not state.forward:
        controller.backward()
    elif state.left and not state.right and not state.forward and not state.backward:
        controller.left()
    elif state.right and not state.left and not state.forward and not state.backward:
        controller.right()
    else:
        controller.stop()


@app.websocket("/ws/control")
async def control_ws(ws: WebSocket) -> None:
    await ws.accept()
    try:
        await ws.send_json({"type": "hello", "state": state.to_dict()})
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                # Support simple text commands too
                data = {"type": "command", "cmd": raw}

            msg_type = data.get("type")

            if msg_type == "key":
                key = str(data.get("key", "")).lower()
                action = data.get("action")  # "down" | "up"
                is_down = action == "down"
                if key == "w":
                    state.forward = is_down
                elif key == "s":
                    state.backward = is_down
                elif key == "a":
                    state.left = is_down
                elif key == "d":
                    state.right = is_down
                apply_state()
                await ws.send_json({"type": "state", "state": state.to_dict()})

            elif msg_type == "command":
                cmd = str(data.get("cmd", "")).lower()
                if cmd == "forward":
                    state.forward, state.backward, state.left, state.right = True, False, False, False
                elif cmd == "backward":
                    state.forward, state.backward, state.left, state.right = False, True, False, False
                elif cmd == "left":
                    state.forward, state.backward, state.left, state.right = False, False, True, False
                elif cmd == "right":
                    state.forward, state.backward, state.left, state.right = False, False, False, True
                elif cmd == "stop":
                    state.forward, state.backward, state.left, state.right = False, False, False, False
                apply_state()
                await ws.send_json({"type": "state", "state": state.to_dict()})

            else:
                await ws.send_json({"type": "error", "message": "unknown message"})
    except WebSocketDisconnect:
        # Stop on disconnect to avoid runaway
        state.forward = state.backward = state.left = state.right = False
        apply_state()


# Uvicorn entrypoint: uvicorn webapp.main:app --host 0.0.0.0 --port 8000


