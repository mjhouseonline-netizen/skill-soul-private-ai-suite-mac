import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4


def ensure_dir(path):
    path = Path(path)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        if not path.exists():
            raise
    return path


def discover_installed_models(models_root):
    models = []
    root = Path(models_root)
    if not root.exists():
        return models

    for model_path in sorted(root.rglob("*.gguf")):
        models.append(
            {
                "name": model_path.stem,
                "path": model_path,
                "size_gb": round(model_path.stat().st_size / (1024 ** 3), 2),
            }
        )
    return models


class LocalRuntimeBackend:
    def __init__(self, runtime_dir, host="127.0.0.1", port=8123):
        self.runtime_dir = Path(runtime_dir)
        self.host = host
        self.port = port
        self.process = None
        self.log_path = self.runtime_dir / "llama-server.log"
        self.log_handle = None
        self.current_model_path = None

    def find_server_binary(self):
        candidates = [
            self.runtime_dir / "llama-server.exe",
            self.runtime_dir / "llama-server",
            self.runtime_dir / "server" / "llama-server.exe",
            self.runtime_dir / "server" / "llama-server",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def status_summary(self):
        binary = self.find_server_binary()
        if binary:
            return f"Runtime ready at {binary}"
        return "No bundled llama-server runtime found yet"

    def is_running(self):
        if self.process and self.process.poll() is None:
            return True

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            return sock.connect_ex((self.host, self.port)) == 0

    def api_ready(self):
        request = urllib.request.Request(
            f"http://{self.host}:{self.port}/v1/models",
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=2) as response:
                return response.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def start(self, model_path, context_length=None):
        binary = self.find_server_binary()
        if not binary:
            raise RuntimeError(
                "No local runtime bundled yet. Place llama-server.exe in the runtime folder before shipping."
            )

        requested_model = str(Path(model_path))
        if self.api_ready():
            if self.current_model_path == requested_model:
                return
            self.stop()

        ensure_dir(self.runtime_dir)

        cmd = [
            str(binary),
            "-m",
            str(model_path),
            "--host",
            self.host,
            "--port",
            str(self.port),
        ]
        if context_length:
            cmd.extend(["-c", str(int(context_length))])

        popen_kwargs = {
            "cwd": str(self.runtime_dir),
        }
        if binary.suffix.lower() == ".exe":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            popen_kwargs["startupinfo"] = startupinfo
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        self._close_log_handle()
        log_handle = open(self.log_path, "a", encoding="utf-8")
        self.log_handle = log_handle
        log_handle.write(f"\n=== Starting runtime for {Path(model_path).name} at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        log_handle.flush()
        popen_kwargs["stdout"] = log_handle
        popen_kwargs["stderr"] = subprocess.STDOUT

        try:
            self.process = subprocess.Popen(
                cmd,
                **popen_kwargs,
            )
            self.current_model_path = requested_model
        except Exception:
            self._close_log_handle()
            self.current_model_path = None
            raise

        deadline = time.time() + 90
        while time.time() < deadline:
            if self.process and self.process.poll() is not None:
                code = self.process.returncode
                self._close_log_handle()
                self.current_model_path = None
                raise RuntimeError(
                    f"Local runtime exited early with code {code}. Check {self.log_path}"
                )
            if self.api_ready():
                return
            time.sleep(0.5)

        raise RuntimeError(f"Local runtime did not start in time. Check {self.log_path}")

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        self.current_model_path = None
        self._close_log_handle()

    def _close_log_handle(self):
        if self.log_handle:
            try:
                self.log_handle.close()
            except Exception:
                pass
        self.log_handle = None

    def chat(
        self,
        model_name,
        prompt=None,
        system_prompt="You are a helpful offline workstation assistant.",
        messages=None,
        temperature=0.7,
        max_tokens=None,
        top_p=None,
        repeat_penalty=None,
    ):
        conversation = [{"role": "system", "content": system_prompt}]
        if messages:
            conversation.extend(messages)
        elif prompt is not None:
            conversation.append({"role": "user", "content": prompt})

        payload = {
            "model": model_name,
            "messages": conversation,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens:
            payload["max_tokens"] = int(max_tokens)
        if top_p is not None:
            payload["top_p"] = top_p
        if repeat_penalty is not None:
            payload["repeat_penalty"] = repeat_penalty
        request = urllib.request.Request(
            f"http://{self.host}:{self.port}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))

        return body["choices"][0]["message"]["content"].strip()


class LocalImageBackend:
    def __init__(self, backend_dir, host="127.0.0.1", port=7860):
        self.backend_dir = Path(backend_dir)
        self.host = host
        self.port = port
        self.process = None
        self.log_path = self.backend_dir / "image-backend.log"
        self.log_handle = None

    def _base_url(self):
        return f"http://{self.host}:{self.port}"

    def _request_json(self, path, timeout=3):
        request = urllib.request.Request(f"{self._base_url()}{path}", method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def system_stats(self):
        try:
            status, body = self._request_json("/system_stats", timeout=4)
            if status == 200:
                return body
        except Exception:
            pass
        return {}

    def detect_api_kind(self):
        try:
            status, _body = self._request_json("/sdapi/v1/options", timeout=2)
            if status == 200:
                return "sdapi"
        except Exception:
            pass

        try:
            status, _body = self._request_json("/system_stats", timeout=2)
            if status == 200:
                return "comfyui"
        except Exception:
            pass
        return None

    def api_ready(self):
        return self.detect_api_kind() is not None

    def is_running(self):
        if self.process and self.process.poll() is None:
            return True
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            return sock.connect_ex((self.host, self.port)) == 0

    def find_launch_target(self):
        candidates = [
            self.backend_dir / "launch-api.bat",
            self.backend_dir / "start-image-backend.bat",
            self.backend_dir / "webui-user.bat",
            self.backend_dir / "webui.bat",
            self.backend_dir / "run.bat",
            self.backend_dir / "ComfyUI_windows_portable" / "run_nvidia_gpu.bat",
            self.backend_dir / "ComfyUI_windows_portable" / "run_cpu.bat",
            self.backend_dir / "ComfyUI_windows_portable_nvidia" / "run_nvidia_gpu.bat",
            self.backend_dir / "ComfyUI_windows_portable_nvidia" / "run_cpu.bat",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def status_summary(self):
        kind = self.detect_api_kind()
        if kind == "sdapi":
            return f"Image backend ready at {self._base_url()} (Stable Diffusion API)"
        if kind == "comfyui":
            return f"Image backend ready at {self._base_url()} (ComfyUI)"
        launch_target = self.find_launch_target()
        if launch_target:
            return f"Bundled image backend is available at {launch_target}"
        return "No bundled image backend found yet"

    def start(self):
        existing_kind = self.detect_api_kind()
        if existing_kind:
            return existing_kind

        launch_target = self.find_launch_target()
        if not launch_target:
            raise RuntimeError(
                "No local image backend bundle was found. Add a bundled backend package to the image-backend folder."
            )

        self.backend_dir.mkdir(parents=True, exist_ok=True)
        popen_kwargs = {
            "cwd": str(launch_target.parent),
            "env": self._launch_env(),
        }

        if launch_target.suffix.lower() in {".bat", ".cmd"}:
            cmd = ["cmd", "/c", str(launch_target)]
        else:
            cmd = [str(launch_target)]

        if launch_target.suffix.lower() in {".exe", ".bat", ".cmd"}:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            popen_kwargs["startupinfo"] = startupinfo
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        self._close_log_handle()
        log_handle = open(self.log_path, "a", encoding="utf-8")
        self.log_handle = log_handle
        log_handle.write(
            f"\n=== Starting image backend from {launch_target.name} at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n"
        )
        log_handle.flush()
        popen_kwargs["stdout"] = log_handle
        popen_kwargs["stderr"] = subprocess.STDOUT

        try:
            self.process = subprocess.Popen(cmd, **popen_kwargs)
        except Exception:
            self._close_log_handle()
            raise

        deadline = time.time() + 180
        while time.time() < deadline:
            kind = self.detect_api_kind()
            if kind:
                return kind
            if self.process and self.process.poll() is not None:
                code = self.process.returncode
                self._close_log_handle()
                raise RuntimeError(
                    f"Image backend exited early with code {code}. Check {self.log_path}"
                )
            time.sleep(1.0)

        raise RuntimeError(f"Image backend did not start in time. Check {self.log_path}")

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        self._close_log_handle()

    def comfyui_generate(self, prompt, output_path, size=(1024, 1024), style_name="Cinematic Poster"):
        width, height = size
        output_path = Path(output_path)
        client_id = f"offline-ai-workstation-{int(time.time())}"
        generation_profile = self._recommended_generation_profile(width, height, style_name)
        workflow = self._load_workflow_for_style(
            style_name=style_name,
            prompt=prompt,
            width=generation_profile["width"],
            height=generation_profile["height"],
            steps=generation_profile["steps"],
            cfg=generation_profile["cfg"],
            sampler=generation_profile["sampler"],
            scheduler=generation_profile["scheduler"],
            output_stem=output_path.stem,
        )
        payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base_url()}/prompt",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
        prompt_id = body.get("prompt_id")
        if not prompt_id:
            raise RuntimeError("ComfyUI did not return a prompt id.")

        deadline = time.time() + generation_profile["timeout_seconds"]
        while time.time() < deadline:
            request = urllib.request.Request(f"{self._base_url()}/history/{prompt_id}", method="GET")
            try:
                with urllib.request.urlopen(request, timeout=8) as response:
                    history = json.loads(response.read().decode("utf-8"))
            except Exception:
                time.sleep(1.0)
                continue

            prompt_history = history.get(prompt_id) or {}
            outputs = prompt_history.get("outputs") or {}
            for node_data in outputs.values():
                for image in node_data.get("images") or []:
                    filename = image.get("filename")
                    subfolder = image.get("subfolder", "")
                    image_type = image.get("type", "output")
                    if not filename:
                        continue
                    query = urlencode(
                        {
                            "filename": filename,
                            "subfolder": subfolder,
                            "type": image_type,
                        }
                    )
                    view_request = urllib.request.Request(
                        f"{self._base_url()}/view?{query}",
                        method="GET",
                    )
                    with urllib.request.urlopen(view_request, timeout=30) as response:
                        image_bytes = response.read()
                    ensure_dir(output_path.parent)
                    try:
                        output_path.write_bytes(image_bytes)
                        return output_path
                    except OSError:
                        fallback_dir = self.backend_dir / "saved-images"
                        ensure_dir(fallback_dir)
                        fallback_path = fallback_dir / f"{output_path.stem}-{uuid4().hex[:8]}{output_path.suffix or '.png'}"
                        fallback_path.write_bytes(image_bytes)
                        return fallback_path
            time.sleep(1.2)

        raise RuntimeError("ComfyUI did not finish generating an image in time.")

    def _workflow_dir_candidates(self):
        return [
            self.backend_dir / "workflows",
            self.backend_dir / "ComfyUI_windows_portable" / "workflows",
            self.backend_dir / "ComfyUI_windows_portable_nvidia" / "workflows",
        ]

    def _workflow_template_path(self, style_name):
        preferred = "premium-poster.json" if "poster" in str(style_name or "").lower() else "text-to-image.json"
        for workflow_dir in self._workflow_dir_candidates():
            candidate = workflow_dir / preferred
            if candidate.exists():
                return candidate
        for workflow_dir in self._workflow_dir_candidates():
            fallback = workflow_dir / "text-to-image.json"
            if fallback.exists():
                return fallback
        return None

    def _recommended_generation_profile(self, width, height, style_name):
        style_lower = str(style_name or "").lower()
        profile = {
            "width": int(width),
            "height": int(height),
            "steps": 28 if "poster" in style_lower else 22,
            "cfg": 7.5 if "poster" in style_lower else 6.8,
            "sampler": "euler",
            "scheduler": "normal",
            "timeout_seconds": 240,
        }

        stats = self.system_stats()
        devices = stats.get("devices") or []
        device_names = " ".join(str(device.get("name", "")) for device in devices).lower()
        using_cpu = not devices or "cpu" in device_names

        if using_cpu:
            max_dim = 640 if "poster" in style_lower else 768
            scale = min(1.0, max_dim / max(1, max(int(width), int(height))))
            scaled_width = max(512, int(round(int(width) * scale / 64.0) * 64))
            scaled_height = max(512, int(round(int(height) * scale / 64.0) * 64))
            profile.update(
                {
                    "width": scaled_width,
                    "height": scaled_height,
                    "steps": 12 if "poster" in style_lower else 10,
                    "cfg": 6.0 if "poster" in style_lower else 5.5,
                    "timeout_seconds": 600,
                }
            )

        return profile

    def _load_workflow_for_style(self, style_name, prompt, width, height, output_stem, steps=None, cfg=None, sampler=None, scheduler=None):
        template_path = self._workflow_template_path(style_name)
        if template_path and template_path.exists():
            template = json.loads(template_path.read_text(encoding="utf-8"))
        else:
            template = self._default_workflow_template()

        replacements = {
            "__PROMPT__": prompt,
            "__NEGATIVE_PROMPT__": "blurry, low quality, distorted, malformed, extra limbs, watermark, text overlay, cropped",
            "__WIDTH__": int(width),
            "__HEIGHT__": int(height),
            "__STEPS__": int(steps if steps is not None else (28 if "poster" in str(style_name or "").lower() else 22)),
            "__CFG__": float(cfg if cfg is not None else (7.5 if "poster" in str(style_name or "").lower() else 6.8)),
            "__SAMPLER__": str(sampler or "euler"),
            "__SCHEDULER__": str(scheduler or "normal"),
            "__SEED__": int(time.time() * 1000) % 2147483647,
            "__CKPT_NAME__": self._guess_comfy_checkpoint_name(),
            "__FILENAME_PREFIX__": output_stem or "offline-ai",
        }
        return self._substitute_workflow_values(template, replacements)

    def _substitute_workflow_values(self, value, replacements):
        if isinstance(value, dict):
            return {key: self._substitute_workflow_values(item, replacements) for key, item in value.items()}
        if isinstance(value, list):
            return [self._substitute_workflow_values(item, replacements) for item in value]
        if isinstance(value, str):
            if value in replacements:
                return replacements[value]
            updated = value
            for placeholder, replacement in replacements.items():
                updated = updated.replace(placeholder, str(replacement))
            return updated
        return value

    def _default_workflow_template(self):
        return {
            "3": {
                "inputs": {
                    "seed": "__SEED__",
                    "steps": "__STEPS__",
                    "cfg": "__CFG__",
                    "sampler_name": "__SAMPLER__",
                    "scheduler": "__SCHEDULER__",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
                "class_type": "KSampler",
            },
            "4": {
                "inputs": {"ckpt_name": "__CKPT_NAME__"},
                "class_type": "CheckpointLoaderSimple",
            },
            "5": {
                "inputs": {"width": "__WIDTH__", "height": "__HEIGHT__", "batch_size": 1},
                "class_type": "EmptyLatentImage",
            },
            "6": {
                "inputs": {"text": "__PROMPT__", "clip": ["4", 1]},
                "class_type": "CLIPTextEncode",
            },
            "7": {
                "inputs": {"text": "__NEGATIVE_PROMPT__", "clip": ["4", 1]},
                "class_type": "CLIPTextEncode",
            },
            "8": {
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
                "class_type": "VAEDecode",
            },
            "9": {
                "inputs": {"filename_prefix": "__FILENAME_PREFIX__", "images": ["8", 0]},
                "class_type": "SaveImage",
            },
        }

    def _guess_comfy_checkpoint_name(self):
        model_dirs = [
            self.backend_dir / "ComfyUI" / "models" / "checkpoints",
            self.backend_dir / "ComfyUI_windows_portable" / "ComfyUI" / "models" / "checkpoints",
            self.backend_dir / "ComfyUI_windows_portable_nvidia" / "ComfyUI" / "models" / "checkpoints",
            self.backend_dir / "models" / "checkpoints",
        ]
        for model_dir in model_dirs:
            if not model_dir.exists():
                continue
            for pattern in ("*.safetensors", "*.ckpt", "*.gguf", "*.pth"):
                matches = sorted(model_dir.glob(pattern))
                if matches:
                    return matches[0].name
        raise RuntimeError(
            "ComfyUI is running but no checkpoint was found in its models/checkpoints folder."
        )

    def _launch_env(self):
        env = dict(os.environ)
        env.setdefault("COMMANDLINE_ARGS", f"--api --listen --port {self.port}")
        env.setdefault("WEBUI_BROWSER", "0")
        return env

    def _close_log_handle(self):
        if self.log_handle:
            try:
                self.log_handle.close()
            except Exception:
                pass
        self.log_handle = None
