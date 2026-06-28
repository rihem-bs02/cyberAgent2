#!/bin/bash
# ==========================================
# Quick Docker Run Script
# ==========================================

if [ -z "$1" ]; then
    echo "Usage: ./scripts/docker-run.sh <TARGET_IP> [objective] [stealth_level]"
    echo ""
    echo "Examples:"
    echo "  ./scripts/docker-run.sh 192.168.1.100"
    echo "  ./scripts/docker-run.sh 192.168.1.100 \"Full security audit\" high"
    echo "  ./scripts/docker-run.sh example.com \"Web app test\" medium --safe-mode"
    exit 1
fi

TARGET=$1
OBJECTIVE=${2:-"Complete security assessment"}
STEALTH=${3:-"high"}

echo "========================================="
echo "  Red Team Agent - Quick Run"
echo "========================================="
echo "Target: $TARGET"
echo "Objective: $OBJECTIVE"
echo "Stealth: $STEALTH"
echo "========================================="

# Build if needed
if ! docker images | grep -q redteam-agent; then
    echo "Building agent image..."
    docker-compose build redteam-agent
fi

# Ensure services are running
docker-compose up -d qdrant neo4j

# Wait for services
echo "Waiting for services..."
sleep 10

# Run scan
docker-compose run --rm redteam-agent python main.py "$TARGET" -o "$OBJECTIVE" -s "$STEALTH" "${@:4}"

echo ""
echo "Scan complete! Check reports/ directory for results."