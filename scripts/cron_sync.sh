#!/bin/bash
# NyTex Sync System Cron Job Wrapper
# Generated automatically - do not edit manually

# Set up environment
export PATH="/Users/joshgoble/.cursor/extensions/ms-python.python-2025.6.1-darwin-arm64/python_files/deactivate/bash:/Users/joshgoble/code/nytexfireworks/nytex_dashboard/.venv/bin:/usr/local/opt/python/libexec/bin:/Users/joshgoble/.cursor/extensions/ms-python.python-2025.6.1-darwin-arm64/python_files/deactivate/bash:/Users/joshgoble/code/nytexfireworks/nytex_dashboard/.venv/bin:/usr/local/bin:/System/Cryptexes/App/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/local/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/appleinternal/bin:/Users/joshgoble/.cursor/extensions/ms-python.python-2025.6.1-darwin-arm64/python_files/deactivate/bash:/Users/joshgoble/code/nytexfireworks/nytex_dashboard/.venv/bin:/Users/joshgoble/google-cloud-sdk/bin:/usr/local/opt/python@3.11/bin"
export VIRTUAL_ENV="/Users/joshgoble/code/nytexfireworks/nytex_dashboard/.venv"

# Change to project directory
cd "/Users/joshgoble/code/nytexfireworks/nytex_dashboard"

# Load environment variables
if [ -f .env.local ]; then
    export $(cat .env.local | grep -v '^#' | xargs)
fi

# Run the sync orchestrator
"/Users/joshgoble/code/nytexfireworks/nytex_dashboard/.venv/bin/python" scripts/sync_orchestrator.py "$@" >> logs/cron.log 2>&1
