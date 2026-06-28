#!/bin/bash
# ==========================================
# Red Team Agent - Start Script
# ==========================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  Starting Red Team Agent${NC}"
echo -e "${GREEN}=========================================${NC}"

# Start core services
echo -e "${BLUE}[*] Starting core services...${NC}"
docker-compose up -d qdrant neo4j
echo -e "${GREEN}[✓] Core services started${NC}"

# Wait for services to be healthy
echo -e "${BLUE}[*] Waiting for services to be ready...${NC}"
echo -e "${YELLOW}  This may take 30-60 seconds...${NC}"

# Wait for Qdrant
for i in {1..30}; do
    if curl -s http://localhost:6333/health > /dev/null 2>&1; then
        echo -e "${GREEN}[✓] Qdrant is ready${NC}"
        break
    fi
    sleep 2
done

# Wait for Neo4j
for i in {1..30}; do
    if docker exec redteam-neo4j cypher-shell -u neo4j -p password "RETURN 1" > /dev/null 2>&1; then
        echo -e "${GREEN}[✓] Neo4j is ready${NC}"
        break
    fi
    sleep 2
done

# Start optional services
if [ "$USE_OLLAMA" = "true" ]; then
    echo -e "${BLUE}[*] Starting Ollama (GPU)...${NC}"
    docker-compose --profile gpu up -d ollama
fi

if [ ! -z "$LETTA_TOKEN" ]; then
    echo -e "${BLUE}[*] Starting Letta Memory...${NC}"
    docker-compose --profile memory up -d letta
fi

# Start agent
echo -e "${BLUE}[*] Starting Red Team Agent...${NC}"
docker-compose up -d redteam-agent
echo -e "${GREEN}[✓] Agent started${NC}"

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  Agent is Running!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "Services:"
echo -e "  ${BLUE}Qdrant Dashboard:${NC}  http://localhost:6333/dashboard"
echo -e "  ${BLUE}Neo4j Browser:${NC}    http://localhost:7474"
echo -e "  ${BLUE}Neo4j Credentials:${NC} neo4j/password"
echo ""
echo -e "To run a scan:"
echo -e "  ${YELLOW}docker exec -it redteam-agent python main.py <TARGET_IP>${NC}"
echo ""
echo -e "Example:"
echo -e "  ${YELLOW}docker exec -it redteam-agent python main.py 192.168.1.100 -o \"Complete security audit\"${NC}"
echo ""
echo -e "To view logs:"
echo -e "  ${YELLOW}docker logs -f redteam-agent${NC}"
echo ""
echo -e "To stop:"
echo -e "  ${YELLOW}./scripts/stop.sh${NC}"

# If target provided as argument, run immediately
if [ ! -z "$1" ]; then
    TARGET=$1
    OBJECTIVE=${2:-"Complete security assessment"}
    STEALTH=${3:-"high"}
    
    echo -e "${BLUE}[*] Auto-running scan against $TARGET...${NC}"
    docker exec redteam-agent python main.py "$TARGET" -o "$OBJECTIVE" -s "$STEALTH"
fi