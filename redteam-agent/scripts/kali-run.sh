#!/bin/bash
# ==========================================
# Kali Quick Run Script
# ==========================================

PURPLE='\033[0;35m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${PURPLE}🐉 Kali Red Team Agent${NC}"

# Check if services are running
if ! docker ps | grep -q redteam-qdrant; then
    echo "Starting services..."
    docker-compose -f docker-compose-kali.yml up -d qdrant neo4j
    echo "Waiting for services..."
    sleep 20
fi

# Check if agent is running
if ! docker ps | grep -q redteam-agent; then
    echo "Starting agent..."
    docker-compose -f docker-compose-kali.yml up -d redteam-agent
    sleep 5
fi

# Run scan if target provided
if [ ! -z "$1" ]; then
    TARGET=$1
    OBJECTIVE=${2:-"Complete security assessment"}
    
    echo ""
    echo -e "${GREEN}🎯 Target: $TARGET${NC}"
    echo -e "${GREEN}📋 Objective: $OBJECTIVE${NC}"
    echo ""
    
    docker exec -it redteam-agent python3 main.py "$TARGET" -o "$OBJECTIVE"
else
    echo ""
    echo "Usage: ./scripts/kali-run.sh <TARGET> [OBJECTIVE]"
    echo ""
    echo "Examples:"
    echo "  ./scripts/kali-run.sh 192.168.1.100"
    echo "  ./scripts/kali-run.sh example.com \"Web app pentest\""
    echo ""
    echo "Interactive shell:"
    echo "  docker exec -it redteam-agent /bin/bash"
fi