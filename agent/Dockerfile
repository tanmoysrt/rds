# Build stage - Create PEX environment only
FROM python:3.12-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONWARNINGS="ignore::RuntimeWarning"

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    pkg-config \
    libssl-dev \
    libmariadb-dev \
    build-essential \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Install Python build tools
RUN pip install --upgrade pip poetry pex
RUN poetry self add poetry-plugin-export

WORKDIR /app

# Copy only dependency files for caching
COPY pyproject.toml poetry.lock* ./

# Export requirements - no wheel building needed
RUN poetry export -f requirements.txt --without-hashes --only=main -o requirements.txt

# Create PEX environment only (no app code inside)
RUN pex -r requirements.txt \
    -o env.pex \
    --venv \
    --include-tools \
    --python-shebang="/usr/bin/env python3.12"

# Runtime stage
FROM python:3.12-slim as runtime

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmariadb3 \
    libssl3 \
    ca-certificates \
    vim-tiny \
    sqlite3 \
    supervisor \
    redis-server \
    systemd \
    dbus \
    rsync \
    tar \
    curl \
    netcat-openbsd \
    htop \
    procps \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Symlink vim
RUN ln -s /usr/bin/vim.tiny /usr/bin/vim

# Copy PEX environment
COPY --from=builder /app/env.pex /usr/bin/pex-env
RUN chmod +x /usr/bin/pex-env


# Copy your project source code
COPY . /app

# Basic vim config
RUN echo 'set nocompatible' > /root/.vimrc && \
    echo 'set number' >> /root/.vimrc && \
    echo 'set autoindent' >> /root/.vimrc && \
    echo 'set tabstop=4' >> /root/.vimrc && \
    echo 'set shiftwidth=4' >> /root/.vimrc && \
    echo 'set expandtab' >> /root/.vimrc && \
    echo 'set hlsearch' >> /root/.vimrc && \
    echo 'set ignorecase' >> /root/.vimrc && \
    echo 'set smartcase' >> /root/.vimrc && \
    echo 'set background=dark' >> /root/.vimrc

WORKDIR /app

ENV EDITOR=vim
ENV PYTHONWARNINGS="ignore::RuntimeWarning"
ENV PYTHONPATH="/app"

# Write rqscheduler script
RUN echo 'import re' > /app/rqscheduler.py && \
    echo 'import sys' >> /app/rqscheduler.py && \
    echo 'from rq_scheduler.scripts.rqscheduler import main' >> /app/rqscheduler.py && \
    echo 'if __name__ == "__main__":' >> /app/rqscheduler.py && \
    echo '    sys.argv[0] = re.sub(r"(-script\.pyw|\.exe)?$", "", sys.argv[0])' >> /app/rqscheduler.py && \
    echo '    sys.exit(main())' >> /app/rqscheduler.py

# Write rq cli script
RUN echo 'import re' > /app/rq_cli.py && \
    echo 'import sys' >> /app/rq_cli.py && \
    echo 'from rq.cli import main' >> /app/rq_cli.py && \
    echo 'if __name__ == "__main__":' >> /app/rq_cli.py && \
    echo '    sys.argv[0] = re.sub(r"(-script\.pyw|\.exe)?$", "", sys.argv[0])' >> /app/rq_cli.py && \
    echo '    sys.exit(main())' >> /app/rq_cli.py

ENTRYPOINT ["supervisord", "-c", "/app/supervisord.conf"]