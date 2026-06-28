#!/bin/bash
# ==========================================
# Red Team Agent - Kali Linux Setup
# ==========================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${PURPLE}=========================================${NC}"
echo -e "${PURPLE}  🐉 Red Team Agent - Kali Setup${NC}"
echo -e "${PURPLE}=========================================${NC}"

# Check if running on Kali
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ "$ID" == "kali" ]]; then
        echo -e "${GREEN}[✓] Running on Kali Linux ${VERSION}${NC}"
    else
        echo -e "${YELLOW}[!] Not running on Kali. Some features may not work.${NC}"
    fi
fi

# Check Docker
echo -e "${BLUE}[*] Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}[!] Installing Docker...${NC}"
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose
    sudo systemctl enable docker --now
    sudo usermod -aG docker $USER
    echo -e "${GREEN}[✓] Docker installed. Please log out and back in.${NC}"
else
    echo -e "${GREEN}[✓] Docker is installed${NC}"
fi

# Create directories
echo -e "${BLUE}[*] Creating directories...${NC}"
mkdir -p {reports,logs,qdrant_data,neo4j_data,neo4j_logs,wordlists}
echo -e "${GREEN}[✓] Directories created${NC}"

# Check for Kali tools
echo -e "${BLUE}[*] Checking Kali tools...${NC}"
TOOLS=("nmap" "hydra" "john" "sqlmap" "nikto" "dirb" "gobuster" "metasploit")
for tool in "${TOOLS[@]}"; do
    if command -v $tool &> /dev/null; then
        echo -e "  ${GREEN}[✓]${NC} $tool"
    else
        echo -e "  ${YELLOW}[!]${NC} $tool (will be available in container)"
    fi
done

# Setup wordlists
echo -e "${BLUE}[*] Setting up wordlists...${NC}"
if [ -f /usr/share/wordlists/rockyou.txt.gz ]; then
    echo -e "${YELLOW}[*] Extracting rockyou.txt...${NC}"
    sudo gunzip -k /usr/share/wordlists/rockyou.txt.gz 2>/dev/null || true
fi
echo -e "${GREEN}[✓] Wordlists ready${NC}"

# Copy .env if not exists
if [ ! -f .env ]; then
    echo -e "${BLUE}[*] Creating .env file...${NC}"
    cat > .env << 'EOF'
# LLM API Keys
GROQ_API_KEY=your_groq_api_key_here

# Models
GROQ_MODEL_HEAVY=llama-3.3-70b-versatile
GROQ_MODEL_FAST=qwen/qwen3-32b

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_PATH=/app/qdrant_data

# Neo4j
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASS=password

# Campaign (Kali defaults - less safe)
SAFE_MODE=false
STEALTH_LEVEL=high
LOG_LEVEL=INFO
TARGET_ENV=medflow
EOF
    echo -e "${YELLOW}[!] Edit .env with your API keys${NC}"
fi

# Build
echo -e "${BLUE}[*] Building Kali agent image...${NC}"
docker-compose -f docker-compose-kali.yml build
echo -e "${GREEN}[✓] Image built${NC}"

# Pull services
echo -e "${BLUE}[*] Pulling service images...${NC}"
docker-compose -f docker-compose-kali.yml pull qdrant neo4j
echo -e "${GREEN}[✓] Services pulled${NC}"

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  🐉 Kali Setup Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "Start the agent:"
echo -e "  ${YELLOW}docker-compose -f docker-compose-kali.yml up -d${NC}"
echo ""
echo -e "Run a scan:"
echo -e "  ${YELLOW}docker exec -it redteam-agent python3 main.py <TARGET>${NC}"
echo ""
echo -e "Kali shell with all tools:"
echo -e "  ${YELLOW}docker exec -it redteam-agent /bin/bash${NC}"