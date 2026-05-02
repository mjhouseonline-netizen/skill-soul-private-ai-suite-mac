import json
import os
import subprocess
import shutil
import socket
import ssl
import base64
import tempfile
import threading
import time
import tkinter as tk
import urllib.request
import webbrowser
import re
import zipfile
from pathlib import Path
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from uuid import uuid4
from xml.etree import ElementTree as ET

from runtime_backend import LocalImageBackend, LocalRuntimeBackend, discover_installed_models


def ensure_dir(path):
    path = Path(path)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        if not path.exists():
            raise
    return path


try:
    import pypdf  # type: ignore
except Exception:
    pypdf = None

try:
    import certifi  # type: ignore
except Exception:
    certifi = None

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps, ImageStat, ImageTk  # type: ignore
except Exception:
    Image = None
    ImageDraw = None
    ImageEnhance = None
    ImageFilter = None
    ImageOps = None
    ImageStat = None
    ImageTk = None

APP_NAME = "Offline AI Workstation"
APP_VERSION = "1.0"
RUNTIME_PORT = 8123
PRODUCT_EXE_NAME = "Offline-AI-Workstation"
PAYMENT_LINK = "https://your-payment-link-here"

CAPABILITY_BLURBS = [
    "Private offline chat with local GGUF models",
    "Local knowledge base from files stored on the computer",
    "Fast writing, summaries, brainstorming, and coding help",
    "Built-in image studio for local visual drafts and concept boards",
    "Local runtime bundled - no LM Studio dependency",
]

USE_CASE_BLURBS = [
    "Personal assistant for writing, admin, and idea work",
    "Research workstation for private notes and summaries",
    "Local support desk or team knowledge helper",
    "Offline creative partner for content, scripts, and plans",
]

INCLUDED_ITEMS = [
    "Desktop install with one-click launch",
    "Local runtime, presets, and workspace UI",
    "Standard Knowledge Base with local document import",
    "Built-in Image Studio for local visual generation",
    "Bring-your-own models or install recommended packs",
    "Works without internet after setup is complete",
]

INSTALL_STEPS = [
    "Choose the model pack that fits the computer's RAM",
    "Let the setup download models and prepare the runtime",
    "Open Workspace, use the included Knowledge Base, and start chatting",
]

SALES_PROMISE = "Buy once, install locally, and keep your workflow private."

KNOWLEDGE_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".xlsx",
    ".json",
    ".log",
    ".ini",
    ".cfg",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".htm",
    ".pdf",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".webp",
    ".tif",
    ".tiff",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".css",
    ".java",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".sql",
    ".ps1",
    ".bat",
}
KNOWLEDGE_MAX_DOCS = 3
KNOWLEDGE_SNIPPET_CHARS = 1800
KNOWLEDGE_TOTAL_CHARS = 4200

HTTP_HEADERS = {
    "User-Agent": f"{APP_NAME}/{APP_VERSION} Python-urllib",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


def create_ssl_context():
    if certifi is not None:
        try:
            cafile = certifi.where()
            if cafile and Path(cafile).exists():
                return ssl.create_default_context(cafile=cafile)
        except Exception:
            pass
    return ssl.create_default_context()


SSL_CONTEXT = create_ssl_context()


def safe_urlopen(request, timeout=60):
    return urllib.request.urlopen(request, timeout=timeout, context=SSL_CONTEXT)

MODELS = [
    {
        "id": "micro",
        "name": "Micro",
        "desc": "Ultra-fast. Runs on 4GB RAM.",
        "size_gb": 0.7,
        "ram_gb": 4,
        "tier": "starter",
        "filename": "Phi-3-mini-4k-instruct-q4.gguf",
        "url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf",
    },
    {
        "id": "spark",
        "name": "Spark",
        "desc": "Daily tasks, emails, summaries.",
        "size_gb": 1.5,
        "ram_gb": 6,
        "tier": "starter",
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
    },
    {
        "id": "lightning",
        "name": "Lightning",
        "desc": "Quick rewrites and simple tasks.",
        "size_gb": 1.8,
        "ram_gb": 6,
        "tier": "starter",
        "filename": "gemma-2-2b-it-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf",
    },
    {
        "id": "quick-chat",
        "name": "Quick Chat",
        "desc": "Natural conversation and brainstorming.",
        "size_gb": 2.8,
        "ram_gb": 8,
        "tier": "standard",
        "filename": "Mistral-7B-Instruct-v0.3-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Mistral-7B-Instruct-v0.3-GGUF/resolve/main/Mistral-7B-Instruct-v0.3-Q4_K_M.gguf",
    },
    {
        "id": "snapshot",
        "name": "Snapshot",
        "desc": "Understands images and screenshots.",
        "size_gb": 4.1,
        "ram_gb": 8,
        "tier": "standard",
        "filename": "llava-v1.6-mistral-7b.Q4_K_M.gguf",
        "url": "https://huggingface.co/cjpais/llava-1.6-mistral-7b-gguf/resolve/main/llava-v1.6-mistral-7b.Q4_K_M.gguf",
    },
    {
        "id": "developer",
        "name": "Developer",
        "desc": "Code generation and debugging.",
        "size_gb": 7.8,
        "ram_gb": 10,
        "tier": "standard",
        "filename": "DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF/resolve/main/DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf",
    },
    {
        "id": "storyteller",
        "name": "Storyteller",
        "desc": "Creative writing and roleplay.",
        "size_gb": 7.8,
        "ram_gb": 8,
        "tier": "standard",
        "filename": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
        "url": "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
    },
    {
        "id": "unchained",
        "name": "Unchained",
        "desc": "No content filters.",
        "size_gb": 4.92,
        "ram_gb": 8,
        "tier": "standard",
        "filename": "meta-llama-3.1-8b-instruct-abliterated.Q4_K_M.gguf",
        "url": "https://huggingface.co/mlabonne/Meta-Llama-3.1-8B-Instruct-abliterated-GGUF/resolve/main/meta-llama-3.1-8b-instruct-abliterated.Q4_K_M.gguf",
    },
    {
        "id": "balanced",
        "name": "Balanced",
        "desc": "Best all-purpose model.",
        "size_gb": 9.8,
        "ram_gb": 12,
        "tier": "pro",
        "filename": "Meta-Llama-3.1-8B-Instruct-Q6_K.gguf",
        "url": "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q6_K.gguf",
    },
    {
        "id": "vision",
        "name": "Vision",
        "desc": "Precise image Q&A.",
        "size_gb": 2.84,
        "ram_gb": 8,
        "tier": "pro",
        "filename": "moondream2-text-model-f16.gguf",
        "url": "https://huggingface.co/moondream/moondream2-gguf/resolve/main/moondream2-text-model-f16.gguf",
    },
    {
        "id": "unrestricted",
        "name": "Unrestricted",
        "desc": "Fully open generation.",
        "size_gb": 7.8,
        "ram_gb": 8,
        "tier": "pro",
        "filename": "mistral-7b-v0.1.Q4_K_M.gguf",
        "url": "https://huggingface.co/TheBloke/Mistral-7B-v0.1-GGUF/resolve/main/mistral-7b-v0.1.Q4_K_M.gguf",
    },
    {
        "id": "powerhouse",
        "name": "Powerhouse",
        "desc": "Most capable. Needs 16GB+ RAM.",
        "size_gb": 14.8,
        "ram_gb": 16,
        "tier": "pro",
        "filename": "Meta-Llama-3-70B-Instruct-Q2_K.gguf",
        "url": "https://huggingface.co/bartowski/Meta-Llama-3-70B-Instruct-GGUF/resolve/main/Meta-Llama-3-70B-Instruct-Q2_K.gguf",
    },
]

TIER_MODELS = {
    "starter": [m for m in MODELS if m["tier"] == "starter"],
    "standard": [m for m in MODELS if m["tier"] in ("starter", "standard")],
    "pro": MODELS,
}

THEMES = {
    "dark": {
        "bg": "#09111b",
        "surface": "#0f1b2a",
        "card": "#142235",
        "border": "#22364f",
        "cyan": "#3ec7e8",
        "green": "#43c97b",
        "amber": "#d39a2f",
        "red": "#ff5574",
        "text": "#eef4fb",
        "muted": "#91a2b8",
        "white": "#ffffff",
        "button_text": "#041018",
    },
    "light": {
        "bg": "#edf2f7",
        "surface": "#e0e8f0",
        "card": "#ffffff",
        "border": "#c6d2df",
        "cyan": "#0d7b95",
        "green": "#248756",
        "amber": "#a56f16",
        "red": "#d43a57",
        "text": "#182638",
        "muted": "#64758a",
        "white": "#0f1724",
        "button_text": "#ffffff",
    },
}

C = dict(THEMES["dark"])

FONT_TITLE = ("Georgia", 30, "bold")
FONT_HEAD = ("Georgia", 15, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_CHAT = ("Segoe UI", 11)
FONT_LABEL = ("Segoe UI Semibold", 9)
FONT_BUTTON = ("Segoe UI Semibold", 10)
FONT_BUTTON_SMALL = ("Segoe UI Semibold", 9)
FONT_METRIC = ("Segoe UI Semibold", 12)
WELCOME_COMPACT_BREAKPOINT = 700
WORKSPACE_COMPACT_BREAKPOINT = 980
SESSION_HISTORY_LIMIT = 12
STARTER_PROMPTS = [
    "Summarize the key points from my local knowledge base.",
    "Help me draft a professional email.",
    "Turn my notes into a step-by-step plan.",
    "Brainstorm ideas based on the files I imported.",
]
IMAGE_STYLES = {
    "Cinematic Poster": {
        "background": ("#0f1724", "#0b7d98"),
        "accent": "#1bc9e8",
        "glow": "#2fcf6b",
        "text": "#f4f8fc",
    },
    "Blueprint": {
        "background": ("#0d2640", "#173f66"),
        "accent": "#6cc6ff",
        "glow": "#d7f3ff",
        "text": "#f4fbff",
    },
    "Sunset Editorial": {
        "background": ("#351431", "#cc6a3b"),
        "accent": "#ffd369",
        "glow": "#fff0b3",
        "text": "#fff8ef",
    },
    "Mono Minimal": {
        "background": ("#161616", "#646464"),
        "accent": "#f5f5f5",
        "glow": "#d8d8d8",
        "text": "#ffffff",
    },
}
IMAGE_SIZES = {
    "Square 640": (640, 640),
    "Portrait 640x832": (640, 832),
    "Landscape 832x512": (832, 512),
    "Square 1024": (1024, 1024),
    "Portrait 1024x1280": (1024, 1280),
    "Landscape 1280x768": (1280, 768),
    "Banner 1536x768": (1536, 768),
}
DEFAULT_SETTINGS = {
    "startup_model_path": "",
    "auto_start_runtime": False,
    "auto_start_image_backend": False,
    "open_workspace_on_launch": True,
    "collapse_models_by_default": False,
    "appearance": "dark",
    "image_backend_mode": "auto",
    "image_backend_url": "http://127.0.0.1:7860",
}
DEFAULT_MODEL_PRESET = {
    "name": "General Assistant",
    "systemPrompt": "You are a helpful offline workstation assistant.",
    "temperature": 0.7,
    "maxTokens": 1024,
    "topP": 0.9,
    "repeatPenalty": 1.1,
    "contextLength": 4096,
    "note": "General-purpose local assistant for writing, questions, and planning.",
}


def recommended_image_size_label(sys_info):
    profile = str((sys_info or {}).get("image_acceleration_profile", "")).lower()
    if profile == "cpu":
        return "Square 640"
    if profile == "mixed":
        return "Portrait 640x832"
    return "Square 1024"


def detect_system():
    import platform

    info = {}
    info["os"] = platform.system()
    info["arch"] = platform.machine()
    try:
        usage = shutil.disk_usage(Path.home())
        info["disk_free_gb"] = round(usage.free / (1024 ** 3))
    except Exception:
        info["disk_free_gb"] = 50

    try:
        if info["os"] == "Windows":
            import ctypes

            class MEMORYSTATUS(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("dwTotalPhys", ctypes.c_size_t),
                    ("dwAvailPhys", ctypes.c_size_t),
                    ("dwTotalPageFile", ctypes.c_size_t),
                    ("dwAvailPageFile", ctypes.c_size_t),
                    ("dwTotalVirtual", ctypes.c_size_t),
                    ("dwAvailVirtual", ctypes.c_size_t),
                ]

            stat = MEMORYSTATUS()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatus(ctypes.byref(stat))
            info["ram_gb"] = round(stat.dwTotalPhys / (1024 ** 3))
        else:
            info["ram_gb"] = 8
    except Exception:
        info["ram_gb"] = 8

    info["graphics_name"] = "Unknown graphics"
    info["graphics_vendor"] = "unknown"
    info["image_acceleration_profile"] = "cpu"
    info["image_acceleration_note"] = "Image generation will use a slower local mode on this computer."

    try:
        if info["os"] == "Windows":
            import ctypes

            class DISPLAY_DEVICE(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.c_ulong),
                    ("DeviceName", ctypes.c_wchar * 32),
                    ("DeviceString", ctypes.c_wchar * 128),
                    ("StateFlags", ctypes.c_ulong),
                    ("DeviceID", ctypes.c_wchar * 128),
                    ("DeviceKey", ctypes.c_wchar * 128),
                ]

            devices = []
            index = 0
            while True:
                device = DISPLAY_DEVICE()
                device.cb = ctypes.sizeof(DISPLAY_DEVICE)
                if not ctypes.windll.user32.EnumDisplayDevicesW(None, index, ctypes.byref(device), 0):
                    break
                name = (device.DeviceString or "").strip()
                if name:
                    devices.append(name)
                index += 1

            if devices:
                primary_name = devices[0]
                lower_name = primary_name.lower()
                info["graphics_name"] = primary_name
                if "nvidia" in lower_name or "geforce" in lower_name or "rtx" in lower_name or "gtx" in lower_name:
                    info["graphics_vendor"] = "nvidia"
                    info["image_acceleration_profile"] = "gpu"
                    info["image_acceleration_note"] = "NVIDIA graphics detected. Best local image performance is available."
                elif "amd" in lower_name or "radeon" in lower_name:
                    info["graphics_vendor"] = "amd"
                    info["image_acceleration_profile"] = "mixed"
                    info["image_acceleration_note"] = "AMD graphics detected. Local image features may need a CPU-friendly backend bundle."
                elif "intel" in lower_name or "uhd" in lower_name or "iris" in lower_name:
                    info["graphics_vendor"] = "intel"
                    info["image_acceleration_profile"] = "cpu"
                    info["image_acceleration_note"] = "Integrated Intel graphics detected. Local image generation will work best in CPU mode and may be slower."
    except Exception:
        pass

    app_home = Path.home() / ".offline-ai-workstation"
    info["app_home"] = app_home
    info["models_dir"] = app_home / "models"
    info["presets_dir"] = app_home / "presets"
    info["runtime_dir"] = app_home / "runtime"
    info["image_backend_dir"] = app_home / "image-backend"
    info["ocr_dir"] = app_home / "ocr"
    info["knowledge_dir"] = app_home / "knowledge-base"
    info["images_dir"] = app_home / "generated-images"
    info["sessions_file"] = app_home / "chat-sessions.json"
    info["settings_file"] = app_home / "settings.json"
    return info


def get_model_target_path(models_root, model):
    parsed = urlparse(model["url"])
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2:
        publisher = parts[0]
        repo = parts[1]
    else:
        publisher = "local"
        repo = model["id"]
    return Path(models_root) / publisher / repo / model["filename"]


def get_preset_search_roots():
    roots = []
    if getattr(__import__("sys"), "frozen", False):
        import sys

        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass))
        roots.append(Path(sys.executable).resolve().parent)
    else:
        src_dir = Path(__file__).resolve().parent
        roots.extend([src_dir.parent, src_dir.parent.parent, src_dir])
    seen = set()
    unique_roots = []
    for root in roots:
        key = str(root)
        if key not in seen:
            unique_roots.append(root)
            seen.add(key)
    return unique_roots


def get_platform_bundle_names(base_name):
    system = platform.system().lower()
    arch = platform.machine().lower()
    names = []

    if system == "darwin":
        names.extend(
            [
                f"{base_name}-mac-{arch}",
                f"{base_name}-darwin-{arch}",
                f"{base_name}-mac",
                f"{base_name}-macos",
                f"{base_name}-darwin",
            ]
        )
    elif system == "windows":
        names.extend(
            [
                f"{base_name}-windows-{arch}",
                f"{base_name}-win-{arch}",
                f"{base_name}-windows",
                f"{base_name}-win",
            ]
        )
    else:
        names.extend(
            [
                f"{base_name}-linux-{arch}",
                f"{base_name}-linux",
            ]
        )

    names.append(base_name)

    unique = []
    seen = set()
    for name in names:
        if name not in seen:
            unique.append(name)
            seen.add(name)
    return unique


def find_bundled_directory(base_name):
    for base in get_preset_search_roots():
        for folder_name in get_platform_bundle_names(base_name):
            candidate = base / folder_name
            if candidate.exists():
                return candidate
    return None


def copy_bundle_contents(source_dir, dest_dir):
    source_dir = Path(source_dir)
    dest_dir = Path(dest_dir)
    copied = 0
    skipped = 0

    for item in source_dir.iterdir():
        dest = dest_dir / item.name
        if item.is_dir():
            if dest.exists():
                shutil.copytree(str(item), str(dest), dirs_exist_ok=True)
                skipped += 1
            else:
                shutil.copytree(str(item), str(dest))
                copied += 1
            continue
        if dest.exists():
            skipped += 1
            continue
        shutil.copy2(str(item), str(dest))
        copied += 1
    return copied, skipped


def copy_bundled_runtime(runtime_dir):
    runtime_dir = Path(runtime_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    bundled_runtime = find_bundled_directory("runtime-bin")
    if not bundled_runtime:
        return 0, 0
    copied, skipped = copy_bundle_contents(bundled_runtime, runtime_dir)
    return copied, skipped


def copy_bundled_image_backend(backend_dir):
    backend_dir = Path(backend_dir)
    backend_dir.mkdir(parents=True, exist_ok=True)
    bundled_backend = find_bundled_directory("image-backend-bin")
    if not bundled_backend:
        return 0, 0
    copied, skipped = copy_bundle_contents(bundled_backend, backend_dir)
    return copied, skipped


def _ocr_binary_name():
    return "tesseract.exe" if os.name == "nt" else "tesseract"


def find_bundled_ocr_assets():
    installer = None
    traineddata = None
    runtime_dir = None
    binary_name = _ocr_binary_name()
    for base in get_preset_search_roots():
        for folder_name in get_platform_bundle_names("ocr-bin"):
            bundled_ocr = base / folder_name
            if not bundled_ocr.exists():
                continue
            candidate_runtime = bundled_ocr / "runtime"
            candidate_installer = bundled_ocr / "tesseract-ocr-w64-setup.exe"
            traineddata_candidates = [
                bundled_ocr / "eng.traineddata",
                bundled_ocr / "tessdata" / "eng.traineddata",
                candidate_runtime / "eng.traineddata",
                candidate_runtime / "tessdata" / "eng.traineddata",
            ]
            if runtime_dir is None:
                if (candidate_runtime / binary_name).exists() or candidate_runtime.exists():
                    runtime_dir = candidate_runtime
                elif (bundled_ocr / binary_name).exists():
                    runtime_dir = bundled_ocr
            if installer is None and candidate_installer.exists():
                installer = candidate_installer
            if traineddata is None:
                for candidate_traineddata in traineddata_candidates:
                    if candidate_traineddata.exists():
                        traineddata = candidate_traineddata
                        break
            if runtime_dir and traineddata:
                break
        if runtime_dir and traineddata:
            break
    return runtime_dir, installer, traineddata


def install_bundled_ocr(ocr_dir):
    ocr_dir = Path(ocr_dir)
    ocr_dir.mkdir(parents=True, exist_ok=True)
    tesseract_exe = ocr_dir / _ocr_binary_name()
    tessdata_dir = ocr_dir / "tessdata"
    eng_data = tessdata_dir / "eng.traineddata"
    if tesseract_exe.exists() and eng_data.exists():
        return "ready"

    runtime_dir, installer, traineddata = find_bundled_ocr_assets()
    if runtime_dir and not tesseract_exe.exists():
        copy_bundle_contents(runtime_dir, ocr_dir)
    elif installer and not tesseract_exe.exists():
        cmd = [str(installer), "/S", f"/D={ocr_dir}"]
        popen_kwargs = {}
        if installer.suffix.lower() == ".exe" and os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            popen_kwargs["startupinfo"] = startupinfo
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        subprocess.run(cmd, check=True, timeout=300, **popen_kwargs)

    if traineddata and not eng_data.exists():
        tessdata_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(traineddata), str(eng_data))

    if tesseract_exe.exists() and os.name != "nt":
        current_mode = tesseract_exe.stat().st_mode
        tesseract_exe.chmod(current_mode | 0o111)

    if tesseract_exe.exists() and eng_data.exists():
        return "ready"
    if tesseract_exe.exists():
        return "partial"
    return "missing"


def discover_knowledge_documents(knowledge_root):
    docs = []
    root = Path(knowledge_root)
    if not root.exists():
        return docs

    for doc_path in sorted(root.rglob("*")):
        if not doc_path.is_file():
            continue
        if doc_path.suffix.lower() not in KNOWLEDGE_EXTENSIONS:
            continue
        try:
            size_kb = round(doc_path.stat().st_size / 1024, 1)
        except OSError:
            size_kb = 0
        docs.append(
            {
                "name": doc_path.name,
                "path": doc_path,
                "suffix": doc_path.suffix.lower(),
                "size_kb": size_kb,
            }
        )
    return docs


def read_knowledge_text(doc_path, max_chars=KNOWLEDGE_SNIPPET_CHARS):
    path = Path(doc_path)
    suffix = path.suffix.lower()

    if suffix == ".docx":
        text = _read_docx_text(path)
        return text[:max_chars]
    if suffix == ".xlsx":
        text = _read_xlsx_text(path)
        return text[:max_chars]
    if suffix == ".pdf":
        text = _read_pdf_text(path)
        return text[:max_chars]
    if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff"}:
        text = _read_image_text(path)
        return text[:max_chars]

    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
    except Exception:
        return ""

    text = re.sub(r"\s+", " ", raw).strip()
    return text[:max_chars]


def _read_docx_text(path):
    try:
        with zipfile.ZipFile(path) as archive:
            xml_bytes = archive.read("word/document.xml")
    except Exception:
        return ""

    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return ""

    namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    chunks = []
    for paragraph in root.findall(".//w:p", namespaces):
        parts = [node.text for node in paragraph.findall(".//w:t", namespaces) if node.text]
        if parts:
            chunks.append("".join(parts))
    return re.sub(r"\s+", " ", "\n".join(chunks)).strip()


def _read_xlsx_text(path):
    try:
        with zipfile.ZipFile(path) as archive:
            shared_strings = _read_xlsx_shared_strings(archive)
            sheet_names = sorted(
                name for name in archive.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
            )
            chunks = []
            for sheet_name in sheet_names:
                try:
                    xml_bytes = archive.read(sheet_name)
                except Exception:
                    continue
                sheet_text = _read_xlsx_sheet_text(xml_bytes, shared_strings)
                if sheet_text:
                    chunks.append(sheet_text)
    except Exception:
        return ""

    return re.sub(r"\s+", " ", "\n".join(chunks)).strip()


def _read_xlsx_shared_strings(archive):
    shared = []
    try:
        xml_bytes = archive.read("xl/sharedStrings.xml")
    except Exception:
        return shared

    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return shared

    namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    for item in root.findall(".//a:si", namespace):
        parts = [node.text for node in item.findall(".//a:t", namespace) if node.text]
        shared.append("".join(parts))
    return shared


def _read_xlsx_sheet_text(xml_bytes, shared_strings):
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return ""

    namespace = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rows = []
    for row in root.findall(".//a:sheetData/a:row", namespace):
        values = []
        for cell in row.findall("a:c", namespace):
            cell_type = cell.attrib.get("t", "")
            value_node = cell.find("a:v", namespace)
            inline_node = cell.find("a:is", namespace)
            cell_text = ""
            if cell_type == "s" and value_node is not None and value_node.text:
                try:
                    index = int(value_node.text)
                    if 0 <= index < len(shared_strings):
                        cell_text = shared_strings[index]
                except Exception:
                    cell_text = value_node.text
            elif inline_node is not None:
                parts = [node.text for node in inline_node.findall(".//a:t", namespace) if node.text]
                cell_text = "".join(parts)
            elif value_node is not None and value_node.text:
                cell_text = value_node.text

            cell_text = re.sub(r"\s+", " ", cell_text).strip()
            if cell_text:
                values.append(cell_text)
        if values:
            rows.append(" | ".join(values))
    return "\n".join(rows)


def _read_pdf_text(path):
    try:
        if pypdf is not None:
            reader = pypdf.PdfReader(str(path))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                return text
    except Exception:
        pass

    try:
        raw = path.read_bytes()
    except Exception:
        return ""

    # Lightweight fallback: decode text-like PDF segments well enough for simple local retrieval.
    decoded = raw.decode("latin-1", errors="ignore")
    matches = re.findall(r"\(([^()]*)\)\s*Tj", decoded)
    matches.extend(fragment.replace("\\)", ")").replace("\\(", "(") for fragment in re.findall(r"\[(.*?)\]\s*TJ", decoded))
    text = " ".join(matches)
    text = re.sub(r"\\[nrt]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _find_tesseract_executable():
    try:
        candidate = shutil.which("tesseract")
        if candidate:
            return candidate
    except Exception:
        pass

    common_paths = [
        Path.home() / ".offline-ai-workstation" / "ocr" / "tesseract",
        Path.home() / ".offline-ai-workstation" / "ocr" / "tesseract.exe",
        Path("/opt/homebrew/bin/tesseract"),
        Path("/usr/local/bin/tesseract"),
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
        Path.home() / "AppData/Local/Programs/Tesseract-OCR/tesseract.exe",
    ]
    for candidate in common_paths:
        if candidate.exists():
            return str(candidate)
    return None


def _read_image_text(path):
    if Image is None:
        return ""

    try:
        with Image.open(path) as image:
            width, height = image.size
            mode = image.mode
            metadata = f"Image file: {path.name} ({width}x{height}, {mode})."
            prepared = image.convert("L")
    except Exception:
        return ""

    tesseract_path = _find_tesseract_executable()
    ocr_text = ""
    if tesseract_path:
        temp_image_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_image:
                temp_image_path = Path(tmp_image.name)
            prepared.save(temp_image_path)
            tessdata_dir = Path(tesseract_path).resolve().parent / "tessdata"
            env = os.environ.copy()
            if tessdata_dir.exists():
                env["TESSDATA_PREFIX"] = str(tessdata_dir)
            result = subprocess.run(
                [
                    str(tesseract_path),
                    str(temp_image_path),
                    "stdout",
                    "-l",
                    "eng",
                ],
                capture_output=True,
                text=True,
                timeout=45,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if result.returncode == 0:
                ocr_text = result.stdout.strip()
        except Exception:
            ocr_text = ""
        finally:
            try:
                if temp_image_path:
                    temp_image_path.unlink(missing_ok=True)
            except Exception:
                pass

    if ocr_text:
        cleaned = re.sub(r"\s+", " ", ocr_text).strip()
        return f"{metadata} OCR text: {cleaned}"

    return (
        f"{metadata} OCR text is not available on this installation yet. "
        "Bundled OCR is missing or not ready, so screenshots and scanned images are not searchable yet."
    )


def build_knowledge_context(query, knowledge_docs):
    query_terms = {term for term in re.findall(r"[a-z0-9]{3,}", query.lower())}
    ranked = []
    for doc in knowledge_docs:
        snippet = read_knowledge_text(doc["path"])
        if not snippet:
            continue

        haystack = f"{doc['name'].lower()} {snippet.lower()}"
        score = 0
        for term in query_terms:
            if term in haystack:
                score += 3 if term in doc["name"].lower() else 1
        if query_terms and score == 0:
            continue
        ranked.append((score, doc, snippet))

    if not ranked and knowledge_docs:
        for doc in knowledge_docs[:KNOWLEDGE_MAX_DOCS]:
            snippet = read_knowledge_text(doc["path"])
            if snippet:
                ranked.append((0, doc, snippet))

    ranked.sort(key=lambda item: (-item[0], item[1]["name"].lower()))
    blocks = []
    total_chars = 0
    for _score, doc, snippet in ranked[:KNOWLEDGE_MAX_DOCS]:
        remaining = KNOWLEDGE_TOTAL_CHARS - total_chars
        if remaining <= 0:
            break
        clipped = snippet[:remaining]
        block = f"[Document: {doc['name']}]\n{clipped}"
        blocks.append(block)
        total_chars += len(clipped)

    if not blocks:
        return ""
    return "\n\n".join(blocks)


def suggest_chat_title(text):
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return "New Chat"
    if len(cleaned) <= 36:
        return cleaned
    return cleaned[:33].rstrip() + "..."


def message_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _hex_to_rgb(color):
    color = color.lstrip("#")
    if len(color) != 6:
        return 255, 255, 255
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def _blend_colors(color_a, color_b, ratio):
    ratio = max(0.0, min(1.0, ratio))
    a = _hex_to_rgb(color_a)
    b = _hex_to_rgb(color_b)
    return tuple(int(a[i] * (1.0 - ratio) + b[i] * ratio) for i in range(3))


def _wrap_prompt_lines(text, max_len=28, max_lines=5):
    words = re.findall(r"\S+", text.strip())
    if not words:
        return ["Untitled visual"]

    lines = []
    current = ""
    for word in words:
        next_line = word if not current else f"{current} {word}"
        if len(next_line) <= max_len:
            current = next_line
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) >= max_lines - 1:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(words) > sum(len(line.split()) for line in lines):
        lines[-1] = lines[-1][: max(0, max_len - 3)].rstrip() + "..."
    return lines[:max_lines]


def _prompt_seed(prompt, style_name):
    source = f"{style_name}|{prompt}".encode("utf-8", errors="ignore")
    total = 0
    for index, byte in enumerate(source, start=1):
        total = (total + index * byte) % 2_147_483_647
    return total or 1337


def _fit_reference_image(reference_path, size):
    if Image is None:
        return None
    try:
        with Image.open(reference_path) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
            return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)
    except Exception:
        return None


def _extract_prompt_profile(prompt):
    lower = prompt.lower()
    raw_words = re.findall(r"[a-z0-9']+", lower)
    stopwords = {
        "a", "an", "the", "and", "or", "for", "with", "from", "into", "onto", "that", "this", "these", "those",
        "create", "make", "generate", "design", "show", "turn", "transform", "based", "using", "uploaded", "image",
        "person", "photo", "look", "looks", "style", "styled", "premium", "high", "quality", "of", "to", "in",
        "on", "at", "by", "it", "as", "be", "is", "are",
    }
    keywords = [word for word in raw_words if word not in stopwords]

    mode = "poster"
    if any(word in lower for word in ("collector", "figure", "edition", "packaging", "boxed", "toy", "doll")):
        mode = "collector"
    elif any(word in lower for word in ("card", "tarot", "book cover", "cover")):
        mode = "cover"

    mood = "editorial"
    if any(word in lower for word in ("fantasy", "magical", "enchanted", "mythic")):
        mood = "fantasy"
    elif any(word in lower for word in ("cyberpunk", "neon", "futuristic", "sci-fi", "scifi")):
        mood = "cyberpunk"
    elif any(word in lower for word in ("luxury", "premium", "executive", "fashion")):
        mood = "luxury"
    elif any(word in lower for word in ("vintage", "retro", "classic")):
        mood = "retro"

    scene_request = any(phrase in lower for phrase in ("image of", "picture of", "photo of", "scene of", "landscape of", "illustration of"))
    scene_subject = any(word in lower for word in ("sunset", "sunrise", "beach", "ocean", "lake", "forest", "mountain", "garden", "moonlit", "night sky", "skyline"))

    composition = "editorial"
    if any(phrase in lower for phrase in ("product mockup", "product shot", "packaging shot", "boxed product", "hero product")):
        composition = "product_mockup"
    elif any(phrase in lower for phrase in ("story frame", "story scene", "film still", "movie still", "cinematic frame")):
        composition = "story_frame"
    elif any(phrase in lower for phrase in ("luxury editorial", "campaign", "fashion spread", "magazine", "editorial")):
        composition = "luxury_editorial"
    elif scene_request or scene_subject:
        composition = "fantasy_scene"
    elif any(phrase in lower for phrase in ("fantasy scene", "landscape", "worldbuilding", "environment concept")):
        composition = "fantasy_scene"
    elif mode == "collector":
        composition = "product_mockup"
    elif mood == "fantasy":
        composition = "fantasy_scene"
    elif mood == "luxury":
        composition = "luxury_editorial"
    elif any(word in lower for word in ("scene", "kingdom", "temple", "forest", "moonlit", "lake", "mountain")):
        composition = "fantasy_scene"
    elif any(word in lower for word in ("poster", "frame", "cinematic")):
        composition = "story_frame"

    headline = "Visual Concept"
    subheadline = "Prompt-guided local concept render"
    if mode == "collector":
        headline = "Collector Edition"
        subheadline = "Premium figure packaging concept"
    elif mode == "cover":
        headline = "Signature Cover"
        subheadline = "Prompt-guided editorial cover concept"
    elif mood == "fantasy":
        headline = "Fantasy Portrait"
        subheadline = "Cinematic character concept"
    elif mood == "cyberpunk":
        headline = "Neon Character"
        subheadline = "Futuristic concept composition"
    elif mood == "luxury":
        headline = "Luxury Portrait"
        subheadline = "Premium campaign concept"
    elif composition == "fantasy_scene":
        headline = "Scene Render"
        subheadline = "Local offline artwork"

    noun_candidates = []
    for word in keywords:
        if word in {"collector", "edition", "figure", "premium", "fantasy", "person", "uploaded", "image"}:
            continue
        if word not in noun_candidates:
            noun_candidates.append(word)
    accents = noun_candidates[:4] or ["portrait", "concept", "local"]
    prompt_summary = " ".join(word.title() for word in accents[:3])
    if prompt_summary and composition != "fantasy_scene":
        headline = prompt_summary if mode == "poster" else headline

    archetypes = [
        "forest guardian",
        "celestial oracle",
        "desert mystic",
        "water priestess",
        "dream alchemist",
        "spirit healer",
        "moon archivist",
        "starborn knight",
        "crystal druid",
    ]
    environments = [
        "enchanted forest",
        "floating sky realm",
        "ancient ruins",
        "cozy magical cottage",
        "underwater sanctuary",
        "moonlit observatory",
        "crystal temple",
        "twilight garden",
    ]
    effects = [
        "glowing light",
        "swirling mist",
        "floating particles",
        "magical plants",
        "energy trails",
        "soft stardust",
        "aurora ribbons",
    ]
    accessory_pool = [
        "alternate face",
        "alternate hands",
        "crystal",
        "lantern",
        "book",
        "herbs",
        "amulet",
        "potion",
        "staff",
        "rune cards",
    ]
    phrases = [
        "Quiet power still changes the room.",
        "Calm is a form of magic.",
        "Grace carries hidden strength.",
        "Your light does not need permission.",
        "Stillness can move worlds.",
    ]

    def _pick_phrase(options, default):
        for option in options:
            if option in lower:
                return option
        return default

    seed = _prompt_seed(prompt, mode)
    import random

    rng = random.Random(seed)
    archetype = _pick_phrase(archetypes, rng.choice(archetypes))
    environment = _pick_phrase(environments, rng.choice(environments))
    effect = _pick_phrase(effects, rng.choice(effects))
    accessories = [item for item in accessory_pool if item in lower]
    if not accessories:
        accessories = rng.sample(accessory_pool, 4)
    phrase = ""
    for line in re.split(r"[\r\n]+", prompt):
        candidate = line.strip().strip('"').strip("'")
        lowered = candidate.lower()
        if not candidate:
            continue
        if len(candidate.split()) > 12:
            continue
        if any(token in lowered for token in ("include", "incorporate", "ensure", "style:", "lighting should", "transform the person")):
            continue
        if "power" in lowered or "calm" in lowered or "strength" in lowered:
            phrase = candidate
            break
    if not phrase:
        phrase = rng.choice(phrases)

    return {
        "mode": mode,
        "mood": mood,
        "composition": composition,
        "clean_scene": composition == "fantasy_scene",
        "headline": headline,
        "subheadline": subheadline,
        "labels": [word.title() for word in accents[:3]],
        "archetype": archetype.title(),
        "environment": environment.title(),
        "effect": effect.title(),
        "accessories": [item.title() for item in accessories[:4]],
        "phrase": phrase.strip().strip('"'),
    }


def _palette_for_profile(style, profile):
    if profile["mood"] == "fantasy":
        return {
            "background": ("#1a1230", "#6d3fa8"),
            "accent": "#f1d67a",
            "glow": "#ffe8a8",
            "text": "#fff9ea",
        }
    if profile["mood"] == "cyberpunk":
        return {
            "background": ("#0b122a", "#0a677f"),
            "accent": "#5ef2ff",
            "glow": "#ff4fd8",
            "text": "#f4feff",
        }
    if profile["mood"] == "luxury":
        return {
            "background": ("#131313", "#5f4a2b"),
            "accent": "#f3d58a",
            "glow": "#fff1c7",
            "text": "#fffaf1",
        }
    if profile["mood"] == "retro":
        return {
            "background": ("#2b1d18", "#aa6938"),
            "accent": "#ffd18a",
            "glow": "#fff0cf",
            "text": "#fff7ef",
        }
    return dict(style)


def _reference_anchor_image(reference_path, size, palette, soften=False):
    image = _fit_reference_image(reference_path, size)
    if image is None:
        return None
    if ImageEnhance is not None:
        image = ImageEnhance.Contrast(image).enhance(1.08)
        image = ImageEnhance.Color(image).enhance(1.18)
    if soften and ImageFilter is not None:
        image = image.filter(ImageFilter.GaussianBlur(radius=0.5))
    return image


def _reference_portrait_image(reference_path, size, soften=False):
    if Image is None:
        return None
    try:
        with Image.open(reference_path) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
            src_w, src_h = image.size
            target_w, target_h = size
            crop_w = max(1, int(src_w * 0.58))
            crop_h = max(1, int(src_h * 0.72))
            left = max(0, (src_w - crop_w) // 2)
            top = max(0, int(src_h * 0.06))
            if top + crop_h > src_h:
                top = max(0, src_h - crop_h)
            crop = image.crop((left, top, left + crop_w, top + crop_h))
            portrait = ImageOps.fit(crop, size, method=Image.Resampling.LANCZOS)
            if ImageEnhance is not None:
                portrait = ImageEnhance.Contrast(portrait).enhance(1.1)
                portrait = ImageEnhance.Color(portrait).enhance(1.08)
                portrait = ImageEnhance.Sharpness(portrait).enhance(1.1)
            if soften and ImageFilter is not None:
                portrait = portrait.filter(ImageFilter.GaussianBlur(radius=0.35))
            return portrait
    except Exception:
        return None


def _safe_font(size, bold=False):
    try:
        from PIL import ImageFont  # type: ignore

        for candidate in (("georgiab.ttf" if bold else "georgia.ttf"), ("arialbd.ttf" if bold else "arial.ttf")):
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:
                continue
        return ImageFont.load_default()
    except Exception:
        return None


def _rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def _subject_palette_from_reference(reference_path, palette):
    fallback = {
        "primary": _hex_to_rgb(palette["accent"]),
        "secondary": _hex_to_rgb(palette["glow"]),
        "shadow": (34, 28, 46),
    }
    if ImageStat is None:
        return fallback
    try:
        with Image.open(reference_path) as original:
            image = ImageOps.exif_transpose(original).convert("RGB").resize((160, 160))
            stat = ImageStat.Stat(image)
            average = tuple(int(v) for v in stat.mean[:3])
            return {
                "primary": average,
                "secondary": tuple(min(255, int(v * 1.18) + 18) for v in average),
                "shadow": tuple(max(0, int(v * 0.34)) for v in average),
            }
    except Exception:
        return fallback


def _draw_environment_scene(draw, box, environment, palette, rng):
    x0, y0, x1, y1 = box
    width = x1 - x0
    height = y1 - y0
    accent = _hex_to_rgb(palette["accent"])
    glow = _hex_to_rgb(palette["glow"])
    deep = _hex_to_rgb(palette["background"][0])
    mid = _hex_to_rgb(palette["background"][1])
    env = environment.lower()

    if "forest" in env or "garden" in env:
        for _ in range(10):
            trunk_x = rng.randint(x0 + 20, x1 - 35)
            trunk_w = rng.randint(10, 20)
            trunk_h = rng.randint(height // 5, height // 2)
            draw.rounded_rectangle((trunk_x, y1 - trunk_h - 18, trunk_x + trunk_w, y1 - 18), radius=4, fill=(92, 63, 42, 220))
            canopy = (trunk_x - 24, y1 - trunk_h - 52, trunk_x + trunk_w + 34, y1 - trunk_h + 24)
            draw.ellipse(canopy, fill=(*accent, 110))
            draw.ellipse((canopy[0] + 12, canopy[1] - 8, canopy[2] + 18, canopy[3] - 10), fill=(*glow, 60))
    elif "sky" in env or "observatory" in env:
        for _ in range(14):
            cx = rng.randint(x0 + 20, x1 - 20)
            cy = rng.randint(y0 + 20, y0 + height // 2)
            r = rng.randint(2, 5)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*glow, 180))
        for _ in range(4):
            cx = rng.randint(x0 + 30, x1 - 90)
            cy = rng.randint(y0 + 40, y0 + height // 3)
            draw.rounded_rectangle((cx, cy, cx + rng.randint(70, 120), cy + rng.randint(22, 34)), radius=16, fill=(255, 255, 255, 38))
    elif "ruins" in env or "temple" in env:
        for column in range(4):
            col_x = x0 + 40 + column * max(54, width // 5)
            col_h = rng.randint(height // 3, int(height * 0.62))
            draw.rounded_rectangle((col_x, y1 - col_h - 24, col_x + 26, y1 - 24), radius=8, fill=(*mid, 200))
            draw.rounded_rectangle((col_x - 6, y1 - col_h - 38, col_x + 32, y1 - col_h - 18), radius=8, fill=(*glow, 72))
    elif "underwater" in env or "water" in env:
        for _ in range(20):
            cx = rng.randint(x0 + 12, x1 - 12)
            cy = rng.randint(y0 + 20, y1 - 20)
            r = rng.randint(5, 18)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, 70), width=2)
        for _ in range(6):
            sea_x = rng.randint(x0 + 10, x1 - 60)
            sea_y = y1 - rng.randint(50, 120)
            draw.polygon([(sea_x, sea_y), (sea_x + 20, sea_y - 70), (sea_x + 42, sea_y)], fill=(*accent, 88))
    else:
        draw.rounded_rectangle((x0 + 24, y0 + 24, x1 - 24, y1 - 24), radius=32, outline=(*glow, 95), width=2)
        for _ in range(9):
            cx = rng.randint(x0 + 20, x1 - 20)
            cy = rng.randint(y0 + 20, y1 - 20)
            r = rng.randint(18, 42)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*accent, 22))
    draw.rectangle((x0, y1 - 36, x1, y1), fill=(*deep, 170))


def _draw_magic_effects(draw, box, effect, palette, rng):
    x0, y0, x1, y1 = box
    accent = _hex_to_rgb(palette["accent"])
    glow = _hex_to_rgb(palette["glow"])
    name = effect.lower()
    if "mist" in name or "glow" in name:
        for _ in range(8):
            mx = rng.randint(x0, x1 - 80)
            my = rng.randint(y0 + 20, y1 - 20)
            draw.ellipse((mx, my, mx + rng.randint(70, 180), my + rng.randint(28, 64)), fill=(*glow, 28))
    if "particle" in name or "stardust" in name or "light" in name:
        for _ in range(32):
            px = rng.randint(x0 + 10, x1 - 10)
            py = rng.randint(y0 + 10, y1 - 10)
            r = rng.randint(1, 4)
            draw.ellipse((px - r, py - r, px + r, py + r), fill=(*glow, 190))
    if "plant" in name:
        for _ in range(6):
            sx = rng.randint(x0 + 20, x1 - 40)
            sy = y1 - rng.randint(30, 80)
            draw.arc((sx - 10, sy - 42, sx + 14, sy + 12), 190, 340, fill=(*accent, 150), width=3)
    if "energy" in name or "aurora" in name:
        for _ in range(3):
            start_x = rng.randint(x0 + 20, x0 + 90)
            start_y = rng.randint(y0 + 40, y1 - 90)
            points = []
            for step in range(6):
                points.append((start_x + step * rng.randint(28, 40), start_y + rng.randint(-20, 20)))
            draw.line(points, fill=(*accent, 120), width=6, joint="curve")


def _draw_accessory_icon(draw, box, label, palette):
    x0, y0, x1, y1 = box
    cx = (x0 + x1) // 2
    cy = y0 + 34
    accent = _hex_to_rgb(palette["accent"])
    glow = _hex_to_rgb(palette["glow"])
    text = label.lower()
    if "crystal" in text:
        draw.polygon([(cx, cy - 18), (cx + 16, cy), (cx, cy + 24), (cx - 16, cy)], fill=(*glow, 180), outline=(*accent, 220))
    elif "lantern" in text:
        draw.rounded_rectangle((cx - 14, cy - 12, cx + 14, cy + 18), radius=8, outline=(*accent, 220), width=3)
        draw.line((cx, cy - 24, cx, cy - 12), fill=(*glow, 220), width=3)
    elif "book" in text or "cards" in text:
        draw.rounded_rectangle((cx - 18, cy - 16, cx + 18, cy + 14), radius=6, outline=(*accent, 220), width=3)
        draw.line((cx, cy - 16, cx, cy + 14), fill=(*glow, 200), width=2)
    elif "hands" in text:
        draw.ellipse((cx - 22, cy - 10, cx - 2, cy + 12), outline=(*accent, 220), width=3)
        draw.ellipse((cx + 2, cy - 10, cx + 22, cy + 12), outline=(*accent, 220), width=3)
    elif "face" in text:
        draw.ellipse((cx - 18, cy - 20, cx + 18, cy + 16), outline=(*accent, 220), width=3)
        draw.arc((cx - 8, cy - 2, cx + 8, cy + 10), 10, 170, fill=(*glow, 220), width=2)
    else:
        draw.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill=(*glow, 140))
        draw.line((cx, cy - 20, cx, cy + 20), fill=(*accent, 220), width=3)


def _draw_prompt_scene(draw, box, prompt, palette, rng):
    x0, y0, x1, y1 = box
    width = x1 - x0
    height = y1 - y0
    lower = prompt.lower()
    accent = _hex_to_rgb(palette["accent"])
    glow = _hex_to_rgb(palette["glow"])
    deep = _hex_to_rgb(palette["background"][0])
    mid = _hex_to_rgb(palette["background"][1])
    warm = (255, 179, 96)
    shadow = tuple(max(0, int(value * 0.45)) for value in deep)

    sky_top = _blend_colors(palette["background"][0], "#120f2a", 0.35)
    sky_bottom = _blend_colors(palette["background"][1], palette["accent"], 0.22)
    for row in range(height):
        blend = row / max(1, height - 1)
        color = tuple(int(sky_top[index] + (sky_bottom[index] - sky_top[index]) * blend) for index in range(3))
        draw.line((x0, y0 + row, x1, y0 + row), fill=(*color, 255))

    is_sunset = any(term in lower for term in ("sunset", "sunrise", "dawn", "golden hour", "sun"))
    has_water = any(term in lower for term in ("lake", "water", "ocean", "river", "sea"))
    has_forest = any(term in lower for term in ("forest", "trees", "woods"))
    has_mountains = any(term in lower for term in ("mountain", "mountains", "peak", "peaks"))
    has_city = any(term in lower for term in ("city", "cityscape", "skyline"))
    has_flowers = any(term in lower for term in ("flower", "flowers", "petals", "garden"))

    for _ in range(4 if is_sunset else 3):
        cloud_w = rng.randint(max(90, width // 8), max(180, width // 4))
        cloud_h = rng.randint(36, 72)
        cloud_x = rng.randint(x0 - 20, x1 - cloud_w + 20)
        cloud_y = rng.randint(y0 + 24, y0 + max(60, height // 3))
        cloud_fill = (*warm, 22) if is_sunset else (*glow, 16)
        cursor = cloud_x
        for puff in range(rng.randint(4, 6)):
            puff_w = int(cloud_w * rng.uniform(0.18, 0.32))
            puff_h = int(cloud_h * rng.uniform(0.72, 1.12))
            puff_x = cursor + rng.randint(-8, 12)
            puff_y = cloud_y + rng.randint(-10, 10)
            draw.ellipse((puff_x, puff_y, puff_x + puff_w, puff_y + puff_h), fill=cloud_fill)
            cursor += int(puff_w * rng.uniform(0.45, 0.7))

    horizon = y0 + int(height * (0.64 if not has_water else 0.58))
    if is_sunset:
        glow_y = horizon - 32
        for band in range(7):
            radius_y = 18 + band * 14
            alpha = max(18, 86 - band * 10)
            draw.ellipse((x0 + int(width * 0.18), glow_y - radius_y, x1 - int(width * 0.18), glow_y + radius_y), fill=(*warm, alpha))

    if has_mountains or is_sunset:
        ridge_count = 3 if width >= 900 else 2
        ridge_palette = [
            (*shadow, 150),
            (*tuple(max(0, min(255, c + 20)) for c in shadow), 190),
            (*deep, 228),
        ]
        for ridge in range(ridge_count):
            points = [(x0, y1)]
            steps = 6
            for step in range(steps + 1):
                px = x0 + int(width * step / steps)
                peak_y = horizon - rng.randint(26 + ridge * 18, 120 + ridge * 32)
                points.append((px, peak_y))
            points.append((x1, y1))
            draw.polygon(points, fill=ridge_palette[min(ridge, len(ridge_palette) - 1)])

    if has_water:
        draw.rectangle((x0, horizon, x1, y1), fill=(*_blend_colors(palette["background"][1], "#5132a7", 0.55), 220))
        for wave in range(8):
            wy = horizon + 14 + wave * 12
            draw.arc((x0 + 20, wy, x1 - 20, wy + 28), 0, 180, fill=(*glow, 90), width=2)
        draw.rectangle((x0, horizon - 3, x1, horizon + 3), fill=(*glow, 70))
        reflection_width = max(60, width // 8)
        reflection_x = x0 + int(width * 0.7)
        for band in range(8):
            band_y = horizon + 10 + band * 18
            band_w = max(20, reflection_width - band * 6)
            draw.ellipse((reflection_x - band_w, band_y, reflection_x + band_w, band_y + 16), fill=(*warm, max(18, 72 - band * 6)))
        for shore in range(10):
            sx = x0 + shore * (width // 9) + rng.randint(-14, 14)
            sy = horizon + rng.randint(-4, 6)
            draw.arc((sx - 24, sy - 6, sx + 26, sy + 10), 0, 180, fill=(*shadow, 120), width=2)

    if any(term in lower for term in ("moon", "moonlit", "night")):
        moon_x = x0 + int(width * 0.74)
        moon_y = y0 + int(height * 0.18)
        r = max(26, width // 12)
        draw.ellipse((moon_x - r, moon_y - r, moon_x + r, moon_y + r), fill=(255, 244, 209, 220))
        draw.ellipse((moon_x - r - 18, moon_y - r - 18, moon_x + r + 18, moon_y + r + 18), outline=(*glow, 70), width=4)

    if is_sunset:
        sun_x = x0 + int(width * 0.72)
        sun_y = y0 + int(height * 0.22)
        r = max(30, width // 10)
        draw.ellipse((sun_x - r, sun_y - r, sun_x + r, sun_y + r), fill=(255, 193, 108, 180))
        draw.ellipse((sun_x - r - 22, sun_y - r - 22, sun_x + r + 22, sun_y + r + 22), fill=(255, 193, 108, 24))
        if has_water:
            draw.rectangle((sun_x - 3, horizon - 8, sun_x + 3, y1), fill=(*warm, 34))

    if has_forest:
        draw.rectangle((x0, y1 - 92, x1, y1), fill=(18, 26, 24, 118))
        tree_count = 7 if width >= 900 else 5
        for index in range(tree_count):
            base_x = x0 + int((index + rng.uniform(0.15, 0.85)) * width / tree_count)
            trunk_h = rng.randint(int(height * 0.18), int(height * 0.38))
            trunk_w = rng.randint(7, 14)
            trunk_top = y1 - trunk_h - 18
            draw.rounded_rectangle((base_x, trunk_top, base_x + trunk_w, y1 - 18), radius=4, fill=(66, 49, 39, 228))
            canopy_layers = rng.randint(2, 4)
            for layer in range(canopy_layers):
                layer_w = rng.randint(40, 88) - layer * 8
                layer_h = rng.randint(22, 38)
                layer_y = trunk_top - layer * rng.randint(10, 18) - layer_h
                layer_x = base_x - layer_w // 2 + trunk_w // 2 + rng.randint(-6, 6)
                draw.ellipse((layer_x, layer_y, layer_x + layer_w, layer_y + layer_h), fill=(74, 128, 106, 132))
                if layer < canopy_layers - 1:
                    draw.ellipse((layer_x + 10, layer_y - 8, layer_x + layer_w - 6, layer_y + layer_h - 8), fill=(90, 150, 122, 96))
        for _ in range(5):
            pine_x = rng.randint(x0 + 10, x1 - 46)
            pine_h = rng.randint(74, 150)
            tiers = rng.randint(2, 3)
            for tier in range(tiers):
                tier_y = y1 - 24 - tier * (pine_h // 4)
                half_w = max(14, 28 - tier * 6)
                top_y = tier_y - pine_h // (tiers + 1)
                draw.polygon(
                    [(pine_x, tier_y), (pine_x + half_w, top_y), (pine_x + half_w * 2, tier_y)],
                    fill=(18, 32, 26, 230),
                )

    if has_flowers:
        for _ in range(14):
            fx = rng.randint(x0 + 20, x1 - 20)
            fy = rng.randint(y0 + int(height * 0.35), y1 - 26)
            stem_top = fy - rng.randint(16, 44)
            draw.line((fx, fy, fx, stem_top), fill=(90, 170, 118, 160), width=3)
            for angle in range(0, 360, 72):
                ox = int(10 * __import__("math").cos(__import__("math").radians(angle)))
                oy = int(10 * __import__("math").sin(__import__("math").radians(angle)))
                draw.ellipse((fx + ox - 7, stem_top + oy - 7, fx + ox + 7, stem_top + oy + 7), fill=(*glow, 135))
            draw.ellipse((fx - 6, stem_top - 6, fx + 6, stem_top + 6), fill=(*accent, 210))

    if has_mountains:
        for index in range(4):
            mx = x0 + index * (width // 4)
            peak = y0 + rng.randint(int(height * 0.18), int(height * 0.36))
            draw.polygon([(mx, y1 - 24), (mx + width // 8, peak), (mx + width // 4, y1 - 24)], fill=(*deep, 180))

    if has_city:
        base = y1 - 24
        cursor = x0 + 20
        while cursor < x1 - 20:
            building_w = rng.randint(22, 52)
            building_h = rng.randint(int(height * 0.18), int(height * 0.54))
            draw.rounded_rectangle((cursor, base - building_h, cursor + building_w, base), radius=4, fill=(*deep, 200))
            for row in range(3, building_h // 18):
                wy = base - building_h + row * 16
                for col in range(1, building_w // 12):
                    wx = cursor + col * 10
                    draw.rectangle((wx, wy, wx + 4, wy + 6), fill=(255, 218, 132, 120))
            cursor += building_w + rng.randint(6, 16)

    if not has_city:
        draw.rectangle((x0, y1 - 20, x1, y1), fill=(*shadow, 180))
        for rock in range(4):
            rock_x = x0 + rock * (width // 4) + rng.randint(-10, 24)
            rock_y = y1 - rng.randint(26, 48)
            rock_w = rng.randint(24, 56)
            rock_h = rng.randint(12, 26)
            draw.ellipse((rock_x, rock_y, rock_x + rock_w, rock_y + rock_h), fill=(*shadow, 170))

    for _ in range(24):
        px = rng.randint(x0 + 10, x1 - 10)
        py = rng.randint(y0 + 10, y1 - 10)
        r = rng.randint(1, 3)
        draw.ellipse((px - r, py - r, px + r, py + r), fill=(*glow, 160))


def _add_painterly_finish(canvas, box, prompt, palette, rng):
    if Image is None or ImageDraw is None or ImageFilter is None:
        return canvas

    x0, y0, x1, y1 = box
    width = x1 - x0
    height = y1 - y0
    lower = prompt.lower()
    glow = _hex_to_rgb(palette["glow"])
    accent = _hex_to_rgb(palette["accent"])
    deep = _hex_to_rgb(palette["background"][0])
    warm = (255, 196, 128)

    paint_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    paint = ImageDraw.Draw(paint_layer, "RGBA")

    for _ in range(10):
        blob_w = rng.randint(max(80, width // 10), max(140, width // 4))
        blob_h = rng.randint(max(40, height // 18), max(90, height // 7))
        blob_x = rng.randint(x0 - 10, x1 - blob_w + 10)
        blob_y = rng.randint(y0 + 20, y1 - blob_h - 20)
        color = (*glow, rng.randint(10, 24)) if rng.random() > 0.5 else (*accent, rng.randint(10, 20))
        paint.ellipse((blob_x, blob_y, blob_x + blob_w, blob_y + blob_h), fill=color)

    if any(term in lower for term in ("moon", "moonlit", "night")):
        moon_x = x0 + int(width * 0.74)
        moon_y = y0 + int(height * 0.18)
        for ring in range(4):
            radius = max(50, width // 10) + ring * 26
            alpha = max(10, 38 - ring * 7)
            paint.ellipse((moon_x - radius, moon_y - radius, moon_x + radius, moon_y + radius), fill=(*glow, alpha))

    if any(term in lower for term in ("sunset", "sunrise", "dawn", "golden hour", "sun")):
        glow_y = y0 + int(height * 0.52)
        for band in range(6):
            band_h = 28 + band * 18
            alpha = max(10, 40 - band * 5)
            paint.ellipse((x0 + int(width * 0.12), glow_y - band_h, x1 - int(width * 0.12), glow_y + band_h), fill=(*warm, alpha))

    if any(term in lower for term in ("lake", "water", "ocean", "river", "sea")):
        water_y = y0 + int(height * 0.58)
        for sweep in range(10):
            start_x = x0 + rng.randint(20, width // 3)
            end_x = x1 - rng.randint(20, width // 4)
            sweep_y = water_y + sweep * rng.randint(10, 15)
            paint.arc((start_x, sweep_y, end_x, sweep_y + rng.randint(18, 34)), 4, 176, fill=(*warm, 22), width=3)

    if any(term in lower for term in ("forest", "trees", "woods")):
        mist_y = y1 - int(height * 0.28)
        for mist in range(6):
            mx = x0 + rng.randint(-20, width - 120)
            my = mist_y + rng.randint(-24, 24)
            mw = rng.randint(120, 240)
            mh = rng.randint(28, 62)
            paint.ellipse((mx, my, mx + mw, my + mh), fill=(*deep, rng.randint(24, 44)))

    paint_layer = paint_layer.filter(ImageFilter.GaussianBlur(radius=14))
    combined = Image.alpha_composite(canvas, paint_layer)

    glaze = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glaze_draw = ImageDraw.Draw(glaze, "RGBA")
    for _ in range(80):
        stroke_w = rng.randint(18, 54)
        stroke_h = rng.randint(8, 18)
        sx = rng.randint(x0, x1 - stroke_w)
        sy = rng.randint(y0, y1 - stroke_h)
        color = (*accent, rng.randint(3, 8)) if rng.random() > 0.55 else (*glow, rng.randint(3, 7))
        glaze_draw.rounded_rectangle((sx, sy, sx + stroke_w, sy + stroke_h), radius=stroke_h // 2, fill=color)
    glaze = glaze.filter(ImageFilter.GaussianBlur(radius=6))
    return Image.alpha_composite(combined, glaze)


def _draw_scene_caption(draw, box, profile, style, title_font, subtitle_font):
    x0, y0, x1, y1 = box
    caption_h = min(164, max(112, (y1 - y0) // 5))
    panel = (x0 + 22, y1 - caption_h - 18, x1 - 22, y1 - 18)
    glow = _hex_to_rgb(style["glow"])
    accent = _hex_to_rgb(style["accent"])
    draw.rounded_rectangle(panel, radius=22, fill=(10, 12, 18, 108), outline=(*glow, 76), width=2)
    headline_lines = _wrap_prompt_lines(profile["headline"], max_len=18, max_lines=2)
    sub_lines = _wrap_prompt_lines(profile["subheadline"], max_len=30, max_lines=1)
    draw.multiline_text((panel[0] + 20, panel[1] + 16), "\n".join(headline_lines), fill=style["text"], font=title_font, spacing=8)
    draw.multiline_text((panel[0] + 20, panel[1] + 82), "\n".join(sub_lines), fill=style["accent"], font=subtitle_font, spacing=6)
    badge_x = panel[0] + 20
    badge_y = panel[3] - 34
    for label in (profile.get("labels") or [])[:2]:
        chip_w = max(92, len(label) * 11)
        draw.rounded_rectangle((badge_x, badge_y, badge_x + chip_w, badge_y + 24), radius=12, fill=(*accent, 112), outline=(*glow, 90), width=1)
        draw.text((badge_x + 10, badge_y + 4), label.upper(), fill=style["text"], font=_safe_font(14, bold=False))
        badge_x += chip_w + 8


def _paste_rounded_image(canvas, image, box, radius=28):
    if image is None:
        return
    target_w = max(1, box[2] - box[0])
    target_h = max(1, box[3] - box[1])
    fitted = ImageOps.fit(image, (target_w, target_h), method=Image.Resampling.LANCZOS)
    mask = _rounded_mask((target_w, target_h), radius)
    layer = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    layer.paste(fitted.convert("RGBA"), (0, 0))
    layer.putalpha(mask)
    canvas.alpha_composite(layer, (box[0], box[1]))


def _draw_label_chips(draw, labels, origin, palette, font):
    if not labels:
        return
    accent = _hex_to_rgb(palette["accent"])
    glow = _hex_to_rgb(palette["glow"])
    x, y = origin
    for label in labels[:3]:
        chip_w = max(112, len(label) * 12)
        chip_h = 34
        draw.rounded_rectangle((x, y, x + chip_w, y + chip_h), radius=16, fill=(*accent, 78), outline=(*glow, 120), width=2)
        draw.text((x + 14, y + 8), label.upper(), fill=palette["text"], font=font)
        x += chip_w + 10


def _render_concept_layout(canvas, overlay, prompt, profile, style, rng, main_reference, title_font, subtitle_font, small_font):
    width, height = canvas.size
    overlay_draw = ImageDraw.Draw(overlay, "RGBA")
    draw = ImageDraw.Draw(canvas)
    accent = _hex_to_rgb(style["accent"])
    glow = _hex_to_rgb(style["glow"])
    deep = _hex_to_rgb(style["background"][0])
    text_color = style["text"]
    composition = profile.get("composition", "editorial")
    headline_lines = _wrap_prompt_lines(profile["headline"], max_len=18 if width < 1200 else 24, max_lines=2)
    sub_lines = _wrap_prompt_lines(profile["subheadline"], max_len=28 if width < 1200 else 34, max_lines=2)

    if composition == "product_mockup":
        hero_box = (int(width * 0.14), int(height * 0.16), int(width * 0.62), int(height * 0.76))
        side_box = (int(width * 0.68), int(height * 0.2), int(width * 0.88), int(height * 0.76))
        text_box = (int(width * 0.1), int(height * 0.8), int(width * 0.9), int(height * 0.92))
        overlay_draw.rounded_rectangle((int(width * 0.08), int(height * 0.09), int(width * 0.92), int(height * 0.92)), radius=38, fill=(10, 14, 20, 92), outline=(*glow, 145), width=3)
        overlay_draw.rounded_rectangle(hero_box, radius=32, fill=(16, 22, 30, 126), outline=(*glow, 126), width=3)
        overlay_draw.rounded_rectangle(side_box, radius=28, fill=(12, 18, 24, 116), outline=(*accent, 110), width=2)
        _draw_prompt_scene(overlay_draw, hero_box, prompt, style, rng)
        pedestal_y = hero_box[3] - 42
        overlay_draw.rounded_rectangle((hero_box[0] + 46, pedestal_y, hero_box[2] - 46, pedestal_y + 24), radius=12, fill=(*deep, 210), outline=(*accent, 110), width=2)
        if main_reference is not None:
            ref_box = (hero_box[0] + 58, hero_box[1] + 36, hero_box[2] - 58, hero_box[3] - 86)
            _paste_rounded_image(canvas, main_reference, ref_box, radius=28)
        for idx, label in enumerate(profile.get("labels") or ["Premium", "Local", "Offline"]):
            item_y = side_box[1] + 24 + idx * 94
            item_box = (side_box[0] + 18, item_y, side_box[2] - 18, item_y + 76)
            overlay_draw.rounded_rectangle(item_box, radius=18, fill=(255, 255, 255, 18), outline=(*glow, 90), width=2)
            draw.text((item_box[0] + 16, item_box[1] + 18), label.upper(), fill=text_color, font=small_font)
        overlay_draw.rounded_rectangle(text_box, radius=24, fill=(8, 12, 18, 172))
        draw.multiline_text((text_box[0] + 20, text_box[1] + 18), "\n".join(headline_lines), fill=text_color, font=title_font, spacing=10)
        draw.multiline_text((text_box[0] + 20, text_box[1] + 100), "\n".join(sub_lines), fill=style["accent"], font=subtitle_font, spacing=8)
        _draw_label_chips(draw, profile.get("labels"), (text_box[0] + 20, text_box[1] + 154), style, small_font)
        return canvas

    if composition == "story_frame":
        frame_box = (int(width * 0.08), int(height * 0.11), int(width * 0.92), int(height * 0.84))
        scene_box = (frame_box[0] + 24, frame_box[1] + 24, frame_box[2] - 24, frame_box[3] - 140)
        strip_y = frame_box[3] - 98
        overlay_draw.rounded_rectangle(frame_box, radius=30, fill=(12, 14, 20, 74), outline=(*glow, 140), width=3)
        overlay_draw.rounded_rectangle(scene_box, radius=24, fill=(0, 0, 0, 0), outline=(*accent, 80), width=2)
        _draw_prompt_scene(overlay_draw, scene_box, prompt, style, rng)
        if main_reference is not None:
            ref_box = (scene_box[0] + 28, scene_box[1] + 28, scene_box[0] + int((scene_box[2] - scene_box[0]) * 0.38), scene_box[1] + int((scene_box[3] - scene_box[1]) * 0.58))
            _paste_rounded_image(canvas, main_reference, ref_box, radius=24)
            overlay_draw.rounded_rectangle(ref_box, radius=24, outline=(*glow, 128), width=3)
        overlay_draw.rounded_rectangle((frame_box[0] + 18, strip_y, frame_box[2] - 18, frame_box[3] - 18), radius=20, fill=(8, 12, 18, 182))
        draw.multiline_text((frame_box[0] + 42, strip_y + 18), "\n".join(headline_lines), fill=text_color, font=title_font, spacing=10)
        draw.multiline_text((frame_box[0] + 42, strip_y + 100), "\n".join(sub_lines), fill=style["accent"], font=subtitle_font, spacing=8)
        _draw_label_chips(draw, profile.get("labels"), (frame_box[0] + 42, strip_y + 148), style, small_font)
        return canvas

    if composition == "luxury_editorial":
        left_box = (int(width * 0.08), int(height * 0.12), int(width * 0.48), int(height * 0.82))
        right_box = (int(width * 0.53), int(height * 0.12), int(width * 0.92), int(height * 0.82))
        overlay_draw.rounded_rectangle(left_box, radius=28, fill=(255, 255, 255, 18), outline=(*glow, 95), width=2)
        overlay_draw.rounded_rectangle(right_box, radius=28, fill=(10, 12, 18, 122), outline=(*accent, 110), width=2)
        if main_reference is not None:
            _paste_rounded_image(canvas, main_reference, (left_box[0] + 18, left_box[1] + 18, left_box[2] - 18, left_box[3] - 18), radius=24)
        else:
            _draw_prompt_scene(overlay_draw, left_box, prompt, style, rng)
        overlay_draw.rounded_rectangle((right_box[0] + 20, right_box[1] + 20, right_box[2] - 20, right_box[1] + 150), radius=20, fill=(*accent, 32))
        draw.multiline_text((right_box[0] + 28, right_box[1] + 36), "\n".join(headline_lines), fill=text_color, font=title_font, spacing=10)
        draw.multiline_text((right_box[0] + 28, right_box[1] + 150), "\n".join(sub_lines), fill=style["accent"], font=subtitle_font, spacing=8)
        _draw_label_chips(draw, profile.get("labels"), (right_box[0] + 28, right_box[1] + 214), style, small_font)
        quote_box = (right_box[0] + 24, right_box[1] + 300, right_box[2] - 24, right_box[1] + 430)
        overlay_draw.rounded_rectangle(quote_box, radius=22, fill=(255, 255, 255, 14), outline=(*glow, 84), width=2)
        quote_lines = _wrap_prompt_lines(profile.get("phrase") or "Quiet confidence in a local concept render.", max_len=28, max_lines=3)
        draw.multiline_text((quote_box[0] + 22, quote_box[1] + 22), "\n".join(quote_lines), fill=text_color, font=subtitle_font, spacing=8)
        return canvas

    scene_box = (int(width * 0.03), int(height * 0.03), int(width * 0.97), int(height * 0.97))
    _draw_prompt_scene(overlay_draw, scene_box, prompt, style, rng)
    if main_reference is not None:
        ref_box = (scene_box[0] + 28, scene_box[1] + 28, scene_box[0] + int((scene_box[2] - scene_box[0]) * 0.28), scene_box[1] + int((scene_box[3] - scene_box[1]) * 0.38))
        _paste_rounded_image(canvas, main_reference, ref_box, radius=24)
        overlay_draw.rounded_rectangle(ref_box, radius=24, outline=(*glow, 122), width=2)
    if composition == "fantasy_scene":
        if main_reference is not None:
            overlay_draw.rounded_rectangle(ref_box, radius=24, outline=(*glow, 110), width=2)
        canvas = _add_painterly_finish(canvas, scene_box, prompt, style, rng)
        return canvas

    overlay_draw.rounded_rectangle((int(width * 0.04), int(height * 0.04), int(width * 0.96), int(height * 0.96)), radius=34, outline=(*glow, 128), width=3)
    _draw_scene_caption(draw, scene_box, profile, style, _safe_font(42, bold=True), subtitle_font)
    return canvas


def _create_doll_subject(reference_path, size, palette, archetype):
    width, height = size
    subject = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(subject, "RGBA")
    colors = _subject_palette_from_reference(reference_path, palette)
    accent = _hex_to_rgb(palette["accent"])
    glow = _hex_to_rgb(palette["glow"])
    dark = colors["shadow"]
    shoulder_y = int(height * 0.42)
    waist_y = int(height * 0.58)
    base_y = int(height * 0.94)
    center_x = width // 2

    draw.ellipse((int(width * 0.26), int(height * 0.03), int(width * 0.74), int(height * 0.19)), fill=(*glow, 62))
    draw.rounded_rectangle((int(width * 0.3), int(height * 0.24), int(width * 0.7), int(height * 0.58)), radius=width // 8, fill=(*colors["secondary"], 30))
    draw.ellipse((int(width * 0.33), int(height * 0.3), int(width * 0.67), int(height * 0.46)), fill=(*dark, 110))
    draw.polygon(
        [
            (int(width * 0.34), shoulder_y),
            (int(width * 0.66), shoulder_y),
            (int(width * 0.86), base_y),
            (int(width * 0.14), base_y),
        ],
        fill=(*colors["primary"], 220),
    )
    draw.polygon(
        [
            (int(width * 0.38), shoulder_y + 8),
            (center_x, waist_y),
            (int(width * 0.62), shoulder_y + 8),
            (center_x, int(height * 0.5)),
        ],
        fill=(*colors["secondary"], 180),
    )
    draw.polygon(
        [
            (int(width * 0.2), int(height * 0.5)),
            (int(width * 0.32), int(height * 0.46)),
            (int(width * 0.38), int(height * 0.7)),
            (int(width * 0.27), int(height * 0.78)),
        ],
        fill=(*colors["primary"], 170),
    )
    draw.polygon(
        [
            (int(width * 0.8), int(height * 0.5)),
            (int(width * 0.68), int(height * 0.46)),
            (int(width * 0.62), int(height * 0.7)),
            (int(width * 0.73), int(height * 0.78)),
        ],
        fill=(*colors["primary"], 170),
    )
    for fold in range(7):
        x = int(width * (0.22 + fold * 0.08))
        draw.line((x, int(height * 0.5), x + rng_sign(fold) * 10, base_y), fill=(*dark, 84), width=3)

    if reference_path:
        face = _reference_portrait_image(reference_path, (int(width * 0.34), int(height * 0.28)), soften=True)
    else:
        face = None
    if face is not None:
        mask = Image.new("L", face.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, face.size[0], face.size[1]), fill=245)
        mask_draw.rounded_rectangle((int(face.size[0] * 0.18), int(face.size[1] * 0.56), int(face.size[0] * 0.82), face.size[1]), radius=max(10, face.size[0] // 8), fill=255)
        face_rgba = face.convert("RGBA")
        face_rgba.putalpha(mask)
        face_x = (width - face.width) // 2
        face_y = int(height * 0.11)
        subject.alpha_composite(face_rgba, (face_x, face_y))
        draw.rounded_rectangle((face_x - 10, face_y + int(face.height * 0.68), face_x + face.width + 10, face_y + face.height + 18), radius=18, fill=(*colors["secondary"], 70))

    if "oracle" in archetype.lower() or "celestial" in archetype.lower() or "moon" in archetype.lower():
        draw.arc((int(width * 0.26), int(height * 0.02), int(width * 0.74), int(height * 0.24)), 18, 162, fill=(*accent, 230), width=5)
    elif "guardian" in archetype.lower() or "druid" in archetype.lower():
        for leaf in range(5):
            lx = int(width * (0.36 + leaf * 0.07))
            draw.ellipse((lx, int(height * 0.08), lx + 22, int(height * 0.15)), fill=(96, 170, 120, 180))
    elif "water" in archetype.lower():
        for wave in range(3):
            draw.arc((int(width * 0.3), int(height * (0.1 + wave * 0.03)), int(width * 0.7), int(height * (0.24 + wave * 0.03))), 200, 340, fill=(*accent, 210), width=3)
    return subject


def rng_sign(value):
    return -1 if value % 2 else 1


def generate_local_art(prompt, output_path, style_name="Cinematic Poster", size=(1024, 1024), references=None):
    if Image is None or ImageDraw is None or ImageFilter is None or ImageOps is None:
        raise RuntimeError("Pillow is required for Image Studio, but it is not available in this build.")

    references = list(references or [])
    width, height = size
    profile = _extract_prompt_profile(prompt)
    style = _palette_for_profile(IMAGE_STYLES.get(style_name, IMAGE_STYLES["Cinematic Poster"]), profile)
    seed = _prompt_seed(prompt, style_name)
    import random

    rng = random.Random(seed)
    canvas = Image.new("RGB", (width, height), _hex_to_rgb(style["background"][0]))
    pixels = canvas.load()
    top_color = style["background"][0]
    bottom_color = style["background"][1]
    for y in range(height):
        blend = y / max(1, height - 1)
        line_color = _blend_colors(top_color, bottom_color, blend)
        for x in range(width):
            jitter = rng.randint(-6, 6)
            pixels[x, y] = tuple(max(0, min(255, value + jitter)) for value in line_color)

    draw = ImageDraw.Draw(canvas, "RGBA")

    ambient_shapes = 14 if profile["mode"] != "collector" else 6
    if profile.get("composition") == "fantasy_scene":
        ambient_shapes = 4
    elif profile.get("composition") in {"luxury_editorial", "story_frame"}:
        ambient_shapes = 8
    for _ in range(ambient_shapes):
        x0 = rng.randint(-width // 8, width)
        y0 = rng.randint(-height // 8, height)
        w = rng.randint(width // 8, width // 2)
        h = rng.randint(height // 8, height // 2)
        fill = _blend_colors(style["accent"], style["glow"], rng.random())
        alpha = rng.randint(24, 76) if profile["mode"] != "collector" else rng.randint(10, 26)
        if rng.random() > 0.45:
            draw.ellipse((x0, y0, x0 + w, y0 + h), fill=(*fill, alpha))
        else:
            draw.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=rng.randint(18, 42), fill=(*fill, alpha))

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay, "RGBA")
    title_font = _safe_font(58 if width < 1200 else 66, bold=True)
    subtitle_font = _safe_font(24, bold=False)
    small_font = _safe_font(18, bold=False)
    label_font = _safe_font(22, bold=True)

    main_reference = None
    if references:
        main_reference = _reference_anchor_image(references[0], (int(width * 0.48), int(height * 0.62)), style)

    if profile["mode"] == "collector":
        package = (int(width * 0.07), int(height * 0.06), int(width * 0.93), int(height * 0.94))
        inner = (package[0] + 24, package[1] + 24, package[2] - 24, package[3] - 24)
        subject_box = (int(width * 0.12), int(height * 0.18), int(width * 0.59), int(height * 0.81))
        accessory_col = (int(width * 0.64), int(height * 0.22), int(width * 0.88), int(height * 0.81))
        phrase_box = (int(width * 0.12), int(height * 0.83), int(width * 0.88), int(height * 0.91))

        overlay_draw.rounded_rectangle(package, radius=48, fill=(8, 12, 20, 166), outline=(*_hex_to_rgb(style["glow"]), 200), width=4)
        overlay_draw.rounded_rectangle(inner, radius=40, fill=(255, 255, 255, 16), outline=(*_hex_to_rgb(style["accent"]), 90), width=2)
        overlay_draw.rounded_rectangle(subject_box, radius=34, fill=(14, 18, 28, 112), outline=(*_hex_to_rgb(style["glow"]), 138), width=3)
        overlay_draw.rounded_rectangle(accessory_col, radius=28, fill=(12, 18, 24, 110), outline=(*_hex_to_rgb(style["accent"]), 120), width=2)
        overlay_draw.rounded_rectangle(phrase_box, radius=24, fill=(10, 14, 18, 128), outline=(*_hex_to_rgb(style["glow"]), 96), width=2)

        _draw_environment_scene(overlay_draw, subject_box, profile["environment"], style, rng)
        _draw_magic_effects(overlay_draw, subject_box, profile["effect"], style, rng)

        base_y = subject_box[3] - int((subject_box[3] - subject_box[1]) * 0.12)
        overlay_draw.rounded_rectangle(
            (subject_box[0] + 46, base_y, subject_box[2] - 46, base_y + 36),
            radius=18,
            fill=(*_hex_to_rgb(style["background"][0]), 220),
            outline=(*_hex_to_rgb(style["accent"]), 100),
            width=2,
        )

        doll = _create_doll_subject(references[0] if references else None, (subject_box[2] - subject_box[0] - 86, subject_box[3] - subject_box[1] - 74), style, profile["archetype"])
        canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay)
        doll_x = subject_box[0] + ((subject_box[2] - subject_box[0]) - doll.width) // 2
        doll_y = subject_box[1] + 28
        canvas.alpha_composite(doll, (doll_x, doll_y))

        draw = ImageDraw.Draw(canvas)
        title_lines = _wrap_prompt_lines(profile["headline"], max_len=22, max_lines=1)
        archetype_lines = _wrap_prompt_lines(profile["archetype"], max_len=24, max_lines=2)
        env_lines = _wrap_prompt_lines(profile["environment"], max_len=22, max_lines=2)
        phrase_lines = _wrap_prompt_lines(profile["phrase"], max_len=42 if width >= 1000 else 32, max_lines=3)

        draw.text((int(width * 0.12), int(height * 0.1)), title_lines[0], fill=style["text"], font=title_font)
        draw.text((int(width * 0.12), int(height * 0.145)), "Fantasy Collector Figure", fill=style["accent"], font=subtitle_font)
        draw.text((subject_box[0] + 18, subject_box[1] + 16), "\n".join(archetype_lines), fill=style["glow"], font=label_font, spacing=8)
        draw.text((subject_box[0] + 18, subject_box[1] + 64), "\n".join(env_lines), fill=style["text"], font=small_font, spacing=6)
        draw.multiline_text((phrase_box[0] + 22, phrase_box[1] + 16), "\n".join(phrase_lines), fill=style["text"], font=subtitle_font, spacing=8)

        accessory_gap = 18
        accessory_height = int((accessory_col[3] - accessory_col[1] - accessory_gap * 5) / 4)
        for index, label in enumerate(profile["accessories"] or ["Crystal", "Lantern", "Book", "Alternate Face"]):
            y0 = accessory_col[1] + accessory_gap + index * (accessory_height + accessory_gap)
            box = (accessory_col[0] + 18, y0, accessory_col[2] - 18, y0 + accessory_height)
            overlay_draw = ImageDraw.Draw(canvas, "RGBA")
            overlay_draw.rounded_rectangle(box, radius=20, fill=(255, 255, 255, 16), outline=(*_hex_to_rgb(style["glow"]), 110), width=2)
            _draw_accessory_icon(overlay_draw, box, label, style)
            draw.text((box[0] + 16, box[3] - 28), label.upper(), fill=style["text"], font=small_font)
        draw.text((accessory_col[0] + 18, accessory_col[1] - 28), profile["effect"].upper(), fill=style["accent"], font=small_font)
    else:
        canvas = canvas.convert("RGBA")
        canvas = _render_concept_layout(canvas, overlay, prompt, profile, style, rng, main_reference, title_font, subtitle_font, small_font)
        canvas = Image.alpha_composite(canvas, overlay)

    final = canvas.convert("RGB").filter(ImageFilter.SMOOTH_MORE)
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    final.save(output_path, format="PNG", optimize=True)
    return output_path


def _base64_image_from_path(image_path):
    return base64.b64encode(Path(image_path).read_bytes()).decode("utf-8")


def detect_sd_backend(base_url):
    base_url = str(base_url or "").strip().rstrip("/")
    if not base_url:
        return False, "No backend URL configured.", None
    request = urllib.request.Request(
        f"{base_url}/sdapi/v1/options",
        headers={"Content-Type": "application/json"},
        method="GET",
    )
    try:
        with safe_urlopen(request, timeout=3) as response:
            if response.status == 200:
                return True, f"Connected to local Stable Diffusion backend at {base_url}", "sdapi"
    except Exception:
        pass
    request = urllib.request.Request(
        f"{base_url}/system_stats",
        headers={"Content-Type": "application/json"},
        method="GET",
    )
    try:
        with safe_urlopen(request, timeout=3) as response:
            if response.status == 200:
                return True, f"Connected to local ComfyUI backend at {base_url}", "comfyui"
            return False, f"Backend at {base_url} did not expose a supported image API.", None
    except Exception as exc:
        return False, f"Backend not available at {base_url}: {exc}", None


def comfyui_queue_status(base_url):
    base_url = str(base_url or "").strip().rstrip("/")
    if not base_url:
        return False, 0, 0
    request = urllib.request.Request(
        f"{base_url}/queue",
        headers={"Content-Type": "application/json"},
        method="GET",
    )
    try:
        with safe_urlopen(request, timeout=3) as response:
            body = json.loads(response.read().decode("utf-8"))
        running = body.get("queue_running") or []
        pending = body.get("queue_pending") or []
        return True, len(running), len(pending)
    except Exception:
        return False, 0, 0


def generate_sd_image(prompt, output_path, base_url, size=(1024, 1024), references=None, style_name="Cinematic Poster"):
    base_url = str(base_url or "").strip().rstrip("/")
    available, detail, backend_kind = detect_sd_backend(base_url)
    if not available:
        raise RuntimeError(detail)
    width, height = size
    references = list(references or [])
    if backend_kind == "comfyui":
        if references:
            raise RuntimeError("ComfyUI is available for text-to-image in this build, but reference-based transforms still require an SD API backend.")
        helper = LocalImageBackend(Path.home() / ".offline-ai-workstation" / "image-backend")
        return helper.comfyui_generate(prompt, output_path, size=size, style_name=style_name)
    endpoint = "/sdapi/v1/img2img" if references else "/sdapi/v1/txt2img"
    payload = {
        "prompt": prompt,
        "negative_prompt": "blurry, low quality, deformed, extra limbs, watermark, text overlay, cropped",
        "steps": 24,
        "cfg_scale": 7,
        "width": width,
        "height": height,
        "sampler_name": "Euler a",
    }
    if references:
        payload["init_images"] = [_base64_image_from_path(references[0])]
        payload["denoising_strength"] = 0.5

    request = urllib.request.Request(
        f"{base_url}{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with safe_urlopen(request, timeout=600) as response:
        body = json.loads(response.read().decode("utf-8"))

    images = body.get("images") or []
    if not images:
        raise RuntimeError("The local image backend returned no images.")
    image_bytes = base64.b64decode(images[0])
    output_path = Path(output_path)
    ensure_dir(output_path.parent)
    output_path.write_bytes(image_bytes)
    return output_path


def requires_real_image_backend(prompt, references=None):
    prompt = str(prompt or "")
    lower = prompt.lower()
    has_references = bool(list(references or []))
    likeness_terms = (
        "based on the person",
        "based on the uploaded image",
        "uploaded image",
        "preserving their facial features",
        "preserving facial features",
        "preserving their likeness",
        "preserve their likeness",
        "transform the person",
        "turn the person into",
        "photo transformation",
    )
    identity_terms = (
        "person in the image",
        "same person",
        "their face",
        "their hair",
        "their likeness",
        "facial features",
        "uploaded photo",
        "from the photo",
    )
    return has_references and (
        any(term in lower for term in likeness_terms)
        or ("doll-like" in lower and any(term in lower for term in identity_terms))
    )


class InstallWorker:
    def __init__(self, sys_info, selected_models, callbacks):
        self.sys_info = sys_info
        self.models = selected_models
        self.on_status = callbacks["status"]
        self.on_progress = callbacks["progress"]
        self.on_step = callbacks["step"]
        self.on_done = callbacks["done"]
        self.on_error = callbacks["error"]
        self.cancelled = False
        self._tmp = tempfile.mkdtemp(prefix="offline-ai-workstation-")

    def run(self):
        try:
            self._prepare_workspace()
            if not self.cancelled:
                self._download_models()
            if not self.cancelled:
                self._copy_presets()
            if not self.cancelled:
                self._prepare_runtime()
            if not self.cancelled:
                self._prepare_image_backend()
            if not self.cancelled:
                self._prepare_ocr()
            if not self.cancelled:
                self._prepare_launchers()
            if not self.cancelled:
                self.on_done()
        except Exception as exc:
            self.on_error(str(exc))
        finally:
            shutil.rmtree(self._tmp, ignore_errors=True)

    def _prepare_workspace(self):
        self.on_step("PREPARING WORKSPACE", "Creating your standalone app folders...")
        for key in ("app_home", "models_dir", "presets_dir", "runtime_dir", "image_backend_dir", "ocr_dir", "knowledge_dir", "images_dir"):
            self.sys_info[key].mkdir(parents=True, exist_ok=True)
        self.on_status(f"Workspace ready at {self.sys_info['app_home']}")
        self.on_progress(0.12)

    def _download_models(self):
        models_dir = self.sys_info["models_dir"]
        total = len(self.models)
        base_progress = 0.12
        model_budget = 0.76

        for i, model in enumerate(self.models):
            if self.cancelled:
                return
            dest = get_model_target_path(models_dir, model)
            if dest.exists():
                self.on_status(f"Already have {model['name']} - skipping")
                self.on_progress(base_progress + model_budget * (i + 1) / total)
                continue

            self.on_step(
                f"DOWNLOADING MODEL {i + 1}/{total}",
                f"{model['name']} - {model['size_gb']} GB",
            )
            self._download_file(
                model["url"],
                dest,
                label=model["name"],
                overall_start=base_progress + model_budget * i / total,
                overall_end=base_progress + model_budget * (i + 1) / total,
            )

    def _copy_presets(self):
        self.on_step("INSTALLING PRESETS", "Copying your model profiles...")
        presets_dir = self.sys_info["presets_dir"]
        presets_dir.mkdir(parents=True, exist_ok=True)
        copied = 0
        skipped = 0
        for base in get_preset_search_roots():
            preset_src = base / "model-presets"
            if not preset_src.exists():
                continue
            for preset in preset_src.glob("*.json"):
                dest = presets_dir / preset.name
                if dest.exists():
                    skipped += 1
                    continue
                shutil.copy2(str(preset), str(dest))
                copied += 1
            if copied or skipped:
                break
        if copied == 0 and skipped == 0:
            self.on_status("No preset bundle found.")
        else:
            self.on_status(f"Installed {copied} preset file(s), kept {skipped} existing")
        self.on_progress(0.93)

    def _prepare_runtime(self):
        self.on_step("PREPARING RUNTIME", "Checking for a bundled llama.cpp server...")
        copied, skipped = copy_bundled_runtime(self.sys_info["runtime_dir"])
        backend = LocalRuntimeBackend(self.sys_info["runtime_dir"], port=RUNTIME_PORT)
        if copied:
            self.on_status(f"Installed {copied} runtime file(s), kept {skipped} existing. {backend.status_summary()}")
        elif skipped:
            self.on_status(f"Kept {skipped} existing runtime file(s). {backend.status_summary()}")
        else:
            self.on_status(backend.status_summary())
        self.on_progress(0.99)

    def _prepare_image_backend(self):
        self.on_step("PREPARING IMAGE BACKEND", "Checking for a bundled local image engine...")
        copied, skipped = copy_bundled_image_backend(self.sys_info["image_backend_dir"])
        backend = LocalImageBackend(self.sys_info["image_backend_dir"])
        if copied:
            self.on_status(f"Installed {copied} image backend item(s), kept {skipped} existing. {backend.status_summary()}")
        elif skipped:
            self.on_status(f"Kept {skipped} existing image backend item(s). {backend.status_summary()}")
        else:
            self.on_status(backend.status_summary())
        self.on_progress(0.993)

    def _prepare_ocr(self):
        self.on_step("PREPARING OCR", "Installing bundled offline OCR for images and scanned files...")
        try:
            result = install_bundled_ocr(self.sys_info["ocr_dir"])
        except Exception as exc:
            self.on_status(f"OCR setup skipped: {exc}")
            self.on_progress(0.996)
            return

        if result == "ready":
            self.on_status(f"OCR ready at {self.sys_info['ocr_dir']}")
        elif result == "partial":
            self.on_status("OCR engine installed, but English language data was missing.")
        else:
            self.on_status("Bundled OCR assets were not found. Image OCR will stay unavailable.")
        self.on_progress(0.996)

    def _prepare_launchers(self):
        self.on_step("PREPARING LAUNCHERS", "Writing one-click workspace launchers...")
        app_home = self.sys_info["app_home"]
        exe_path = None
        if getattr(__import__("sys"), "frozen", False):
            import sys

            exe_path = Path(sys.executable).resolve()
        if os.name == "nt":
            launch_bat = app_home / "Open-Offline-AI-Workspace.bat"
            content = [
                "@echo off",
                "setlocal",
                f"cd /d \"{app_home}\"",
            ]
            if exe_path and exe_path.exists():
                content.append(f"start \"\" \"{exe_path}\"")
            else:
                content.append("echo Workspace executable not found in this build.")
                content.append("pause")
            launch_bat.write_text("\n".join(content) + "\n", encoding="utf-8")
            launcher_path = launch_bat
        else:
            launch_script = app_home / "Open-Offline-AI-Workspace.command"
            content = [
                "#!/bin/bash",
                f"cd \"{app_home}\"",
            ]
            if exe_path and exe_path.exists():
                content.append(f"\"{exe_path}\" >/dev/null 2>&1 &")
            else:
                content.append("echo \"Workspace executable not found in this build.\"")
                content.append("read -r -p \"Press Enter to close...\"")
            launch_script.write_text("\n".join(content) + "\n", encoding="utf-8")
            launch_script.chmod(0o755)
            launcher_path = launch_script
        self.on_status(f"Workspace launcher ready at {launcher_path}")
        self.on_progress(0.998)

    def _download_file(self, url, dest, label="", overall_start=0.0, overall_end=1.0):
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp_dest = Path(str(dest) + ".part")
        start_time = time.time()

        try:
            request = urllib.request.Request(url, headers=HTTP_HEADERS)
            with safe_urlopen(request, timeout=60) as response, open(tmp_dest, "wb") as out_file:
                total_size = int(response.headers.get("Content-Length") or 0)
                downloaded = 0
                while True:
                    if self.cancelled:
                        raise Exception("Cancelled")
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    elapsed = max(time.time() - start_time, 0.001)
                    speed_mb = downloaded / elapsed / 1024 / 1024
                    if total_size > 0:
                        frac = downloaded / total_size
                        self.on_progress(overall_start + (overall_end - overall_start) * frac)
                        self.on_status(
                            f"{label}: {downloaded / 1024 / 1024:.0f} / {total_size / 1024 / 1024:.0f} MB  ({speed_mb:.1f} MB/s)"
                        )
                    else:
                        self.on_status(f"{label}: {downloaded / 1024 / 1024:.0f} MB  ({speed_mb:.1f} MB/s)")
            tmp_dest.rename(dest)
        except HTTPError as exc:
            if tmp_dest.exists():
                tmp_dest.unlink()
            raise Exception(f"HTTP error {exc.code} while downloading {label or url}")
        except (URLError, socket.timeout) as exc:
            if tmp_dest.exists():
                tmp_dest.unlink()
            raise Exception(f"Network error while downloading {label or url}: {exc}")
        except Exception:
            if tmp_dest.exists():
                tmp_dest.unlink()
            raise


class StandaloneApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.minsize(760, 760)
        w, h = 820, 820
        self.geometry(f"{w}x{h}+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

        self.sys_info = detect_system()
        self.backend = LocalRuntimeBackend(self.sys_info["runtime_dir"], port=RUNTIME_PORT)
        self.image_backend = LocalImageBackend(self.sys_info["image_backend_dir"])
        self.selected_tier = tk.StringVar(value="standard")
        self.selected_model = tk.StringVar(value="")
        self.worker = None
        self._current_frame = None
        self._knowledge_status = None
        self._knowledge_hint = None
        self._sidebar_visible = True
        self._models_expanded = False
        self._workspace_tab = "chat"
        self._active_session_id = None
        self._chat_sessions = []
        self._session_search = tk.StringVar(value="")
        self.settings = dict(DEFAULT_SETTINGS)
        self._session_buttons = []
        self._session_list_frame = None
        self._models_list_frame = None
        self._workspace_container = None
        self._sidebar_frame = None
        self._main_frame = None
        self._chat_log = None
        self._chat_entry = None
        self._workspace_status = None
        self._settings_vars = {}
        self._session_title_label = None
        self._session_meta_label = None
        self._model_assignment_label = None
        self._sidebar_toggle_button = None
        self._model_presets = {}
        self._current_view = "welcome"
        self._compact_layout = False
        self._compact_panel = None
        self._image_style_var = tk.StringVar(value=list(IMAGE_STYLES.keys())[0])
        self._image_size_var = tk.StringVar(value=recommended_image_size_label(self.sys_info))
        self._image_prompt_var = tk.StringVar(value="")
        self._image_backend_mode_var = tk.StringVar(value=self.settings.get("image_backend_mode", "auto"))
        self._image_backend_url_var = tk.StringVar(value=self.settings.get("image_backend_url", "http://127.0.0.1:7860"))
        self._image_status_var = tk.StringVar(value="Image Studio is ready. Use Concept Render for offline mockups, or connect a local image backend for photo transformations.")
        self._image_reference_paths = []
        self._image_preview_path = None
        self._image_preview_widget = None
        self._image_prompt_entry = None
        self._image_history_frame = None
        self._image_generated_files = []
        self._image_preview_handle = None
        self._generate_image_button = None
        self._image_backend_status = None
        self._image_backend_actions = None
        self._image_generation_thread = None
        self._image_generation_result = None
        self._image_generation_error = None
        self._image_generation_backend_available = False
        self._image_generation_backend_kind = None
        self._image_poll_after = None
        self._last_seen_generated_image = None
        self._expected_generated_image = None
        self._image_generation_started_at = None
        self._resize_after = None
        self._load_settings()
        self._image_backend_mode_var.set(self.settings.get("image_backend_mode", "auto"))
        self._image_backend_url_var.set(self.settings.get("image_backend_url", "http://127.0.0.1:7860"))
        self._apply_theme(self.settings.get("appearance", "dark"))
        self._load_model_presets()
        self._load_chat_sessions()
        self.bind("<Configure>", self._on_window_resize)
        if self.settings.get("open_workspace_on_launch", True) and self._has_existing_install():
            self._show_workspace()
        else:
            self._show_welcome()

    def _has_existing_install(self):
        models = discover_installed_models(self.sys_info["models_dir"])
        runtime_ready = self.backend.find_server_binary() is not None
        return bool(models) or runtime_ready

    def _status_badge(self, parent, text, color):
        badge = tk.Label(
            parent,
            text=text,
            font=FONT_LABEL,
            bg=C["surface"],
            fg=color,
            padx=14,
            pady=7,
            highlightthickness=1,
            highlightbackground=C["border"],
        )
        badge.pack(side="left", padx=(0, 8))
        return badge

    def _clear(self):
        if self._current_frame:
            self._current_frame.destroy()
        self._current_frame = tk.Frame(self, bg=C["bg"])
        self._current_frame.pack(fill="both", expand=True)
        return self._current_frame

    def _clear_scrollable(self):
        if self._current_frame:
            self._current_frame.destroy()

        shell = tk.Frame(self, bg=C["bg"])
        shell.pack(fill="both", expand=True)

        canvas = tk.Canvas(shell, bg=C["bg"], highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=C["bg"])

        content.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        window_id = canvas.create_window((0, 0), window=content, anchor="nw")

        def sync_width(event):
            canvas.itemconfigure(window_id, width=event.width)

        canvas.bind("<Configure>", sync_width)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def on_mousewheel(event):
            delta = -1 * int(event.delta / 120) if event.delta else 0
            if delta:
                canvas.yview_scroll(delta, "units")

        canvas.bind_all("<MouseWheel>", on_mousewheel)
        self._current_frame = shell
        return content

    def _apply_theme(self, appearance=None):
        theme_name = str(appearance or self.settings.get("appearance", "dark")).lower()
        if theme_name not in THEMES:
            theme_name = "dark"
        C.clear()
        C.update(THEMES[theme_name])
        self.settings["appearance"] = theme_name
        self.configure(bg=C["bg"])

    def _appearance_label(self):
        return "LIGHT MODE" if self.settings.get("appearance", "dark") == "dark" else "DARK MODE"

    def _toggle_theme(self):
        next_theme = "light" if self.settings.get("appearance", "dark") == "dark" else "dark"
        self._apply_theme(next_theme)
        self._save_settings()
        self._render_current_view()

    def _render_current_view(self):
        view = getattr(self, "_current_view", "welcome")
        if view == "workspace":
            self._show_workspace()
        elif view == "settings":
            self._show_settings()
        elif view == "done":
            self._show_done()
        elif view == "model_picker":
            self._show_model_picker()
        else:
            self._show_welcome()

    def _is_compact_layout(self, view=None):
        width = self.winfo_width() or self.winfo_reqwidth()
        active_view = view or getattr(self, "_current_view", "welcome")
        breakpoint = WORKSPACE_COMPACT_BREAKPOINT if active_view == "workspace" else WELCOME_COMPACT_BREAKPOINT
        return width < breakpoint

    def _on_window_resize(self, event):
        if event.widget is not self:
            return
        if self._resize_after:
            self.after_cancel(self._resize_after)
        self._resize_after = self.after(120, self._apply_responsive_layout)

    def _apply_responsive_layout(self):
        self._resize_after = None
        compact = self._is_compact_layout(getattr(self, "_current_view", "welcome"))
        if compact == self._compact_layout:
            return
        self._compact_layout = compact
        if not compact:
            self._compact_panel = None
        if getattr(self, "_current_view", "") in {"welcome", "workspace", "settings", "model_picker", "done"}:
            self._render_current_view()

    def _toggle_compact_panel(self, panel_name):
        self._compact_panel = None if self._compact_panel == panel_name else panel_name
        if getattr(self, "_current_view", "") == "workspace":
            self._show_workspace()

    def _header(self, parent, title, subtitle=None):
        tk.Frame(parent, bg=C["cyan"], height=2).pack(fill="x")
        tk.Frame(parent, bg=C["bg"], height=22 if self._compact_layout else 30).pack(fill="x")
        tk.Label(parent, text=title, font=FONT_TITLE, bg=C["bg"], fg=C["white"]).pack()
        if subtitle:
            tk.Label(parent, text=subtitle, font=FONT_SMALL, bg=C["bg"], fg=C["muted"]).pack(pady=(6, 0))
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", pady=(16 if self._compact_layout else 18))

    def _btn(self, parent, text, command, color=None, width=24):
        button = tk.Button(
            parent,
            text=text,
            command=command,
            font=FONT_BUTTON,
            bg=color or C["cyan"],
            fg=C["button_text"],
            relief="flat",
            bd=0,
            padx=26,
            pady=12,
            width=width,
            cursor="hand2",
            activebackground=color or C["cyan"],
            activeforeground=C["button_text"],
            highlightthickness=1,
            highlightbackground=C["border"],
        )
        button.pack(pady=6)
        return button

    def _open_payment_link(self):
        if PAYMENT_LINK.startswith("http://") or PAYMENT_LINK.startswith("https://"):
            webbrowser.open(PAYMENT_LINK)

    def _show_welcome(self):
        self._current_view = "welcome"
        self._compact_layout = self._is_compact_layout("welcome")
        f = self._clear_scrollable()
        self._header(f, "OFFLINE AI", "Private workstation installer and product overview")
        installed_models = self._get_installed_models()
        has_existing_install = self._has_existing_install()
        content_pad = 18 if self._compact_layout else 36
        hero_wrap = 480 if self._compact_layout else 640
        card_wrap = 440 if self._compact_layout else 280

        info_frame = tk.Frame(f, bg=C["bg"])
        info_frame.pack(padx=content_pad, pady=(4, 12), anchor="w")
        for label, value in (
            ("OS", self.sys_info["os"]),
            ("RAM", f"{self.sys_info['ram_gb']} GB"),
            ("FREE DISK", f"{self.sys_info['disk_free_gb']} GB"),
        ):
            card = tk.Frame(info_frame, bg=C["surface"], highlightthickness=1, highlightbackground=C["border"])
            if self._compact_layout:
                card.pack(fill="x", padx=0, pady=4, ipadx=18, ipady=10)
            else:
                card.pack(side="left", padx=(0, 10), ipadx=18, ipady=10)
            tk.Label(card, text=label, font=FONT_LABEL, bg=C["surface"], fg=C["muted"]).pack(anchor="w", padx=12)
            tk.Label(card, text=value, font=FONT_METRIC, bg=C["surface"], fg=C["cyan"]).pack(anchor="w", padx=12, pady=(2, 0))

        hero = tk.Frame(f, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        hero.pack(fill="x", padx=content_pad, pady=(2, 14))
        hero_inner = tk.Frame(hero, bg=C["card"])
        hero_inner.pack(fill="x", padx=22, pady=22)
        eyebrow = tk.Frame(hero_inner, bg=C["card"])
        eyebrow.pack(fill="x", pady=(0, 12))
        tk.Label(
            eyebrow,
            text="PRIVATE LOCAL AI WORKSPACE",
            font=FONT_LABEL,
            bg=C["card"],
            fg=C["cyan"],
        ).pack(anchor="w")
        tk.Label(
            hero_inner,
            text="Install once. Work privately. Run chat, knowledge, and image tools on the machine in front of you.",
            font=("Georgia", 20 if self._compact_layout else 24, "bold"),
            bg=C["card"],
            fg=C["white"],
            wraplength=hero_wrap,
            justify="left",
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(
            hero_inner,
            text=SALES_PROMISE,
            font=FONT_BODY,
            bg=C["card"],
            fg=C["green"],
            wraplength=hero_wrap,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))
        tk.Label(
            hero_inner,
            text="Built for operators, consultants, internal teams, and client work that needs privacy, ownership, and an install flow that feels like a finished product.",
            font=FONT_SMALL,
            bg=C["card"],
            fg=C["muted"],
            wraplength=hero_wrap,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))
        tk.Label(
            hero_inner,
            text="Standard Knowledge Base, local chat, bundled runtime, OCR, and Image Studio are all part of the workstation experience.",
            font=FONT_SMALL,
            bg=C["card"],
            fg=C["cyan"],
            wraplength=hero_wrap,
            justify="left",
        ).pack(anchor="w", pady=(0, 18))

        quick_actions = tk.Frame(f, bg=C["bg"])
        quick_actions.pack(fill="x", padx=content_pad, pady=(0, 10))
        top_actions = tk.Frame(quick_actions, bg=C["bg"])
        top_actions.pack(fill="x", pady=(0, 8))
        tk.Button(
            top_actions,
            text=f"SWITCH TO {self._appearance_label()}",
            command=self._toggle_theme,
            font=FONT_BUTTON_SMALL,
            bg=C["surface"],
            fg=C["cyan"],
            relief="flat",
            bd=0,
            padx=14,
            pady=8,
            cursor="hand2",
        ).pack(side="right" if not self._compact_layout else "top", anchor="e")
        if has_existing_install:
            tk.Label(
                quick_actions,
                text=f"Installed now: {len(installed_models)} local model(s)",
                font=FONT_LABEL,
                bg=C["bg"],
                fg=C["green"],
            ).pack()
            action_row = tk.Frame(quick_actions, bg=C["bg"])
            action_row.pack(pady=(6, 0))
            open_button = tk.Button(
                action_row,
                text="OPEN WORKSPACE",
                command=self._show_workspace,
                font=FONT_BUTTON,
                bg=C["green"],
                fg=C["button_text"],
                relief="flat",
                bd=0,
                padx=18,
                pady=8,
                width=22,
                cursor="hand2",
            )
            more_button = tk.Button(
                action_row,
                text="ADD MORE MODELS",
                command=self._show_model_picker,
                font=FONT_BUTTON,
                bg=C["cyan"],
                fg=C["button_text"],
                relief="flat",
                bd=0,
                padx=18,
                pady=8,
                width=22,
                cursor="hand2",
            )
            if self._compact_layout:
                open_button.pack(fill="x", padx=6, pady=4)
                more_button.pack(fill="x", padx=6, pady=4)
            else:
                open_button.pack(side="left", padx=6)
                more_button.pack(side="left", padx=6)
        else:
            tk.Button(
                quick_actions,
                text="START INSTALL / CHOOSE MODELS",
                command=self._show_model_picker,
                font=FONT_BUTTON,
                bg=C["cyan"],
                fg=C["button_text"],
                relief="flat",
                bd=0,
                padx=18,
                pady=8,
                width=32,
                cursor="hand2",
            ).pack(fill="x" if self._compact_layout else "none")

        grid = tk.Frame(f, bg=C["bg"])
        grid.pack(fill="x", padx=content_pad, pady=(0, 8))

        capabilities = tk.Frame(grid, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        capabilities.pack(side="top" if self._compact_layout else "left", fill="both", expand=True, padx=(0, 0 if self._compact_layout else 8), pady=(0, 8 if self._compact_layout else 0))
        tk.Label(capabilities, text="CAPABILITIES", font=FONT_HEAD, bg=C["card"], fg=C["cyan"]).pack(anchor="w", padx=14, pady=(12, 6))
        for item in CAPABILITY_BLURBS:
            tk.Label(capabilities, text=item, font=FONT_SMALL, bg=C["card"], fg=C["text"], wraplength=card_wrap, justify="left").pack(anchor="w", padx=14, pady=3)

        included = tk.Frame(grid, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        included.pack(side="top" if self._compact_layout else "left", fill="both", expand=True, padx=(0 if self._compact_layout else 8, 0))
        tk.Label(included, text="WHAT'S INCLUDED", font=FONT_HEAD, bg=C["card"], fg=C["green"]).pack(anchor="w", padx=14, pady=(12, 6))
        for item in INCLUDED_ITEMS:
            tk.Label(included, text=item, font=FONT_SMALL, bg=C["card"], fg=C["text"], wraplength=card_wrap, justify="left").pack(anchor="w", padx=14, pady=3)

        use_cases = tk.Frame(f, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        use_cases.pack(fill="x", padx=content_pad, pady=(2, 10))
        tk.Label(use_cases, text="BEST FOR", font=FONT_HEAD, bg=C["card"], fg=C["cyan"]).pack(anchor="w", padx=14, pady=(12, 6))
        use_row = tk.Frame(use_cases, bg=C["card"])
        use_row.pack(fill="x", padx=10, pady=(0, 10))
        for idx, item in enumerate(USE_CASE_BLURBS):
            block = tk.Frame(use_row, bg=C["surface"], highlightthickness=1, highlightbackground=C["border"])
            if self._compact_layout:
                block.grid(row=idx, column=0, sticky="nsew", padx=4, pady=4)
            else:
                block.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=4, pady=4)
            tk.Label(
                block,
                text=item,
                font=FONT_SMALL,
                bg=C["surface"],
                fg=C["text"],
                wraplength=card_wrap,
                justify="left",
            ).pack(anchor="w", padx=12, pady=12)
        use_row.grid_columnconfigure(0, weight=1)
        if not self._compact_layout:
            use_row.grid_columnconfigure(1, weight=1)

        steps = tk.Frame(f, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        steps.pack(fill="x", padx=content_pad, pady=10)
        tk.Label(steps, text="HOW IT WORKS", font=FONT_HEAD, bg=C["card"], fg=C["amber"]).pack(anchor="w", padx=14, pady=(12, 6))
        for index, item in enumerate(INSTALL_STEPS, 1):
            tk.Label(steps, text=f"{index}. {item}", font=FONT_SMALL, bg=C["card"], fg=C["text"], wraplength=hero_wrap, justify="left").pack(anchor="w", padx=14, pady=3)

        sales = tk.Frame(f, bg=C["bg"])
        sales.pack(pady=(8, 2))
        tk.Label(
            sales,
            text="MANAGE YOUR WORKSTATION" if has_existing_install else "READY TO INSTALL",
            font=FONT_LABEL,
            bg=C["bg"],
            fg=C["white"],
        ).pack()
        tk.Label(
            sales,
            text=(
                f"Existing install detected with {len(installed_models)} local model(s). "
                "Open your workspace or run the installer again to add more models."
                if has_existing_install
                else "Choose your model pack now, or connect the payment button below to your checkout page."
            ),
            font=FONT_SMALL,
            bg=C["bg"],
            fg=C["muted"],
            wraplength=hero_wrap + 20,
            justify="center",
        ).pack(pady=(4, 8))
        if has_existing_install:
            self._btn(sales, "OPEN WORKSPACE", self._show_workspace, color=C["green"], width=28)
            self._btn(sales, "INSTALL / ADD MORE MODELS", self._show_model_picker, width=28)
        else:
            self._btn(sales, "START INSTALL / CHOOSE MODELS", self._show_model_picker, width=28)
        if PAYMENT_LINK.startswith("http://") or PAYMENT_LINK.startswith("https://"):
            self._btn(sales, "BUY NOW", self._open_payment_link, color=C["green"], width=28)
        else:
            tk.Label(
                sales,
                text="Add your checkout link by editing PAYMENT_LINK near the top of standalone_app.py",
                font=FONT_SMALL,
                bg=C["bg"],
                fg=C["amber"],
            ).pack(pady=(4, 0))

        if self.sys_info["ram_gb"] < 6:
            tk.Label(
                f,
                text=f"Low-memory machine detected ({self.sys_info['ram_gb']} GB). Starter models recommended.",
                font=FONT_SMALL,
                bg=C["bg"],
                fg=C["amber"],
            ).pack()
        tk.Label(
            f,
            text="Setup requires internet once for model download - about 2 to 15 GB depending on the selected pack.",
            font=FONT_SMALL,
            bg=C["bg"],
            fg=C["muted"],
        ).pack(pady=(6, 0))

    def _show_model_picker(self):
        self._current_view = "model_picker"
        f = self._clear_scrollable()
        self._header(f, "CHOOSE YOUR MODELS", "Pick the set that matches your RAM")
        ram = self.sys_info["ram_gb"]
        tiers = [
            ("starter", "STARTER", "3 models - about 4 GB download - 4GB+ RAM", C["green"], ram >= 4),
            ("standard", "STANDARD", "8 models + standard Knowledge Base - about 10 GB download - 8GB+ RAM", C["cyan"], ram >= 8),
            ("pro", "PRO", "12 models - about 22 GB download - 16GB+ RAM", C["amber"], ram >= 16),
        ]
        default = "starter"
        if ram >= 16:
            default = "pro"
        elif ram >= 8:
            default = "standard"
        self.selected_tier.set(default)

        for value, label, desc, color, fits in tiers:
            row = tk.Frame(f, bg=C["card"] if fits else C["surface"], highlightthickness=1, highlightbackground=C["border"])
            row.pack(fill="x", padx=40, pady=3, ipady=8)
            tk.Radiobutton(
                row,
                variable=self.selected_tier,
                value=value,
                text=f"  {label}",
                bg=row["bg"],
                fg=color if fits else C["muted"],
                selectcolor=C["card"],
                activebackground=row["bg"],
                font=("Georgia", 13, "bold"),
                state="normal" if fits else "disabled",
            ).pack(side="left", padx=12)
            tk.Label(row, text=desc, font=FONT_SMALL, bg=row["bg"], fg=C["muted"]).pack(side="left")

        controls = tk.Frame(f, bg=C["bg"])
        controls.pack(pady=18)
        tk.Button(controls, text="<- BACK", command=self._show_welcome, font=FONT_SMALL,
                  bg=C["surface"], fg=C["muted"], relief="flat", padx=16, pady=8).pack(side="left", padx=8)
        tk.Button(controls, text="START INSTALL ->", command=self._start_install, font=FONT_BUTTON,
                  bg=C["cyan"], fg=C["button_text"], relief="flat", padx=24, pady=8).pack(side="left", padx=8)

    def _start_install(self):
        models = TIER_MODELS[self.selected_tier.get()]
        f = self._clear()
        tk.Frame(f, bg=C["cyan"], height=3).pack(fill="x")
        tk.Frame(f, bg=C["bg"], height=24).pack()
        self._step_label = tk.Label(f, text="STARTING...", font=FONT_HEAD, bg=C["bg"], fg=C["cyan"])
        self._step_label.pack(pady=(0, 2))
        self._step_sub = tk.Label(f, text="", font=FONT_SMALL, bg=C["bg"], fg=C["muted"])
        self._step_sub.pack()
        tk.Frame(f, bg=C["border"], height=1).pack(fill="x", padx=40, pady=12)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.Horizontal.TProgressbar", troughcolor=C["surface"], background=C["cyan"])
        self._pbar = ttk.Progressbar(f, style="Dark.Horizontal.TProgressbar", orient="horizontal", length=560, mode="determinate")
        self._pbar.pack(padx=40, pady=4)
        self._pct_label = tk.Label(f, text="0%", font=("Courier", 9, "bold"), bg=C["bg"], fg=C["cyan"])
        self._pct_label.pack()

        log_frame = tk.Frame(f, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        log_frame.pack(fill="x", padx=40, pady=8)
        self._log = tk.Text(log_frame, height=10, font=("Courier", 9), bg=C["card"], fg=C["muted"], bd=0, wrap="word")
        self._log.pack(fill="x", padx=8, pady=8)
        self._log.configure(state="disabled")

        tk.Button(f, text="CANCEL", command=self._cancel, font=FONT_SMALL, bg=C["surface"], fg=C["muted"], relief="flat",
                  padx=16, pady=6).pack()

        callbacks = {
            "status": self._cb_status,
            "progress": self._cb_progress,
            "step": self._cb_step,
            "done": self._cb_done,
            "error": self._cb_error,
        }
        self.worker = InstallWorker(self.sys_info, models, callbacks)
        threading.Thread(target=self.worker.run, daemon=True).start()

    def _log_write(self, msg):
        self._log.configure(state="normal")
        self._log.insert("end", f"  {msg}\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _cb_status(self, msg):
        self.after(0, lambda: self._log_write(msg))

    def _cb_progress(self, val):
        def update():
            pct = int(val * 100)
            self._pbar["value"] = pct
            self._pct_label.config(text=f"{pct}%")
        self.after(0, update)

    def _cb_step(self, label, sub):
        def update():
            self._step_label.config(text=label)
            self._step_sub.config(text=sub)
            self._log_write(f"-- {label}: {sub}")
        self.after(0, update)

    def _cb_done(self):
        self.after(0, self._show_done)

    def _cb_error(self, msg):
        self.after(0, lambda: self._show_error(msg))

    def _cancel(self):
        if self.worker:
            self.worker.cancelled = True
        self._show_welcome()

    def _show_done(self):
        self._current_view = "done"
        f = self._clear_scrollable()
        tk.Frame(f, bg=C["green"], height=2).pack(fill="x")
        tk.Frame(f, bg=C["bg"], height=42).pack()
        tk.Label(f, text="READY", font=("Georgia", 18, "bold"), bg=C["bg"], fg=C["green"]).pack()
        tk.Label(f, text="Your workstation is live.", font=FONT_TITLE, bg=C["bg"], fg=C["white"]).pack(pady=(4, 2))
        tk.Label(f, text="Local models, bundled runtime, and the workspace are installed and ready to open.", font=FONT_BODY, bg=C["bg"], fg=C["muted"]).pack()
        tk.Frame(f, bg=C["border"], height=1).pack(fill="x", padx=60, pady=24)
        for i, step in enumerate(
            [
                "Open Workspace to browse models, chats, and Image Studio",
                "Start the local runtime for the model you want to use",
                "Import files into Knowledge Base and work fully local",
            ],
            1,
        ):
            tk.Label(f, text=f"  {i}.  {step}", font=FONT_BODY, bg=C["bg"], fg=C["text"]).pack(anchor="w", padx=80)
        self._btn(f, "OPEN WORKSPACE", self._show_workspace, color=C["green"], width=20)
        tk.Button(f, text="SETTINGS", command=self._show_settings, font=FONT_SMALL, bg=C["surface"], fg=C["cyan"],
                  relief="flat", padx=16, pady=8).pack(pady=4)
        tk.Button(f, text="CLOSE", command=self.destroy, font=FONT_SMALL, bg=C["surface"], fg=C["muted"],
                  relief="flat", padx=16, pady=8).pack(pady=6)

    def _show_settings(self):
        self._current_view = "settings"
        f = self._clear_scrollable()
        self._header(f, "SETTINGS", "Default model and runtime behavior")

        models = self._get_installed_models()
        model_choices = {"Automatic first available model": ""}
        for model in models:
            model_choices[f"{model['name']} ({model['size_gb']} GB)"] = str(model["path"])

        current_model = self.settings.get("startup_model_path", "")
        current_label = next((label for label, value in model_choices.items() if value == current_model), "Automatic first available model")

        self._settings_vars = {
            "startup_model": tk.StringVar(value=current_label),
            "auto_start_runtime": tk.BooleanVar(value=bool(self.settings.get("auto_start_runtime", False))),
            "auto_start_image_backend": tk.BooleanVar(value=bool(self.settings.get("auto_start_image_backend", False))),
            "open_workspace_on_launch": tk.BooleanVar(value=bool(self.settings.get("open_workspace_on_launch", True))),
            "collapse_models_by_default": tk.BooleanVar(value=bool(self.settings.get("collapse_models_by_default", True))),
            "appearance": tk.StringVar(value=self.settings.get("appearance", "dark").title()),
            "image_backend_mode": tk.StringVar(value=str(self.settings.get("image_backend_mode", "auto")).title()),
            "image_backend_url": tk.StringVar(value=str(self.settings.get("image_backend_url", "http://127.0.0.1:7860"))),
        }

        card = tk.Frame(f, bg=C["card"], bd=1, relief="solid")
        card.pack(fill="x", padx=40, pady=(8, 12))
        tk.Label(card, text="DEFAULT MODEL", font=FONT_HEAD, bg=C["card"], fg=C["cyan"]).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(card, text="Choose which model new chats should prefer when available.", font=FONT_SMALL, bg=C["card"], fg=C["muted"]).pack(anchor="w", padx=16, pady=(0, 8))
        model_menu = tk.OptionMenu(card, self._settings_vars["startup_model"], *model_choices.keys())
        model_menu.config(font=("Courier", 10), bg=C["surface"], fg=C["text"], activebackground=C["surface"], activeforeground=C["cyan"], relief="flat", highlightthickness=0)
        model_menu["menu"].config(font=("Courier", 10), bg=C["surface"], fg=C["text"])
        model_menu.pack(anchor="w", padx=16, pady=(0, 14))

        options = tk.Frame(f, bg=C["card"], bd=1, relief="solid")
        options.pack(fill="x", padx=40, pady=8)
        tk.Label(options, text="RUNTIME BEHAVIOR", font=FONT_HEAD, bg=C["card"], fg=C["green"]).pack(anchor="w", padx=16, pady=(14, 8))

        for key, label in (
            ("auto_start_runtime", "Auto-start runtime when opening the workspace"),
            ("auto_start_image_backend", "Auto-start image backend when opening Image Studio"),
            ("open_workspace_on_launch", "Open workspace immediately on launch if install exists"),
            ("collapse_models_by_default", "Keep the model picker collapsed by default"),
        ):
            tk.Checkbutton(
                options,
                text=label,
                variable=self._settings_vars[key],
                font=("Courier", 10),
                bg=C["card"],
                fg=C["text"],
                activebackground=C["card"],
                activeforeground=C["cyan"],
                selectcolor=C["surface"],
            ).pack(anchor="w", padx=16, pady=4)

        appearance = tk.Frame(f, bg=C["card"], bd=1, relief="solid")
        appearance.pack(fill="x", padx=40, pady=8)
        tk.Label(appearance, text="APPEARANCE", font=FONT_HEAD, bg=C["card"], fg=C["cyan"]).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(appearance, text="Choose the interface style for the installer and workspace.", font=FONT_SMALL, bg=C["card"], fg=C["muted"]).pack(anchor="w", padx=16, pady=(0, 8))
        for label in ("Dark", "Light"):
            tk.Radiobutton(
                appearance,
                text=f"{label} mode",
                variable=self._settings_vars["appearance"],
                value=label,
                font=("Courier", 10),
                bg=C["card"],
                fg=C["text"],
                activebackground=C["card"],
                activeforeground=C["cyan"],
                selectcolor=C["surface"],
            ).pack(anchor="w", padx=16, pady=4)

        image_backend = tk.Frame(f, bg=C["card"], bd=1, relief="solid")
        image_backend.pack(fill="x", padx=40, pady=8)
        tk.Label(image_backend, text="IMAGE BACKEND", font=FONT_HEAD, bg=C["card"], fg=C["amber"]).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(image_backend, text="Use a real local Stable Diffusion-compatible backend when available, or keep the concept renderer as fallback.", font=FONT_SMALL, bg=C["card"], fg=C["muted"], wraplength=620, justify="left").pack(anchor="w", padx=16, pady=(0, 8))
        for label in ("Auto", "Backend", "Concept"):
            tk.Radiobutton(
                image_backend,
                text=(
                    "Auto detect backend, otherwise use concept renderer"
                    if label == "Auto"
                    else "Require real local image backend"
                    if label == "Backend"
                    else "Use concept renderer only"
                ),
                variable=self._settings_vars["image_backend_mode"],
                value=label,
                font=("Courier", 10),
                bg=C["card"],
                fg=C["text"],
                activebackground=C["card"],
                activeforeground=C["cyan"],
                selectcolor=C["surface"],
            ).pack(anchor="w", padx=16, pady=4)
        tk.Label(image_backend, text="Backend URL", font=FONT_SMALL, bg=C["card"], fg=C["muted"]).pack(anchor="w", padx=16, pady=(10, 2))
        backend_entry = tk.Entry(image_backend, textvariable=self._settings_vars["image_backend_url"], font=("Courier", 10), bg=C["surface"], fg=C["text"], insertbackground=C["cyan"], relief="flat")
        backend_entry.pack(fill="x", padx=16, pady=(0, 14), ipady=7)

        controls = tk.Frame(f, bg=C["bg"])
        controls.pack(pady=18)
        tk.Button(controls, text="BACK", command=self._show_workspace if self._has_existing_install() else self._show_welcome, font=FONT_SMALL,
                  bg=C["surface"], fg=C["muted"], relief="flat", padx=16, pady=8).pack(side="left", padx=8)
        tk.Button(controls, text="SAVE SETTINGS", command=lambda: self._save_settings_from_form(model_choices), font=("Courier", 11, "bold"),
                  bg=C["green"], fg=C["button_text"], relief="flat", padx=20, pady=8).pack(side="left", padx=8)

    def _save_settings_from_form(self, model_choices):
        selected_label = self._settings_vars["startup_model"].get()
        self.settings["startup_model_path"] = model_choices.get(selected_label, "")
        self.settings["auto_start_runtime"] = bool(self._settings_vars["auto_start_runtime"].get())
        self.settings["auto_start_image_backend"] = bool(self._settings_vars["auto_start_image_backend"].get())
        self.settings["open_workspace_on_launch"] = bool(self._settings_vars["open_workspace_on_launch"].get())
        self.settings["collapse_models_by_default"] = bool(self._settings_vars["collapse_models_by_default"].get())
        self._apply_theme(str(self._settings_vars["appearance"].get()).lower())
        self.settings["image_backend_mode"] = str(self._settings_vars["image_backend_mode"].get()).lower()
        self.settings["image_backend_url"] = str(self._settings_vars["image_backend_url"].get()).strip()
        self._image_backend_mode_var.set(self.settings["image_backend_mode"])
        self._image_backend_url_var.set(self.settings["image_backend_url"])
        self._models_expanded = not self.settings["collapse_models_by_default"]
        self._save_settings()
        if self._workspace_status:
            self._workspace_status.config(text="Settings saved.")
        self._show_workspace() if self._has_existing_install() else self._show_welcome()

    def _get_installed_models(self):
        return discover_installed_models(self.sys_info["models_dir"])

    def _load_settings(self):
        self.sys_info["app_home"].mkdir(parents=True, exist_ok=True)
        settings = dict(DEFAULT_SETTINGS)
        settings_file = self.sys_info["settings_file"]
        if settings_file.exists():
            try:
                loaded = json.loads(settings_file.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    settings.update(loaded)
            except Exception:
                pass
        self.settings = settings
        self._models_expanded = not self.settings.get("collapse_models_by_default", True)

    def _save_settings(self):
        self.sys_info["app_home"].mkdir(parents=True, exist_ok=True)
        self.sys_info["settings_file"].write_text(json.dumps(self.settings, indent=2), encoding="utf-8")

    def _preferred_startup_model(self):
        model_path = self.settings.get("startup_model_path", "")
        if model_path and Path(model_path).exists():
            return model_path
        models = self._get_installed_models()
        return str(models[0]["path"]) if models else ""

    def _load_model_presets(self):
        presets = {}
        presets_dir = self.sys_info["presets_dir"]
        if presets_dir.exists():
            for preset_file in sorted(presets_dir.glob("*.json")):
                try:
                    payload = json.loads(preset_file.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if not isinstance(payload, dict):
                    continue
                model_name = str(payload.get("model", "")).strip()
                if not model_name:
                    continue
                for key in {model_name.lower(), Path(model_name).stem.lower()}:
                    presets[key] = payload
        self._model_presets = presets

    def _preset_for_model_path(self, model_path):
        if not model_path:
            return dict(DEFAULT_MODEL_PRESET)

        path = Path(model_path)
        for key in (path.name.lower(), path.stem.lower()):
            preset = self._model_presets.get(key)
            if preset:
                merged = dict(DEFAULT_MODEL_PRESET)
                merged.update(preset)
                return merged

        for model in MODELS:
            if model["filename"].lower() == path.name.lower():
                merged = dict(DEFAULT_MODEL_PRESET)
                merged.update({"name": model["name"], "note": model["desc"]})
                return merged

        return dict(DEFAULT_MODEL_PRESET)

    def _model_capability_text(self, model_path):
        preset = self._preset_for_model_path(model_path)
        note = str(preset.get("note", "")).strip()
        return note or "Local model ready for general offline assistance."

    def _build_system_prompt(self, model_path, knowledge_context):
        preset = self._preset_for_model_path(model_path)
        system_prompt = str(preset.get("systemPrompt") or DEFAULT_MODEL_PRESET["systemPrompt"]).strip()
        if knowledge_context:
            system_prompt = (
                f"{system_prompt} "
                "Prefer the supplied local knowledge base excerpts when answering. "
                "Do not claim to have read documents that were not provided in the prompt."
            )
        return system_prompt

    def _load_chat_sessions(self):
        self.sys_info["app_home"].mkdir(parents=True, exist_ok=True)
        session_file = self.sys_info["sessions_file"]
        loaded_sessions = []
        active_id = None

        if session_file.exists():
            try:
                payload = json.loads(session_file.read_text(encoding="utf-8"))
                loaded_sessions = payload.get("sessions", [])
                active_id = payload.get("active_session_id")
            except Exception:
                loaded_sessions = []
                active_id = None

        normalized = []
        available_models = self._get_installed_models()
        fallback_model = str(available_models[0]["path"]) if available_models else ""
        for item in loaded_sessions:
            messages = item.get("messages", [])
            if not isinstance(messages, list):
                messages = []
            normalized.append(
                {
                    "id": item.get("id") or str(uuid4()),
                    "title": item.get("title") or "New Chat",
                    "model_path": item.get("model_path") or fallback_model,
                    "pinned": bool(item.get("pinned", False)),
                    "messages": [
                        {
                            "role": msg.get("role", "assistant"),
                            "content": msg.get("content", ""),
                            "timestamp": msg.get("timestamp") or message_timestamp(),
                        }
                        for msg in messages
                        if msg.get("content")
                    ],
                }
            )

        self._chat_sessions = normalized
        if not self._chat_sessions:
            session = self._create_session(save=False)
            active_id = session["id"]

        self._active_session_id = active_id if any(s["id"] == active_id for s in self._chat_sessions) else self._chat_sessions[0]["id"]
        self._save_chat_sessions()

    def _save_chat_sessions(self):
        self.sys_info["app_home"].mkdir(parents=True, exist_ok=True)
        payload = {
            "active_session_id": self._active_session_id,
            "sessions": self._chat_sessions,
        }
        self.sys_info["sessions_file"].write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _create_session(self, title="New Chat", model_path=None, save=True):
        if model_path is None:
            active = self._get_active_session()
            if active and active.get("model_path"):
                model_path = active["model_path"]
            else:
                models = self._get_installed_models()
                model_path = str(models[0]["path"]) if models else ""
        session = {
            "id": str(uuid4()),
            "title": title,
            "model_path": model_path,
            "pinned": False,
            "messages": [],
        }
        insert_at = 0
        while insert_at < len(self._chat_sessions) and self._chat_sessions[insert_at].get("pinned"):
            insert_at += 1
        self._chat_sessions.insert(insert_at, session)
        self._active_session_id = session["id"]
        if save:
            self._save_chat_sessions()
        return session

    def _get_active_session(self):
        for session in self._chat_sessions:
            if session["id"] == self._active_session_id:
                return session
        return self._chat_sessions[0] if self._chat_sessions else None

    def _new_chat(self):
        self._create_session()
        self._show_workspace()
        if self._chat_entry:
            self.after(50, lambda: self._chat_entry.focus_set())

    def _rename_active_chat(self):
        session = self._get_active_session()
        if not session:
            return
        new_name = simpledialog.askstring("Rename chat", "Chat name:", initialvalue=session["title"], parent=self)
        if not new_name:
            return
        session["title"] = new_name.strip() or session["title"]
        self._save_chat_sessions()
        self._show_workspace()

    def _delete_active_chat(self):
        session = self._get_active_session()
        if not session:
            return
        if not messagebox.askyesno("Delete chat", f"Delete '{session['title']}'?", parent=self):
            return
        self._chat_sessions = [item for item in self._chat_sessions if item["id"] != session["id"]]
        if not self._chat_sessions:
            self._create_session(save=False)
        self._active_session_id = self._chat_sessions[0]["id"]
        self._save_chat_sessions()
        self._show_workspace()

    def _toggle_pin_active_chat(self):
        session = self._get_active_session()
        if not session:
            return
        session["pinned"] = not session.get("pinned", False)
        self._chat_sessions.sort(key=lambda item: (not item.get("pinned", False), item["title"].lower()))
        self._save_chat_sessions()
        self._show_workspace()

    def _select_session(self, session_id):
        self._active_session_id = session_id
        self._save_chat_sessions()
        self._show_workspace()

    def _export_active_chat(self):
        session = self._get_active_session()
        if not session:
            return
        default_name = re.sub(r"[^A-Za-z0-9._-]+", "-", session["title"]).strip("-") or "chat-export"
        export_path = filedialog.asksaveasfilename(
            title="Export chat",
            defaultextension=".txt",
            initialfile=f"{default_name}.txt",
            filetypes=(
                ("Text file", "*.txt"),
                ("JSON file", "*.json"),
                ("All files", "*.*"),
            ),
        )
        if not export_path:
            return

        export_target = Path(export_path)
        model_name = Path(session["model_path"]).stem if session.get("model_path") else "No model assigned"
        if export_target.suffix.lower() == ".json":
            payload = {
                "title": session["title"],
                "model_path": session.get("model_path", ""),
                "model_name": model_name,
                "pinned": session.get("pinned", False),
                "messages": session["messages"],
            }
            export_target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        else:
            lines = [
                f"Title: {session['title']}",
                f"Model: {model_name}",
                f"Pinned: {'Yes' if session.get('pinned') else 'No'}",
                "",
            ]
            for message in session["messages"]:
                speaker = "You" if message["role"] == "user" else "Assistant"
                lines.append(f"{speaker}")
                lines.append(message["content"])
                lines.append("")
            export_target.write_text("\n".join(lines), encoding="utf-8")

        if self._workspace_status:
            self._workspace_status.config(text=f"Exported chat to {export_target}")

    def _filtered_sessions(self):
        query = self._session_search.get().strip().lower()
        sessions = list(self._chat_sessions)
        if not query:
            return sessions
        matches = []
        for session in sessions:
            haystack = [session["title"].lower()]
            haystack.extend(msg["content"].lower() for msg in session["messages"][-12:])
            if any(query in text for text in haystack):
                matches.append(session)
        return matches

    def _toggle_sidebar(self):
        self._sidebar_visible = not self._sidebar_visible
        self._show_workspace()

    def _toggle_models_panel(self):
        self._models_expanded = not self._models_expanded
        self._show_workspace()

    def _assign_model_to_active_session(self, model_path):
        session = self._get_active_session()
        if not session:
            return
        session["model_path"] = str(model_path)
        self.selected_model.set(str(model_path))
        self._save_chat_sessions()
        selected_name = Path(model_path).stem
        if self.backend.is_running():
            try:
                self._workspace_log(f"Switching runtime to {selected_name}...")
                self.backend.stop()
                preset = self._preset_for_model_path(model_path)
                self.backend.start(model_path, context_length=preset.get("contextLength"))
                if self._workspace_status:
                    self._workspace_status.config(text=f"Runtime switched to {selected_name}.")
            except Exception as exc:
                if self._workspace_status:
                    self._workspace_status.config(text=str(exc))
                self._workspace_log(f"Runtime switch error: {exc}")
        elif self._workspace_status:
            self._workspace_status.config(text=f"Selected {selected_name} for this chat.")
        self._show_workspace()

    def _append_session_message(self, role, content):
        session = self._get_active_session()
        if not session:
            return
        session["messages"].append({"role": role, "content": content, "timestamp": message_timestamp()})
        if role == "user" and (session["title"] == "New Chat" or not session["title"].strip()):
            session["title"] = suggest_chat_title(content)
        self._save_chat_sessions()

    def _conversation_messages_for_runtime(self, user_prompt, knowledge_context=""):
        session = self._get_active_session()
        history = session["messages"][-SESSION_HISTORY_LIMIT:] if session else []
        runtime_messages = list(history)
        if runtime_messages and runtime_messages[-1]["role"] == "user" and runtime_messages[-1]["content"] == user_prompt:
            if knowledge_context:
                runtime_messages[-1] = {
                    "role": "user",
                    "content": (
                        "Use the local document excerpts below when they are relevant. "
                        "If the excerpts do not answer the question, say so clearly and then help with general reasoning.\n\n"
                        f"{knowledge_context}\n\n"
                        f"User question: {user_prompt}"
                    ),
                }
        else:
            if knowledge_context:
                runtime_messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Use the local document excerpts below when they are relevant. "
                            "If the excerpts do not answer the question, say so clearly and then help with general reasoning.\n\n"
                            f"{knowledge_context}\n\n"
                            f"User question: {user_prompt}"
                        ),
                    }
                )
            else:
                runtime_messages.append({"role": "user", "content": user_prompt})
        return runtime_messages

    def _render_session_list(self, parent):
        sessions = self._filtered_sessions()
        if not sessions:
            tk.Label(parent, text="No chats match this search yet.", font=("Courier", 8), bg=C["card"], fg=C["muted"]).pack(anchor="w", padx=8, pady=6)
            return
        for session in sessions:
            is_active = session["id"] == self._active_session_id
            row = tk.Frame(
                parent,
                bg=C["surface"] if is_active else C["card"],
                highlightthickness=1,
                highlightbackground=C["cyan"] if is_active else C["border"],
                bd=0,
            )
            row.pack(fill="x", pady=4)
            title = session["title"]
            if session.get("pinned"):
                title = f"[PIN] {title}"
            tk.Button(
                row,
                text=title,
                command=lambda sid=session["id"]: self._select_session(sid),
                font=("Consolas", 10, "bold" if is_active else "normal"),
                bg=row["bg"],
                fg=C["cyan"] if is_active else C["text"],
                activebackground=row["bg"],
                activeforeground=C["cyan"],
                relief="flat",
                anchor="w",
                padx=10,
                pady=8,
            ).pack(fill="x")
            model_name = Path(session["model_path"]).stem if session.get("model_path") else "No model assigned"
            tk.Label(row, text=model_name, font=FONT_SMALL, bg=row["bg"], fg=C["muted"], anchor="w").pack(fill="x", padx=10, pady=(0, 8))

    def _refresh_session_list_view(self):
        if not self._session_list_frame:
            return
        for child in self._session_list_frame.winfo_children():
            child.destroy()
        self._render_session_list(self._session_list_frame)

    def _use_starter_prompt(self, prompt):
        if not self._chat_entry:
            return
        self._chat_entry.delete(0, "end")
        self._chat_entry.insert(0, prompt)
        self._chat_entry.focus_set()

    def _render_model_list(self, parent, models):
        active = self._get_active_session()
        active_model = active.get("model_path", "") if active else ""
        if not models:
            tk.Label(parent, text="No local models installed yet.", font=FONT_SMALL, bg=C["card"], fg=C["muted"]).pack(anchor="w", padx=12, pady=(0, 8))
            return
        for model in models:
            row = tk.Frame(parent, bg=C["card"])
            row.pack(fill="x", padx=8, pady=2)
            tk.Radiobutton(
                row,
                text=f"{model['name']} ({model['size_gb']} GB)",
                variable=self.selected_model,
                value=str(model["path"]),
                command=lambda p=str(model["path"]): self._assign_model_to_active_session(p),
                bg=C["card"],
                fg=C["text"],
                selectcolor=C["surface"],
                activebackground=C["card"],
                activeforeground=C["cyan"],
                font=("Courier", 9),
                anchor="w",
            ).pack(anchor="w")
            tk.Label(
                row,
                text=self._model_capability_text(model["path"]),
                font=("Courier", 8),
                bg=C["card"],
                fg=C["muted"],
                wraplength=240,
                justify="left",
                anchor="w",
            ).pack(anchor="w", padx=26, pady=(0, 6))
        self.selected_model.set(active_model)

    def _set_workspace_tab(self, tab_name):
        self._workspace_tab = tab_name
        self._show_workspace()
        if tab_name == "image":
            self._ensure_image_polling()

    def _generated_image_directories(self):
        directories = []
        primary_dir = self.sys_info["images_dir"]
        backend_saved_dir = self.sys_info["image_backend_dir"] / "saved-images"
        for folder in (primary_dir, backend_saved_dir):
            folder = Path(folder)
            if folder not in directories:
                directories.append(folder)
        return directories

    def _latest_generated_images(self, limit=6):
        files = []
        seen = set()
        for images_dir in self._generated_image_directories():
            ensure_dir(images_dir)
            for image_path in images_dir.glob("*.png"):
                resolved = str(image_path.resolve())
                if resolved in seen:
                    continue
                seen.add(resolved)
                files.append(image_path)
        files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return files[:limit]

    def _render_image_preview(self):
        if not self._image_preview_widget:
            return
        self._image_preview_widget.configure(image="", text="No image generated yet.")
        self._image_preview_widget.image = None
        preview_path = self._image_preview_path
        if not preview_path or not Path(preview_path).exists() or Image is None or ImageTk is None:
            return
        try:
            with Image.open(preview_path) as image:
                preview = image.copy()
            widget_width = max(720, self._image_preview_widget.winfo_width() - 24)
            widget_height = max(520, self._image_preview_widget.winfo_height() - 24)
            preview.thumbnail((widget_width, widget_height))
            photo = ImageTk.PhotoImage(preview)
            self._image_preview_widget.configure(image=photo, text="")
            self._image_preview_widget.image = photo
            self._image_preview_handle = photo
        except Exception as exc:
            self._image_preview_widget.configure(text=f"Preview unavailable: {exc}")
            self._image_preview_widget.image = None

    def _ensure_image_polling(self):
        if self._image_poll_after is not None:
            return
        self._image_poll_after = self.after(1500, self._poll_generated_images_folder)

    def _poll_generated_images_folder(self):
        self._image_poll_after = None
        if getattr(self, "_workspace_tab", "chat") != "image":
            return
        files = self._latest_generated_images(limit=12)
        if files:
            chosen = None
            if self._expected_generated_image:
                expected_path = Path(self._expected_generated_image)
                for image_path in files:
                    if image_path.name == expected_path.name or image_path.stem.startswith(expected_path.stem):
                        chosen = image_path
                        break
            if chosen is None and self._image_generation_started_at:
                for image_path in files:
                    try:
                        if image_path.stat().st_mtime >= self._image_generation_started_at:
                            chosen = image_path
                            break
                    except OSError:
                        continue
            if chosen is None:
                chosen = files[0]
            newest_key = str(chosen.resolve())
            if self._last_seen_generated_image != newest_key:
                self._last_seen_generated_image = newest_key
                self._image_preview_path = chosen
                self._refresh_image_history()
                self._render_image_preview()
                if not self._image_generation_thread:
                    self._image_status_var.set(f"Loaded latest generated image: {chosen.name}")
        self._ensure_image_polling()

    def _refresh_image_history(self):
        if not self._image_history_frame:
            return
        for child in self._image_history_frame.winfo_children():
            child.destroy()
        files = self._latest_generated_images()
        self._image_generated_files = files
        if not files:
            tk.Label(
                self._image_history_frame,
                text="No generated images yet.",
                font=FONT_SMALL,
                bg=C["card"],
                fg=C["muted"],
            ).pack(anchor="w")
            return
        for image_path in files:
            row = tk.Frame(self._image_history_frame, bg=C["card"])
            row.pack(fill="x", pady=3)
            tk.Button(
                row,
                text=image_path.name,
                command=lambda path=image_path: self._select_generated_image(path),
                font=("Courier", 8, "bold"),
                bg=C["surface"],
                fg=C["text"],
                relief="flat",
                anchor="w",
                padx=10,
                pady=7,
            ).pack(side="left", fill="x", expand=True)

    def _select_generated_image(self, image_path):
        self._image_preview_path = Path(image_path)
        self._last_seen_generated_image = str(Path(image_path).resolve())
        self._image_status_var.set(f"Previewing {Path(image_path).name}")
        self._render_image_preview()

    def _open_generated_images_folder(self):
        preview_path = Path(self._image_preview_path) if self._image_preview_path else None
        if preview_path and preview_path.exists():
            folder = preview_path.parent
        else:
            folder = self.sys_info["images_dir"]
        ensure_dir(folder)
        try:
            os.startfile(str(folder))
            self._image_status_var.set(f"Opened image folder: {folder}")
        except Exception as exc:
            self._image_status_var.set(f"Could not open image folder: {exc}")

    def _add_image_references(self):
        file_paths = filedialog.askopenfilenames(
            title="Choose reference images",
            filetypes=(
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff"),
                ("All files", "*.*"),
            ),
        )
        if not file_paths:
            return
        for file_path in file_paths:
            candidate = str(Path(file_path))
            if candidate not in self._image_reference_paths:
                self._image_reference_paths.append(candidate)
        self._image_status_var.set(f"Added {len(file_paths)} reference image(s).")
        self._show_workspace()

    def _clear_image_references(self):
        self._image_reference_paths = []
        self._image_status_var.set("Reference images cleared.")
        self._show_workspace()

    def _save_generated_image_as(self):
        if not self._image_preview_path or not Path(self._image_preview_path).exists():
            self._image_status_var.set("Generate or open an image first.")
            return
        save_path = filedialog.asksaveasfilename(
            title="Save generated image as",
            defaultextension=".png",
            initialfile=Path(self._image_preview_path).name,
            filetypes=(("PNG image", "*.png"), ("All files", "*.*")),
        )
        if not save_path:
            return
        shutil.copy2(str(self._image_preview_path), save_path)
        self._image_status_var.set(f"Saved copy to {save_path}")

    def _current_image_backend_mode(self):
        return str(self._image_backend_mode_var.get() or self.settings.get("image_backend_mode", "auto")).strip().lower()

    def _current_image_backend_url(self):
        return str(self._image_backend_url_var.get() or self.settings.get("image_backend_url", "http://127.0.0.1:7860")).strip()

    def _image_backend_summary(self):
        mode = self._current_image_backend_mode()
        backend_url = self._current_image_backend_url()
        available, detail, backend_kind = detect_sd_backend(backend_url)
        if mode == "concept":
            return False, "Concept renderer only. Real model backend is disabled.", None
        if available:
            return True, detail, backend_kind
        if mode == "backend":
            return False, f"Real backend required but unavailable. {detail}", None
        return False, f"Auto mode: using concept renderer until a local image backend is running. {detail}", None

    def _refresh_image_backend_status(self):
        available, detail, backend_kind = self._image_backend_summary()
        accel_note = self.sys_info.get("image_acceleration_note", "")
        graphics_name = self.sys_info.get("graphics_name", "Unknown graphics")
        if self._image_backend_status:
            self._image_backend_status.config(
                text=(
                    f"Real backend: {backend_kind.upper()} at {self._current_image_backend_url()} | {graphics_name}. {accel_note}"
                    if available
                    else f"{detail} {graphics_name}. {accel_note}"
                ),
                fg=C["green"] if available else C["muted"],
            )
        return available, detail, backend_kind

    def _image_backend_help_text(self):
        base = (
            "Concept Render stays fully offline for mockups and stylized layouts. "
            "Text-to-image can run through a local Stable Diffusion API or ComfyUI backend when one is bundled or already running. "
            "Reference-based transformations with uploaded people still need a real SD API backend."
        )
        accel_note = self.sys_info.get("image_acceleration_note", "")
        graphics_name = self.sys_info.get("graphics_name", "")
        recommended_size = recommended_image_size_label(self.sys_info)
        if graphics_name:
            return f"{base} Hardware profile: {graphics_name}. {accel_note} Recommended image size on this system: {recommended_size}."
        return base

    def _save_image_backend_preferences(self):
        self.settings["image_backend_mode"] = self._current_image_backend_mode()
        self.settings["image_backend_url"] = self._current_image_backend_url()
        self._save_settings()
        available, detail, backend_kind = self._refresh_image_backend_status()
        if available:
            self._image_status_var.set(f"Real local image backend connected ({backend_kind}).")
        else:
            self._image_status_var.set(detail)

    def _start_image_backend(self):
        self._image_status_var.set("Starting local image backend...")

        def run_backend():
            try:
                backend_kind = self.image_backend.start()
                self.after(
                    0,
                    lambda: self._finish_start_image_backend(backend_kind),
                )
            except Exception as exc:
                self.after(0, lambda: self._image_status_var.set(f"Could not start image backend: {exc}"))
                self.after(0, lambda: self._refresh_image_backend_status())

        threading.Thread(target=run_backend, daemon=True).start()

    def _finish_start_image_backend(self, backend_kind):
        backend_url = self._current_image_backend_url()
        self._refresh_image_backend_status()
        accel_note = self.sys_info.get("image_acceleration_note", "")
        self._image_status_var.set(f"Local image backend is running ({backend_kind}) at {backend_url}. {accel_note}")
        self._workspace_log(f"Image backend started: {backend_kind} at {backend_url}")

    def _stop_image_backend(self):
        self.image_backend.stop()
        self._refresh_image_backend_status()
        self._image_status_var.set("Local image backend stopped.")
        self._workspace_log("Stopped local image backend.")

    def _open_image_backend_folder(self):
        folder = self.sys_info["image_backend_dir"]
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(folder))
            self._image_status_var.set(f"Opened image backend folder: {folder}")
        except Exception as exc:
            self._image_status_var.set(f"Could not open image backend folder: {exc}")

    def _poll_image_generation(self):
        thread = self._image_generation_thread
        if thread and thread.is_alive():
            if self._generate_image_button:
                try:
                    self._generate_image_button.configure(state="disabled")
                except Exception:
                    pass
            if self._image_generation_started_at and self._image_generation_backend_available:
                elapsed = int(max(0, time.time() - self._image_generation_started_at))
                queue_ok, running_count, pending_count = comfyui_queue_status(self._current_image_backend_url())
                if queue_ok:
                    self._image_status_var.set(
                        f"Rendering current image on local CPU backend. Elapsed: {elapsed}s. "
                        f"Queue: {running_count} running, {pending_count} pending. This can take several minutes."
                    )
                else:
                    self._image_status_var.set(
                        f"Rendering current image on local CPU backend. Elapsed: {elapsed}s. "
                        "This can take several minutes."
                    )
            self.after(500, self._poll_image_generation)
            return
        self._image_generation_thread = None
        if self._generate_image_button:
            try:
                self._generate_image_button.configure(state="normal")
            except Exception:
                pass
        if self._image_generation_error:
            exc = self._image_generation_error
            self._workspace_log(f"Image generation failed: {exc}")
            if self._image_generation_backend_available:
                self._image_status_var.set(
                    f"Real backend failed: {exc}. Falling back is available if you switch mode to Auto or Concept Renderer."
                )
            else:
                self._image_status_var.set(f"Image generation failed: {exc}")
            self._image_generation_error = None
            return
        generated_path = self._image_generation_result
        if generated_path:
            self._image_preview_path = Path(generated_path)
            self._last_seen_generated_image = str(Path(generated_path).resolve())
            if self._image_generation_backend_available:
                self._image_status_var.set(
                    f"Real backend image saved locally ({self._image_generation_backend_kind}): {Path(generated_path).name}"
                )
            else:
                self._image_status_var.set(f"Concept render saved locally: {Path(generated_path).name}")
            self._workspace_log(f"Image generation finished: {generated_path}")
            self._render_image_preview()
            self._refresh_image_history()
            self._image_generation_result = None
            self._expected_generated_image = None
            self._image_generation_started_at = None
            return
        self._image_status_var.set("Image generation ended without a file result.")

    def _generate_image(self):
        prompt = self._image_prompt_var.get().strip()
        if not prompt:
            self._image_status_var.set("Describe the visual you want first.")
            return
        if Image is None:
            self._image_status_var.set("Image Studio needs Pillow in this build.")
            return

        style_name = self._image_style_var.get()
        size_name = self._image_size_var.get()
        size = IMAGE_SIZES.get(size_name, IMAGE_SIZES["Square 1024"])
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", prompt.lower()).strip("-") or "image"
        output_path = self.sys_info["images_dir"] / f"{timestamp}-{safe_name[:40]}.png"
        references = [Path(path) for path in self._image_reference_paths if Path(path).exists()]
        backend_available, backend_detail, backend_kind = self._image_backend_summary()
        needs_real_backend = requires_real_image_backend(prompt, references)
        if needs_real_backend and not backend_available:
            self._image_status_var.set(
                "This prompt needs a real local image backend because it transforms an uploaded person. "
                "No image was generated. Start your local image engine, or use a non-photo concept prompt for offline rendering."
            )
            return
        if backend_available:
            self._image_status_var.set("Submitting image job to the real local backend...")
        else:
            self._image_status_var.set("Generating with local concept renderer...")
        self._workspace_log(f"Image generation requested: style={style_name}, size={size_name}, backend={backend_kind or 'concept'}")
        self._image_generation_result = None
        self._image_generation_error = None
        self._expected_generated_image = output_path
        self._image_generation_started_at = time.time()
        self._image_generation_backend_available = backend_available
        self._image_generation_backend_kind = backend_kind

        def run_generation():
            try:
                if backend_available:
                    generated_path = generate_sd_image(
                        prompt,
                        output_path,
                        base_url=self._current_image_backend_url(),
                        size=size,
                        references=references,
                        style_name=style_name,
                    )
                else:
                    generated_path = generate_local_art(
                        prompt,
                        output_path,
                        style_name=style_name,
                        size=size,
                        references=references,
                    )
                self._image_generation_result = generated_path
            except Exception as exc:
                self._image_generation_error = exc

        self._image_status_var.set(
            "Generating image now. CPU systems can take a few minutes for a result."
            if backend_available
            else "Generating concept render now."
        )
        if self._generate_image_button:
            try:
                self._generate_image_button.configure(state="disabled")
            except Exception:
                pass
        self._image_generation_thread = threading.Thread(target=run_generation, daemon=True)
        self._image_generation_thread.start()
        self.after(500, self._poll_image_generation)

    def _render_chat_history(self):
        session = self._get_active_session()
        self._chat_log.configure(state="normal")
        self._chat_log.delete("1.0", "end")
        self._chat_log.insert("end", "Offline AI Workstation ready.\n", "system")
        if not session or not session["messages"]:
            self._chat_log.insert("end", "Start a new chat, choose a local model, and use one of the quick prompts below.\n\n", "meta")
        else:
            for message in session["messages"]:
                stamp = message.get("timestamp", "")
                if message["role"] == "user":
                    self._chat_log.insert("end", f"You", "user_name")
                    if stamp:
                        self._chat_log.insert("end", f"  {stamp}", "time")
                    self._chat_log.insert("end", "\n", "user_name")
                    self._chat_log.insert("end", f"{message['content']}\n\n", "user_body")
                else:
                    self._chat_log.insert("end", f"Assistant", "assistant_name")
                    if stamp:
                        self._chat_log.insert("end", f"  {stamp}", "time")
                    self._chat_log.insert("end", "\n", "assistant_name")
                    self._chat_log.insert("end", f"{message['content']}\n\n", "assistant_body")
        self._chat_log.tag_configure("system", foreground=C["muted"], font=("Segoe UI Semibold", 10))
        self._chat_log.tag_configure("meta", foreground=C["muted"], font=("Segoe UI", 10))
        self._chat_log.tag_configure("time", foreground=C["muted"], font=("Segoe UI", 8))
        self._chat_log.tag_configure("user_name", foreground=C["cyan"], font=("Segoe UI Semibold", 11))
        self._chat_log.tag_configure("assistant_name", foreground=C["green"], font=("Segoe UI Semibold", 11))
        self._chat_log.tag_configure("user_body", foreground=C["text"], font=("Segoe UI", 11), lmargin1=14, lmargin2=14, spacing3=8)
        self._chat_log.tag_configure("assistant_body", foreground=C["text"], font=("Segoe UI", 11), lmargin1=14, lmargin2=14, spacing3=10)
        self._chat_log.see("end")
        self._chat_log.configure(state="disabled")

    def _show_workspace(self):
        self._current_view = "workspace"
        self._compact_layout = self._is_compact_layout("workspace")
        f = self._clear_scrollable() if self._compact_layout else self._clear()
        self._header(f, "WORKSPACE", "Standalone local AI cockpit")
        self._load_model_presets()
        runtime_summary = self.backend.status_summary()
        outer_pad = 16 if self._compact_layout else 28

        models = self._get_installed_models()
        knowledge_docs = discover_knowledge_documents(self.sys_info["knowledge_dir"])
        active = self._get_active_session()
        preferred_model = self._preferred_startup_model()
        if active and active.get("model_path") and Path(active["model_path"]).exists():
            self.selected_model.set(active["model_path"])
        elif preferred_model:
            self.selected_model.set(preferred_model)
            if active and not active.get("model_path"):
                active["model_path"] = preferred_model
        elif models:
            self.selected_model.set(str(models[0]["path"]))

        top_row = tk.Frame(f, bg=C["bg"])
        top_row.pack(fill="x", padx=outer_pad, pady=(0, 10))
        controls_row = tk.Frame(top_row, bg=C["bg"])
        controls_row.pack(fill="x")
        if not self._compact_layout:
            tk.Button(
                controls_row,
                text="HIDE SIDEBAR" if self._sidebar_visible else "SHOW SIDEBAR",
                command=self._toggle_sidebar,
                font=FONT_BUTTON_SMALL,
                bg=C["surface"],
                fg=C["cyan"],
                relief="flat",
                padx=12,
                pady=8,
            ).pack(side="left", padx=(0, 8))
        tk.Button(
            controls_row,
            text=f"SWITCH TO {self._appearance_label()}",
            command=self._toggle_theme,
            font=FONT_BUTTON_SMALL,
            bg=C["surface"],
            fg=C["cyan"],
            relief="flat",
            padx=12,
            pady=8,
        ).pack(
            side="top" if self._compact_layout else "left",
            fill="x" if self._compact_layout else "none",
            padx=(0, 8) if not self._compact_layout else 0,
        )
        badge_row = tk.Frame(top_row, bg=C["bg"])
        badge_row.pack(fill="x", pady=(8, 0) if self._compact_layout else 0)
        self._status_badge(
            badge_row if self._compact_layout else controls_row,
            "RUNTIME READY" if "Runtime ready" in runtime_summary else "RUNTIME MISSING",
            C["green"] if "Runtime ready" in runtime_summary else C["amber"],
        )
        self._status_badge(badge_row if self._compact_layout else controls_row, f"{len(models)} MODELS", C["cyan"] if models else C["amber"])
        self._status_badge(badge_row if self._compact_layout else controls_row, "KB READY", C["green"])

        workspace = tk.Frame(f, bg=C["bg"])
        workspace.pack(fill="both", expand=True, padx=outer_pad, pady=(0, 18))

        if self._sidebar_visible and not self._compact_layout:
            sidebar_wrap = 520 if self._compact_layout else 220
            sidebar = tk.Frame(
                workspace,
                bg=C["card"],
                width=260 if not self._compact_layout else 0,
                bd=0,
                highlightthickness=1,
                highlightbackground=C["border"],
            )
            sidebar.pack(side="top" if self._compact_layout else "left", fill="x" if self._compact_layout else "y", padx=(0, 0 if self._compact_layout else 12), pady=(0, 12 if self._compact_layout else 0))
            sidebar.pack_propagate(False if not self._compact_layout else True)

            tk.Label(sidebar, text="CHATS", font=FONT_HEAD, bg=C["card"], fg=C["cyan"]).pack(anchor="w", padx=12, pady=(12, 2))
            tk.Label(sidebar, text="Multiple local conversations with different models.", font=("Courier", 8), bg=C["card"], fg=C["muted"], wraplength=sidebar_wrap, justify="left").pack(anchor="w", padx=12, pady=(0, 8))

            search_shell = tk.Frame(sidebar, bg=C["surface"], bd=0, highlightthickness=1, highlightbackground=C["border"])
            search_shell.pack(fill="x", padx=12, pady=(0, 10))
            tk.Label(search_shell, text="SEARCH CHATS", font=("Courier", 8, "bold"), bg=C["surface"], fg=C["muted"]).pack(anchor="w", padx=8, pady=(6, 0))
            search_entry = tk.Entry(search_shell, textvariable=self._session_search, font=("Courier", 9), bg=C["surface"], fg=C["text"], insertbackground=C["cyan"], relief="flat")
            search_entry.pack(fill="x", padx=8, pady=(2, 8), ipady=5)
            search_entry.bind("<KeyRelease>", lambda _event: self._refresh_session_list_view())

            side_actions = tk.Frame(sidebar, bg=C["card"])
            side_actions.pack(fill="x", padx=12, pady=(0, 10))
            side_buttons = [
                ("NEW CHAT", self._new_chat, ("Courier", 9, "bold"), C["green"], C["button_text"]),
                ("RENAME", self._rename_active_chat, ("Courier", 8), C["surface"], C["muted"]),
                ("PIN", self._toggle_pin_active_chat, ("Courier", 8), C["surface"], C["muted"]),
                ("DELETE", self._delete_active_chat, ("Courier", 8), C["surface"], C["muted"]),
            ]
            for index, (label, command, font, bg, fg) in enumerate(side_buttons):
                button = tk.Button(side_actions, text=label, command=command, font=font, bg=bg, fg=fg, relief="flat", padx=8, pady=8)
                if self._compact_layout:
                    button.grid(row=index // 2, column=index % 2, sticky="ew", padx=3, pady=3)
                else:
                    button.pack(side="left", padx=(0, 6) if index == 0 else 3)
            if self._compact_layout:
                side_actions.grid_columnconfigure(0, weight=1)
                side_actions.grid_columnconfigure(1, weight=1)

            self._session_list_frame = tk.Frame(sidebar, bg=C["card"])
            self._session_list_frame.pack(fill="x", padx=12, pady=(0, 10))
            self._render_session_list(self._session_list_frame)

            models_panel = tk.Frame(sidebar, bg=C["card"], bd=0, highlightthickness=1, highlightbackground=C["border"])
            models_panel.pack(fill="x", padx=12, pady=(4, 10))
            tk.Button(
                models_panel,
                text="MODELS [+]" if not self._models_expanded else "MODELS [-]",
                command=self._toggle_models_panel,
                font=("Courier", 9, "bold"),
                bg=C["card"],
                fg=C["green"],
                activebackground=C["card"],
                activeforeground=C["green"],
                relief="flat",
                anchor="w",
                padx=8,
                pady=8,
            ).pack(fill="x")
            if self._models_expanded:
                models_list = tk.Frame(models_panel, bg=C["card"])
                models_list.pack(fill="x", padx=4, pady=(0, 8))
                self._render_model_list(models_list, models)

            knowledge_panel = tk.Frame(sidebar, bg=C["card"], bd=0, highlightthickness=1, highlightbackground=C["border"])
            knowledge_panel.pack(fill="x", padx=12, pady=(0, 12))
            tk.Label(knowledge_panel, text="KNOWLEDGE BASE", font=("Courier", 10, "bold"), bg=C["card"], fg=C["green"]).pack(anchor="w", padx=10, pady=(10, 2))
            self._knowledge_status = tk.Label(knowledge_panel, text=f"Folder: {self.sys_info['knowledge_dir']}", font=("Courier", 8), bg=C["card"], fg=C["muted"], wraplength=sidebar_wrap, justify="left")
            self._knowledge_status.pack(anchor="w", padx=10, pady=(0, 4))
            self._knowledge_hint = tk.Label(knowledge_panel, text=self._knowledge_summary_text(knowledge_docs), font=("Courier", 8), bg=C["card"], fg=C["text"], wraplength=sidebar_wrap, justify="left")
            self._knowledge_hint.pack(anchor="w", padx=10, pady=(0, 8))
            kb_actions = tk.Frame(knowledge_panel, bg=C["card"])
            kb_actions.pack(fill="x", padx=10, pady=(0, 10))
            kb_buttons = [
                ("IMPORT", self._import_knowledge_files, ("Courier", 8, "bold"), C["green"], C["button_text"]),
                ("OPEN", self._open_knowledge_folder, ("Courier", 8), C["surface"], C["muted"]),
                ("REFRESH", self._refresh_knowledge_panel, ("Courier", 8), C["surface"], C["muted"]),
            ]
            for index, (label, command, font, bg, fg) in enumerate(kb_buttons):
                button = tk.Button(kb_actions, text=label, command=command, font=font, bg=bg, fg=fg, relief="flat", padx=8, pady=6)
                if self._compact_layout:
                    button.pack(fill="x", pady=3)
                else:
                    button.pack(side="left", padx=(0, 6) if index == 0 else 3)

        main = tk.Frame(workspace, bg=C["card"], bd=0, highlightthickness=1, highlightbackground=C["border"])
        main.pack(side="top" if self._compact_layout else "left", fill="both", expand=True)

        tab_row = tk.Frame(main, bg=C["card"])
        tab_row.pack(fill="x", padx=16, pady=(12, 0))
        for label, tab_name in (("CHAT", "chat"), ("IMAGE STUDIO", "image")):
            is_active = self._workspace_tab == tab_name
            tk.Button(
                tab_row,
                text=label,
                command=lambda tab=tab_name: self._set_workspace_tab(tab),
                font=FONT_BUTTON_SMALL,
                bg=C["cyan"] if is_active else C["surface"],
                fg=C["button_text"] if is_active else C["muted"],
                relief="flat",
                padx=14,
                pady=8,
            ).pack(side="left", padx=(0, 8))

        main_header = tk.Frame(main, bg=C["card"])
        main_header.pack(fill="x", padx=16, pady=(12, 8))
        title_col = tk.Frame(main_header, bg=C["card"])
        title_col.pack(side="top" if self._compact_layout else "left", fill="x", expand=True, anchor="w")
        session_title = active["title"] if active else "New Chat"
        header_title = session_title if self._workspace_tab == "chat" else "Image Studio"
        tk.Label(title_col, text=header_title, font=("Consolas", 16, "bold"), bg=C["card"], fg=C["white"]).pack(anchor="w")
        tk.Label(title_col, text=runtime_summary, font=FONT_SMALL, bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(2, 2))
        model_name = Path(active["model_path"]).stem if active and active.get("model_path") else "No model selected"
        if self._workspace_tab == "chat":
            tk.Label(title_col, text=f"Model for this chat: {model_name}", font=FONT_SMALL, bg=C["card"], fg=C["cyan"]).pack(anchor="w")
        else:
            tk.Label(title_col, text="Prompt-guided local concept renderer with export and reference images.", font=FONT_SMALL, bg=C["card"], fg=C["cyan"]).pack(anchor="w")
        if self._compact_layout:
            tk.Label(
                title_col,
                text=(
                    self._model_capability_text(active["model_path"])
                    if self._workspace_tab == "chat" and active and active.get("model_path")
                    else "Create prompt-guided concept renders, packaging mockups, posters, and branded visual drafts."
                ),
                font=FONT_SMALL,
                bg=C["card"],
                fg=C["muted"],
                wraplength=520,
                justify="left",
            ).pack(anchor="w", pady=(2, 0))
        else:
            tk.Label(
                title_col,
                text=(
                    self._model_capability_text(active["model_path"])
                    if self._workspace_tab == "chat" and active and active.get("model_path")
                    else "Create prompt-guided concept renders, packaging mockups, posters, and branded visual drafts."
                ),
                font=FONT_SMALL,
                bg=C["card"],
                fg=C["muted"],
                wraplength=420,
                justify="left",
            ).pack(anchor="w", pady=(2, 0))

            main_actions = tk.Frame(main_header, bg=C["card"])
            main_actions.pack(side="right", anchor="e")
            action_buttons = [
                ("START RUNTIME", self._start_runtime, FONT_BUTTON_SMALL, C["cyan"], C["button_text"]),
                ("STOP", self._stop_runtime, FONT_SMALL, C["surface"], C["muted"]),
                ("EXPORT CHAT" if self._workspace_tab == "chat" else "SAVE IMAGE", self._export_active_chat if self._workspace_tab == "chat" else self._save_generated_image_as, FONT_SMALL, C["surface"], C["muted"]),
                ("SETTINGS", self._show_settings, FONT_SMALL, C["surface"], C["cyan"]),
                ("BACK", self._show_done, FONT_SMALL, C["surface"], C["muted"]),
            ]
            for label, command, font, bg, fg in action_buttons:
                tk.Button(
                    main_actions,
                    text=label,
                    command=command,
                    font=font,
                    bg=bg,
                    fg=fg,
                    relief="flat",
                    padx=12,
                    pady=8,
                ).pack(side="left", padx=4)

        self._workspace_status = tk.Label(
            main,
            text="Choose a model and start the runtime." if self._workspace_tab == "chat" else self._image_status_var.get(),
            font=FONT_SMALL,
            bg=C["card"],
            fg=C["muted"],
        )
        if self._workspace_tab != "chat":
            self._workspace_status.configure(textvariable=self._image_status_var)
        self._workspace_status.pack(anchor="w", padx=16, pady=(0, 6))

        if self._workspace_tab == "chat":
            convo_shell = tk.Frame(main, bg=C["card"])
            convo_shell.pack(fill="both", expand=True, padx=16, pady=(0, 12))
            chat_frame = tk.Frame(convo_shell, bg=C["surface"], bd=0, highlightthickness=1, highlightbackground=C["border"])
            chat_frame.pack(fill="both", expand=True)
            self._chat_log = tk.Text(chat_frame, font=FONT_CHAT, bg=C["surface"], fg=C["text"], bd=0, wrap="word", insertbackground=C["cyan"])
            self._chat_log.pack(fill="both", expand=True, padx=12, pady=12)
            self._render_chat_history()

            if not active or not active["messages"]:
                prompt_bar = tk.Frame(convo_shell, bg=C["card"])
                prompt_bar.pack(fill="x", pady=(10, 0))
                tk.Label(prompt_bar, text="QUICK START", font=("Consolas", 8, "bold"), bg=C["card"], fg=C["muted"]).pack(anchor="w", pady=(0, 6))
                prompts_row = tk.Frame(prompt_bar, bg=C["card"])
                prompts_row.pack(fill="x")
                for prompt in STARTER_PROMPTS:
                    button = tk.Button(
                        prompts_row,
                        text=prompt,
                        command=lambda p=prompt: self._use_starter_prompt(p),
                        font=FONT_SMALL,
                        bg=C["surface"],
                        fg=C["text"],
                        activebackground=C["surface"],
                        activeforeground=C["cyan"],
                        relief="flat",
                        bd=0,
                        highlightthickness=1,
                        highlightbackground=C["border"],
                        anchor="w",
                        justify="left",
                        wraplength=180,
                        padx=10,
                        pady=8,
                    )
                    if self._compact_layout:
                        button.pack(fill="x", pady=4)
                    else:
                        button.pack(side="left", fill="x", expand=True, padx=(0, 8))

            input_row = tk.Frame(main, bg=C["card"])
            input_row.pack(fill="x", padx=16, pady=(0, 16))
            input_shell = tk.Frame(input_row, bg=C["surface"], highlightthickness=1, highlightbackground=C["border"])
            input_shell.pack(side="top" if self._compact_layout else "left", fill="x", expand=True)
            tk.Label(input_shell, text="Message", font=("Consolas", 8, "bold"), bg=C["surface"], fg=C["muted"]).pack(anchor="w", padx=12, pady=(8, 0))
            self._chat_entry = tk.Entry(input_shell, font=("Segoe UI", 12), bg=C["surface"], fg=C["text"], insertbackground=C["cyan"], relief="flat")
            self._chat_entry.pack(fill="x", padx=12, pady=(2, 10), ipady=10)
            self._chat_entry.bind("<Return>", lambda _event: self._send_chat())
            tk.Button(
                input_row,
                text="SEND",
                command=self._send_chat,
                font=("Consolas", 10, "bold"),
                bg=C["green"],
                fg=C["button_text"],
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground=C["border"],
                padx=18,
                pady=18,
            ).pack(side="top" if self._compact_layout else "left", fill="x" if self._compact_layout else "none", padx=(0 if self._compact_layout else 8, 0), pady=(8, 0) if self._compact_layout else 0)
        else:
            studio_shell = tk.Frame(main, bg=C["card"])
            studio_shell.pack(fill="both", expand=True, padx=16, pady=(0, 12))

            controls = tk.Frame(studio_shell, bg=C["card"])
            controls.pack(fill="x", pady=(0, 10))
            prompt_shell = tk.Frame(controls, bg=C["surface"], highlightthickness=1, highlightbackground=C["border"])
            prompt_shell.pack(fill="x", pady=(0, 8))
            tk.Label(prompt_shell, text="Image Prompt", font=("Consolas", 8, "bold"), bg=C["surface"], fg=C["muted"]).pack(anchor="w", padx=12, pady=(8, 0))
            self._image_prompt_entry = tk.Entry(prompt_shell, textvariable=self._image_prompt_var, font=("Segoe UI", 12), bg=C["surface"], fg=C["text"], insertbackground=C["cyan"], relief="flat")
            self._image_prompt_entry.pack(fill="x", padx=12, pady=(2, 10), ipady=10)
            self._image_prompt_entry.bind("<Return>", lambda _event: self._generate_image())

            control_grid = tk.Frame(controls, bg=C["card"])
            control_grid.pack(fill="x", pady=(0, 8))
            style_menu = tk.OptionMenu(control_grid, self._image_style_var, *IMAGE_STYLES.keys())
            style_menu.configure(bg=C["surface"], fg=C["text"], relief="flat", activebackground=C["surface"], activeforeground=C["cyan"], highlightthickness=1, highlightbackground=C["border"])
            style_menu["menu"].configure(bg=C["card"], fg=C["text"])
            size_menu = tk.OptionMenu(control_grid, self._image_size_var, *IMAGE_SIZES.keys())
            size_menu.configure(bg=C["surface"], fg=C["text"], relief="flat", activebackground=C["surface"], activeforeground=C["cyan"], highlightthickness=1, highlightbackground=C["border"])
            size_menu["menu"].configure(bg=C["card"], fg=C["text"])
            style_menu.pack(side="left", fill="x", expand=True, padx=(0, 8))
            size_menu.pack(side="left", fill="x", expand=True)

            backend_row = tk.Frame(controls, bg=C["card"])
            backend_row.pack(fill="x", pady=(0, 8))
            backend_mode_menu = tk.OptionMenu(backend_row, self._image_backend_mode_var, "auto", "backend", "concept")
            backend_mode_menu.configure(bg=C["surface"], fg=C["text"], relief="flat", activebackground=C["surface"], activeforeground=C["cyan"], highlightthickness=1, highlightbackground=C["border"])
            backend_mode_menu["menu"].configure(bg=C["card"], fg=C["text"])
            backend_mode_menu.pack(side="left", padx=(0, 8))
            backend_entry = tk.Entry(backend_row, textvariable=self._image_backend_url_var, font=("Segoe UI", 10), bg=C["surface"], fg=C["text"], insertbackground=C["cyan"], relief="flat")
            backend_entry.pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 8))
            tk.Button(backend_row, text="SAVE", command=self._save_image_backend_preferences, font=FONT_BUTTON_SMALL, bg=C["surface"], fg=C["cyan"], relief="flat", padx=12, pady=8).pack(side="left")

            backend_actions = tk.Frame(controls, bg=C["card"])
            backend_actions.pack(fill="x", pady=(0, 8))
            tk.Button(backend_actions, text="START IMAGE ENGINE", command=self._start_image_backend, font=("Consolas", 8, "bold"), bg=C["cyan"], fg=C["button_text"], relief="flat", padx=12, pady=8).pack(side="left", padx=(0, 8))
            tk.Button(backend_actions, text="STOP ENGINE", command=self._stop_image_backend, font=("Consolas", 8), bg=C["surface"], fg=C["muted"], relief="flat", padx=10, pady=8).pack(side="left", padx=(0, 8))
            tk.Button(backend_actions, text="OPEN BACKEND FOLDER", command=self._open_image_backend_folder, font=("Consolas", 8), bg=C["surface"], fg=C["muted"], relief="flat", padx=10, pady=8).pack(side="left")

            refs_row = tk.Frame(controls, bg=C["card"])
            refs_row.pack(fill="x", pady=(0, 8))
            tk.Button(refs_row, text="ADD REFERENCES", command=self._add_image_references, font=("Courier", 8, "bold"), bg=C["surface"], fg=C["cyan"], relief="flat", padx=10, pady=8).pack(side="left", padx=(0, 8))
            tk.Button(refs_row, text="CLEAR REFERENCES", command=self._clear_image_references, font=("Courier", 8), bg=C["surface"], fg=C["muted"], relief="flat", padx=10, pady=8).pack(side="left", padx=(0, 8))
            tk.Button(refs_row, text="OPEN IMAGE FOLDER", command=self._open_generated_images_folder, font=("Courier", 8), bg=C["surface"], fg=C["muted"], relief="flat", padx=10, pady=8).pack(side="left")

            self._image_backend_status = tk.Label(controls, text="", font=FONT_SMALL, bg=C["card"], fg=C["muted"], wraplength=620, justify="left")
            self._image_backend_status.pack(anchor="w", pady=(0, 8))
            self._refresh_image_backend_status()
            tk.Label(
                controls,
                text=self._image_backend_help_text(),
                font=FONT_SMALL,
                bg=C["card"],
                fg=C["muted"],
                wraplength=620,
                justify="left",
            ).pack(anchor="w", pady=(0, 8))

            ref_summary = "No references selected." if not self._image_reference_paths else f"References: {', '.join(Path(path).name for path in self._image_reference_paths[:3])}" + (", ..." if len(self._image_reference_paths) > 3 else "")
            tk.Label(controls, text=ref_summary, font=FONT_SMALL, bg=C["card"], fg=C["muted"], wraplength=620, justify="left").pack(anchor="w", pady=(0, 10))

            generate_row = tk.Frame(controls, bg=C["card"])
            generate_row.pack(fill="x", pady=(0, 12))
            self._generate_image_button = tk.Button(generate_row, text="GENERATE IMAGE", command=self._generate_image, font=("Consolas", 10, "bold"), bg=C["green"], fg=C["button_text"], relief="flat", padx=18, pady=12)
            self._generate_image_button.pack(side="left", padx=(0, 8))
            tk.Button(generate_row, text="SAVE COPY", command=self._save_generated_image_as, font=("Consolas", 8, "bold"), bg=C["surface"], fg=C["muted"], relief="flat", padx=14, pady=12).pack(side="left")

            preview_area = tk.Frame(studio_shell, bg=C["card"])
            preview_area.pack(fill="both", expand=True)
            preview_frame = tk.Frame(preview_area, bg=C["surface"], bd=0, highlightthickness=1, highlightbackground=C["border"])
            history_frame = tk.Frame(preview_area, bg=C["card"], bd=0, highlightthickness=1, highlightbackground=C["border"], width=230)
            if self._compact_layout:
                preview_frame.pack(fill="both", expand=True, pady=(0, 10))
                history_frame.pack(fill="x")
            else:
                preview_frame.pack(side="left", fill="both", expand=True, padx=(0, 12))
                history_frame.pack(side="left", fill="y")
                history_frame.pack_propagate(False)

            self._image_preview_widget = tk.Label(preview_frame, text="No image generated yet.", font=FONT_SMALL, bg=C["surface"], fg=C["muted"])
            self._image_preview_widget.pack(fill="both", expand=True, padx=12, pady=12)
            self._image_preview_widget.bind("<Configure>", lambda _event: self._render_image_preview())
            self._render_image_preview()

            tk.Label(history_frame, text="RECENT IMAGES", font=("Consolas", 10, "bold"), bg=C["card"], fg=C["cyan"]).pack(anchor="w", padx=12, pady=(12, 8))
            self._image_history_frame = tk.Frame(history_frame, bg=C["card"])
            self._image_history_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
            self._refresh_image_history()

        if self._compact_layout:
            compact_controls = tk.Frame(main, bg=C["card"])
            compact_controls.pack(fill="x", padx=16, pady=(0, 8))
            compact_buttons = [
                ("CHATS", "chats"),
                ("MODELS", "models"),
                ("TOOLS", "tools"),
                ("KNOWLEDGE", "knowledge"),
            ]
            for index, (label, panel_name) in enumerate(compact_buttons):
                active_panel = self._compact_panel == panel_name
                button = tk.Button(
                    compact_controls,
                    text=f"{label} {'[-]' if active_panel else '[+]'}",
                    command=lambda p=panel_name: self._toggle_compact_panel(p),
                    font=("Consolas", 8, "bold"),
                    bg=C["surface"] if not active_panel else C["card"],
                    fg=C["cyan"] if not active_panel else C["white"],
                    relief="flat",
                    bd=0,
                    highlightthickness=1,
                    highlightbackground=C["cyan"] if active_panel else C["border"],
                    padx=8,
                    pady=7,
                )
                button.grid(row=0, column=index, sticky="ew", padx=4, pady=2)
                compact_controls.grid_columnconfigure(index, weight=1)

            if self._compact_panel:
                panel_wrap = 520
                compact_panel = tk.Frame(main, bg=C["card"], bd=0, highlightthickness=1, highlightbackground=C["border"])
                compact_panel.pack(fill="x", padx=16, pady=(0, 12))
                if self._compact_panel == "chats":
                    tk.Label(compact_panel, text="CHATS", font=FONT_HEAD, bg=C["card"], fg=C["cyan"]).pack(anchor="w", padx=12, pady=(12, 2))
                    tk.Label(compact_panel, text="Multiple local conversations with different models.", font=("Courier", 8), bg=C["card"], fg=C["muted"], wraplength=panel_wrap, justify="left").pack(anchor="w", padx=12, pady=(0, 8))
                    search_shell = tk.Frame(compact_panel, bg=C["surface"], bd=0, highlightthickness=1, highlightbackground=C["border"])
                    search_shell.pack(fill="x", padx=12, pady=(0, 10))
                    tk.Label(search_shell, text="SEARCH CHATS", font=("Courier", 8, "bold"), bg=C["surface"], fg=C["muted"]).pack(anchor="w", padx=8, pady=(6, 0))
                    search_entry = tk.Entry(search_shell, textvariable=self._session_search, font=("Courier", 9), bg=C["surface"], fg=C["text"], insertbackground=C["cyan"], relief="flat")
                    search_entry.pack(fill="x", padx=8, pady=(2, 8), ipady=5)
                    search_entry.bind("<KeyRelease>", lambda _event: self._refresh_session_list_view())

                    side_actions = tk.Frame(compact_panel, bg=C["card"])
                    side_actions.pack(fill="x", padx=12, pady=(0, 10))
                    side_buttons = [
                        ("NEW CHAT", self._new_chat, ("Courier", 9, "bold"), C["green"], C["button_text"]),
                        ("RENAME", self._rename_active_chat, ("Courier", 8), C["surface"], C["muted"]),
                        ("PIN", self._toggle_pin_active_chat, ("Courier", 8), C["surface"], C["muted"]),
                        ("DELETE", self._delete_active_chat, ("Courier", 8), C["surface"], C["muted"]),
                    ]
                    for index, (label, command, font, bg, fg) in enumerate(side_buttons):
                        button = tk.Button(side_actions, text=label, command=command, font=font, bg=bg, fg=fg, relief="flat", padx=8, pady=8)
                        button.grid(row=index // 2, column=index % 2, sticky="ew", padx=3, pady=3)
                    side_actions.grid_columnconfigure(0, weight=1)
                    side_actions.grid_columnconfigure(1, weight=1)

                    self._session_list_frame = tk.Frame(compact_panel, bg=C["card"])
                    self._session_list_frame.pack(fill="x", padx=12, pady=(0, 10))
                    self._render_session_list(self._session_list_frame)
                elif self._compact_panel == "models":
                    tk.Label(compact_panel, text="MODELS", font=FONT_HEAD, bg=C["card"], fg=C["green"]).pack(anchor="w", padx=12, pady=(12, 8))
                    models_list = tk.Frame(compact_panel, bg=C["card"])
                    models_list.pack(fill="x", padx=12, pady=(0, 10))
                    self._render_model_list(models_list, models)
                elif self._compact_panel == "tools":
                    tk.Label(compact_panel, text="RUNTIME TOOLS", font=("Courier", 10, "bold"), bg=C["card"], fg=C["cyan"]).pack(anchor="w", padx=12, pady=(12, 2))
                    tk.Label(compact_panel, text="Start or stop the local runtime, export the current chat, or open settings.", font=("Courier", 8), bg=C["card"], fg=C["muted"], wraplength=panel_wrap, justify="left").pack(anchor="w", padx=12, pady=(0, 8))
                    tools_grid = tk.Frame(compact_panel, bg=C["card"])
                    tools_grid.pack(fill="x", padx=12, pady=(0, 10))
                    tool_buttons = [
                        ("START RUNTIME", self._start_runtime, ("Courier", 9, "bold"), C["cyan"], C["button_text"]),
                        ("STOP", self._stop_runtime, ("Courier", 8), C["surface"], C["muted"]),
                        ("EXPORT", self._export_active_chat, ("Courier", 8), C["surface"], C["muted"]),
                        ("SETTINGS", self._show_settings, ("Courier", 8), C["surface"], C["cyan"]),
                        ("BACK", self._show_done, ("Courier", 8), C["surface"], C["muted"]),
                    ]
                    for index, (label, command, font, bg, fg) in enumerate(tool_buttons):
                        tk.Button(
                            tools_grid,
                            text=label,
                            command=command,
                            font=font,
                            bg=bg,
                            fg=fg,
                            relief="flat",
                            bd=0,
                            highlightthickness=1,
                            highlightbackground=C["border"],
                            padx=8,
                            pady=8,
                        ).grid(row=index // 2, column=index % 2, sticky="ew", padx=3, pady=3)
                    tools_grid.grid_columnconfigure(0, weight=1)
                    tools_grid.grid_columnconfigure(1, weight=1)
                elif self._compact_panel == "knowledge":
                    tk.Label(compact_panel, text="KNOWLEDGE BASE", font=("Courier", 10, "bold"), bg=C["card"], fg=C["green"]).pack(anchor="w", padx=10, pady=(10, 2))
                    self._knowledge_status = tk.Label(compact_panel, text=f"Folder: {self.sys_info['knowledge_dir']}", font=("Courier", 8), bg=C["card"], fg=C["muted"], wraplength=panel_wrap, justify="left")
                    self._knowledge_status.pack(anchor="w", padx=10, pady=(0, 4))
                    self._knowledge_hint = tk.Label(compact_panel, text=self._knowledge_summary_text(knowledge_docs), font=("Courier", 8), bg=C["card"], fg=C["text"], wraplength=panel_wrap, justify="left")
                    self._knowledge_hint.pack(anchor="w", padx=10, pady=(0, 8))
                    kb_actions = tk.Frame(compact_panel, bg=C["card"])
                    kb_actions.pack(fill="x", padx=10, pady=(0, 10))
                    kb_buttons = [
                        ("IMPORT", self._import_knowledge_files, ("Courier", 8, "bold"), C["green"], C["button_text"]),
                        ("OPEN", self._open_knowledge_folder, ("Courier", 8), C["surface"], C["muted"]),
                        ("REFRESH", self._refresh_knowledge_panel, ("Courier", 8), C["surface"], C["muted"]),
                    ]
                    for label, command, font, bg, fg in kb_buttons:
                        tk.Button(
                            kb_actions,
                            text=label,
                            command=command,
                            font=font,
                            bg=bg,
                            fg=fg,
                            relief="flat",
                            padx=8,
                            pady=6,
                        ).pack(fill="x", pady=3)

        if self._workspace_tab == "chat" and self._chat_entry:
            self.after(50, lambda: self._chat_entry.focus_set())
        elif self._workspace_tab == "image" and self._image_prompt_entry:
            self.after(50, lambda: self._image_prompt_entry.focus_set())
        self._maybe_auto_start_runtime()
        self._maybe_auto_start_image_backend()

    def _workspace_log(self, message):
        if not self._chat_log:
            return
        try:
            self._chat_log.configure(state="normal")
            self._chat_log.insert("end", f"{message}\n")
            self._chat_log.see("end")
            self._chat_log.configure(state="disabled")
        except Exception:
            self._chat_log = None

    def _knowledge_summary_text(self, knowledge_docs):
        if not knowledge_docs:
            return (
                "Knowledge Base is included and ready. Import files like PDF, Word, Excel, images, TXT, MD, CSV, JSON, "
                "code, logs, and HTML. The app will search them on this computer and use matching excerpts in chat."
            )
        preview = ", ".join(doc["name"] for doc in knowledge_docs[:3])
        if len(knowledge_docs) > 3:
            preview += ", ..."
        return f"{len(knowledge_docs)} local document(s) ready. Current files: {preview}"

    def _refresh_knowledge_panel(self):
        knowledge_docs = discover_knowledge_documents(self.sys_info["knowledge_dir"])
        if self._knowledge_status:
            self._knowledge_status.config(text=f"Folder: {self.sys_info['knowledge_dir']}")
        if self._knowledge_hint:
            self._knowledge_hint.config(text=self._knowledge_summary_text(knowledge_docs))
        if self._workspace_status:
            self._workspace_status.config(text=f"Knowledge base refreshed: {len(knowledge_docs)} document(s) available.")
        self._workspace_log(f"Knowledge base refreshed. Found {len(knowledge_docs)} supported local file(s).")

    def _copy_into_knowledge_base(self, source_path):
        src = Path(source_path)
        if src.suffix.lower() not in KNOWLEDGE_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {src.suffix or '[no extension]'}")

        target_dir = self.sys_info["knowledge_dir"]
        target_dir.mkdir(parents=True, exist_ok=True)
        dest = target_dir / src.name
        counter = 2
        while dest.exists():
            dest = target_dir / f"{src.stem}-{counter}{src.suffix}"
            counter += 1
        shutil.copy2(str(src), str(dest))
        return dest

    def _import_knowledge_files(self):
        self.sys_info["knowledge_dir"].mkdir(parents=True, exist_ok=True)
        file_paths = filedialog.askopenfilenames(
                title="Import files into local knowledge base",
                filetypes=(
                    ("Supported files", "*.pdf *.docx *.xlsx *.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff *.txt *.md *.csv *.json *.log *.ini *.cfg *.yaml *.yml *.xml *.html *.htm *.py *.js *.ts *.tsx *.jsx *.css *.java *.cs *.cpp *.c *.h *.sql *.ps1 *.bat"),
                    ("All files", "*.*"),
                ),
            )
        if not file_paths:
            return

        imported = []
        skipped = []
        for file_path in file_paths:
            try:
                dest = self._copy_into_knowledge_base(file_path)
                imported.append(dest.name)
            except Exception as exc:
                skipped.append(f"{Path(file_path).name} ({exc})")

        self._refresh_knowledge_panel()
        if imported:
            self._workspace_log(f"Imported into knowledge base: {', '.join(imported)}")
        if skipped:
            self._workspace_log(f"Skipped: {', '.join(skipped)}")

    def _open_knowledge_folder(self):
        folder = self.sys_info["knowledge_dir"]
        folder.mkdir(parents=True, exist_ok=True)
        try:
            import os

            os.startfile(str(folder))
            if self._workspace_status:
                self._workspace_status.config(text=f"Opened knowledge folder: {folder}")
        except Exception as exc:
            if self._workspace_status:
                self._workspace_status.config(text=f"Could not open folder: {exc}")
            self._workspace_log(f"Knowledge folder open error: {exc}")

    def _start_runtime(self):
        session = self._get_active_session()
        model_path = session.get("model_path") if session else self.selected_model.get()
        if not model_path:
            self._workspace_status.config(text="Download a model first.")
            return
        preset = self._preset_for_model_path(model_path)
        try:
            self.backend.start(model_path, context_length=preset.get("contextLength"))
            self._workspace_status.config(text=f"Runtime is running on http://127.0.0.1:{RUNTIME_PORT}")
            self._workspace_log(
                f"Runtime started with {Path(model_path).name} ({self._model_capability_text(model_path)})"
            )
        except Exception as exc:
            self._workspace_status.config(text=str(exc))
            self._workspace_log(f"Runtime error: {exc}")

    def _stop_runtime(self):
        self.backend.stop()
        self._workspace_status.config(text="Runtime stopped.")
        self._workspace_log("Stopped local runtime.")

    def _send_chat(self):
        prompt = self._chat_entry.get().strip()
        if not prompt:
            return
        session = self._get_active_session()
        model_path = session.get("model_path") if session else self.selected_model.get()
        if not model_path:
            self._workspace_status.config(text="Select a model before chatting.")
            return

        model_name = Path(model_path).stem
        knowledge_docs = discover_knowledge_documents(self.sys_info["knowledge_dir"])
        knowledge_context = build_knowledge_context(prompt, knowledge_docs)
        self._append_session_message("user", prompt)
        self._render_chat_history()
        self._chat_entry.delete(0, "end")
        self._workspace_status.config(text="Sending prompt to local runtime...")
        if knowledge_context:
            self._workspace_log("Knowledge base: added local document context to this prompt.")

        def run_chat():
            try:
                preset = self._preset_for_model_path(model_path)
                system_prompt = self._build_system_prompt(model_path, knowledge_context)
                reply = self.backend.chat(
                    model_name,
                    system_prompt=system_prompt,
                    messages=self._conversation_messages_for_runtime(prompt, knowledge_context),
                    temperature=preset.get("temperature", DEFAULT_MODEL_PRESET["temperature"]),
                    max_tokens=preset.get("maxTokens", DEFAULT_MODEL_PRESET["maxTokens"]),
                    top_p=preset.get("topP", DEFAULT_MODEL_PRESET["topP"]),
                    repeat_penalty=preset.get("repeatPenalty", DEFAULT_MODEL_PRESET["repeatPenalty"]),
                )
                def finish():
                    self._append_session_message("assistant", reply)
                    self._render_chat_history()
                    self._show_workspace()
                    self._workspace_status.config(text="Response complete.")
                self.after(0, finish)
            except Exception as exc:
                self.after(0, lambda: self._workspace_log(f"Runtime error: {exc}"))
                self.after(0, lambda: self._workspace_status.config(text=str(exc)))

        threading.Thread(target=run_chat, daemon=True).start()

    def _maybe_auto_start_runtime(self):
        if not self.settings.get("auto_start_runtime", False):
            return
        if getattr(self, "_workspace_tab", "chat") == "image":
            return
        if self.backend.is_running():
            return
        session = self._get_active_session()
        model_path = session.get("model_path") if session else self.selected_model.get()
        if not model_path or not Path(model_path).exists():
            return
        self.after(150, self._start_runtime)

    def _maybe_auto_start_image_backend(self):
        if not self.settings.get("auto_start_image_backend", False):
            return
        if getattr(self, "_workspace_tab", "chat") != "image":
            return
        available, _detail, _kind = self._image_backend_summary()
        if available:
            return
        self.after(200, self._start_image_backend)

    def _show_error(self, msg):
        self._current_view = "error"
        f = self._clear_scrollable()
        tk.Frame(f, bg=C["red"], height=3).pack(fill="x")
        tk.Frame(f, bg=C["bg"], height=48).pack()
        tk.Label(f, text="X", font=("Courier", 64, "bold"), bg=C["bg"], fg=C["red"]).pack()
        tk.Label(f, text="INSTALL FAILED", font=FONT_TITLE, bg=C["bg"], fg=C["red"]).pack(pady=(4, 8))
        err_box = tk.Frame(f, bg=C["card"])
        err_box.pack(padx=60, pady=8, fill="x")
        tk.Label(err_box, text=msg, font=("Courier", 9), bg=C["card"], fg=C["muted"], wraplength=520, justify="left").pack(padx=12, pady=12)
        tk.Button(f, text="TRY AGAIN", command=self._show_welcome, font=("Courier", 11, "bold"), bg=C["cyan"], fg=C["button_text"],
                  relief="flat", padx=24, pady=8).pack(pady=8)
        tk.Button(f, text="CLOSE", command=self.destroy, font=FONT_SMALL, bg=C["surface"], fg=C["muted"],
                  relief="flat", padx=16, pady=8).pack()

    def _handle_close(self):
        try:
            self.backend.stop()
        except Exception:
            pass
        try:
            self.image_backend.stop()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    app = StandaloneApp()
    app.mainloop()
