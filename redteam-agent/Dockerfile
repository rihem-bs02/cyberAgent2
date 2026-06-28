# ==========================================
# Red Team Agent - Kali Full (with Metasploit, Burp, etc.)
# ==========================================

FROM kalilinux/kali-rolling:latest

LABEL maintainer="Red Team Agent"
LABEL description="Autonomous Red Team AI Agent - Kali Full"
LABEL version="3.0-kali-full"

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install FULL Kali toolset
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Full Kali metapackages
    kali-linux-large \
    kali-linux-everything \
    # Additional tools
    metasploit-framework \
    burpsuite \
    zaproxy \
    sqlmap \
    wpscan \
    joomscan \
    # Development
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    golang \
    rustc \
    cargo \
    nodejs \
    npm \
    # Network
    net-tools \
    iproute2 \
    # Utilities
    jq \
    vim \
    tmux \
    screen \
    htop \
    strace \
    ltrace \
    gdb \
    # Clean
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Initialize Metasploit database
RUN msfdb init || true

# Install Python packages
RUN pip3 install --no-cache-dir --break-system-packages \
    python-nmap \
    paramiko \
    impacket \
    pwntools \
    requests \
    beautifulsoup4 \
    lxml \
    aiohttp \
    httpx \
    pymetasploit3 \
    python-masscan \
    shodan \
    censys

# Copy requirements and install
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Setup wordlists
RUN mkdir -p /usr/share/wordlists && \
    if [ -f /usr/share/wordlists/rockyou.txt.gz ]; then \
        gunzip /usr/share/wordlists/rockyou.txt.gz; \
    fi

# Create directories
RUN mkdir -p /app/reports /app/logs /app/qdrant_data && \
    mkdir -p /home/redteam/.msf4 /home/redteam/.burp

# Copy app
COPY agents/ ./agents/
COPY core/ ./core/
COPY tools/ ./tools/
COPY graph/ ./graph/
COPY knowledge/ ./knowledge/
COPY memory/ ./memory/
COPY utils/ ./utils/
COPY main.py .
COPY .env .

# Setup user
RUN useradd -m -s /bin/bash -G sudo redteam && \
    echo "redteam:redteam" | chpasswd && \
    echo "redteam ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    chown -R redteam:redteam /app /home/redteam

USER redteam
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)" || exit 1

ENTRYPOINT ["python3", "main.py"]
CMD ["--help"]