"""On-demand, offline llama.cpp inference over a private Unix socket."""

import codecs
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time


class ModelUnavailable(Exception):
    """A short fixed message suitable for the private dashboard."""


def model_files():
    binary = os.environ.get("WHALE_LLAMA_SERVER") or shutil.which("llama-server")
    executable = Path(binary or "/Applications/Ollama.app/Contents/Resources/llama-server")
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ModelUnavailable("llama-server 실행 파일을 찾지 못했습니다.")
    custom = os.environ.get("WHALE_CHAT_GGUF")
    if custom:
        weights = Path(custom).expanduser()
    else:
        root = Path.home() / ".ollama/models"
        manifest = root / "manifests/registry.ollama.ai/library/qwen2.5/3b"
        try:
            layer = next(
                v
                for v in json.loads(manifest.read_text())["layers"]
                if v["mediaType"] == "application/vnd.ollama.image.model"
            )
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", layer["digest"]):
                raise ValueError
            weights = root / "blobs" / layer["digest"].replace(":", "-")
            if weights.stat().st_size != layer["size"]:
                raise ValueError
        except (OSError, ValueError, KeyError, StopIteration, TypeError):
            raise ModelUnavailable("로컬 Qwen2.5 3B 모델 파일을 확인하세요.") from None
    try:
        with weights.open("rb") as f:
            if f.read(4) != b"GGUF":
                raise ValueError
    except (OSError, ValueError):
        raise ModelUnavailable("로컬 GGUF 모델을 읽을 수 없습니다.") from None
    return executable, weights


class UnixHTTP(http.client.HTTPConnection):
    def __init__(self, path, timeout):
        super().__init__("localhost", timeout=timeout)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)


def native_completion(helper, binary, weights, messages, limit=512):
    payload = bytearray()
    for msg in messages:
        content = msg["content"].encode()
        payload.extend(f'{msg["role"]}\n{len(content)}\n'.encode())
        payload.extend(content)
    try:
        reply = subprocess.run(
            [str(helper), str(weights), str(binary.parent), str(limit)],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=300,
            check=True,
            env={k: os.environ[k] for k in ("HOME", "PATH", "TMPDIR", "LANG") if k in os.environ},
        )
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        text = decoder.decode(reply.stdout, final=False).strip()
        if not text:
            raise ValueError
        if decoder.getstate()[0]:
            text += "\n\n응답이 글자 중간에서 끝났습니다."
        return text[:8000]
    except (OSError, subprocess.SubprocessError, ValueError):
        raise ModelUnavailable("로컬 모델이 주어진 시간 안에 답변을 완료하지 못했습니다.") from None


class LocalModel:
    def __init__(self):
        self.lock = threading.Lock()
        self.process = None
        self.closed = False
        self.temp = None
        self.path = None

    def _request(self, method, endpoint, data=None, timeout=2):
        conn = UnixHTTP(self.path, timeout)
        try:
            body = json.dumps(data).encode() if data is not None else None
            conn.request(method, endpoint, body, {"Content-Type": "application/json"})
            reply = conn.getresponse()
            if reply.status != 200:
                raise ModelUnavailable("로컬 모델이 요청을 완료하지 못했습니다.")
            return json.loads(reply.read(256000))
        finally:
            conn.close()

    def _start(self):
        if self.process and self.process.poll() is None:
            return
        self._stop()
        binary, weights = model_files()
        self.temp = tempfile.TemporaryDirectory(prefix="whale-llm-", dir="/tmp")
        self.path = str(Path(self.temp.name) / "model.sock")
        args = [
            str(binary),
            "--model",
            str(weights),
            "--offline",
            "--host",
            self.path,
            "--no-webui",
            "--log-disable",
            "--ctx-size",
            "24576",
            "--parallel",
            "1",
        ]
        env = {k: os.environ[k] for k in ("HOME", "PATH", "TMPDIR", "LANG") if k in os.environ}
        self.process = subprocess.Popen(
            args,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        deadline = time.monotonic() + 90
        while self.process.poll() is None and time.monotonic() < deadline:
            try:
                if self._request("GET", "/health").get("status") == "ok":
                    return
            except (OSError, http.client.HTTPException, ValueError, ModelUnavailable):
                time.sleep(0.25)
        self._stop()
        raise ModelUnavailable("로컬 모델을 시작할 수 없습니다. 모델·메모리·소켓 권한을 확인하세요.")

    def complete(self, messages):
        # Reserved ChatML delimiters in a source or a question stay ordinary text.
        messages = [dict(role=m["role"], content=m["content"].replace("<|", "〈|")) for m in messages]
        with self.lock:
            if self.closed:
                raise ModelUnavailable("대시보드가 종료되었습니다.")
            try:
                helper = Path(__file__).resolve().parents[1] / ".local-build/whale-chat-infer"
                if helper.is_file():
                    binary, weights = model_files()
                    return native_completion(helper, binary, weights, messages)
                self._start()
                response = self._request(
                    "POST",
                    "/v1/chat/completions",
                    dict(messages=messages, stream=False, temperature=0.2, max_tokens=750),
                    timeout=150,
                )
                content = response["choices"][0]["message"]["content"]
                if not isinstance(content, str) or not content.strip():
                    raise ValueError
                return content.strip()[:8000]
            except (OSError, http.client.HTTPException, ValueError, KeyError, IndexError, TypeError):
                self._stop()
                raise ModelUnavailable("로컬 모델의 응답을 확인할 수 없습니다.") from None

    def _stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process = None
        if self.temp:
            self.temp.cleanup()
            self.temp = None

    def close(self):
        with self.lock:
            self.closed = True
            self._stop()
