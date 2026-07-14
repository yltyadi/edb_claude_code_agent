# EDB Macro Intelligence Agent — Hugging Face Docker Space
#
# A Docker Space (not the Python-only Gradio Space) is required because the
# Claude Agent SDK spawns the `claude` CLI, a Node program installed via npm.
# The SDK resolves it with shutil.which("claude") and needs Claude Code >= 2.0.0.
FROM python:3.11-slim

# ── System deps + Node 20 (for the Claude Code CLI) ───────────────────────────
# Trimmed to reduce final image size: strip apt/npm caches, docs, and man pages
# after install — none of it is needed at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code --no-audit --no-fund \
    && npm cache clean --force \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.npm /tmp/* /usr/share/doc/* /usr/share/man/*

# HF Spaces run as a non-root user with UID 1000.
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860
WORKDIR /home/user/app

# ── Python deps ───────────────────────────────────────────────────────────────
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── App ───────────────────────────────────────────────────────────────────────
COPY --chown=user . .
USER user

EXPOSE 7860
CMD ["python", "app.py"]
