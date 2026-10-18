import os
from typing import List

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

# Layer 1: defaults
DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

# Layer 2: config.development.yaml
YAML_LAYER = {"port": 8250, "api_key": "key-re8mwl5lc0"}

# Layer 3: .env file
DOTENV_TEXT = "APP_DEBUG=false\nAPP_LOG_LEVEL=info\n"

# Layer 4: OS env (APP_* prefix). Real env vars override these if set.
OS_LAYER_DEFAULT = {"APP_PORT": "8688", "APP_DEBUG": "true"}

ALIASES = {"num_workers": "workers"}
TRUE = {"true", "1", "yes", "on"}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def norm_key(k):
    k = str(k).strip().lower()
    if k.startswith("app_"):
        k = k[4:]
    return ALIASES.get(k, k)


def coerce(key, val):
    if key in ("port", "workers"):
        return int(str(val).strip())
    if key == "debug":
        return str(val).strip().lower() in TRUE
    return str(val)


def parse_dotenv(text):
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[norm_key(k)] = v.strip().strip('"').strip("'")
    return out


def os_layer():
    raw = dict(OS_LAYER_DEFAULT)
    for k, v in os.environ.items():
        if k.startswith("APP_") and k != "APP_ENV":
            raw[k] = v
    return {norm_key(k): v for k, v in raw.items()}


def build(overrides):
    merged = dict(DEFAULTS)
    for layer in (YAML_LAYER, parse_dotenv(DOTENV_TEXT), os_layer()):
        for k, v in layer.items():
            merged[norm_key(k)] = v

    for item in overrides:
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        merged[norm_key(k)] = v

    result = {}
    for k, v in merged.items():
        try:
            result[k] = coerce(k, v)
        except (ValueError, TypeError):
            result[k] = DEFAULTS.get(k, v)
    result["api_key"] = "****"
    return result


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/effective-config")
def effective_config(set: List[str] = Query(default=[])):
    return build(set)
