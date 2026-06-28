#!/bin/bash
# ==========================================
# Test Kali Tools in Container
# ==========================================

echo "Testing Kali tools availability..."

docker exec redteam-agent bash -c '
echo "=== Kali Tools Check ==="

tools=(
    "nmap"
    "hydra"
    "john"
    "sqlmap"
    "nikto"
    "dirb"
    "gobuster"
    "whatweb"
    "wpscan"
    "metasploit"
    "msfconsole"
    "searchsploit"
    "hashcat"
    "john"
    "aircrack-ng"
    "netcat"
    "tcpdump"
    "wireshark"
    "responder"
    "impacket"
)

for tool in "${tools[@]}"; do
    if command -v $tool &> /dev/null; then
        echo "  ✅ $tool"
    elif dpkg -l | grep -q $tool 2>/dev/null; then
        echo "  ⚠️  $tool (installed but not in PATH)"
    else
        echo "  ❌ $tool"
    fi
done

echo ""
echo "=== Python Tools ==="
python3 -c "
tools = [\"nmap\", \"paramiko\", \"impacket\", \"pwntools\", \"requests\", \"bs4\"]
for t in tools:
    try:
        __import__(t)
        print(f'  ✅ {t}')
    except:
        print(f'  ❌ {t}')
"

echo ""
echo "=== Metasplit Status ==="
if command -v msfconsole &> /dev/null; then
    msfconsole -q -x "version; exit" 2>/dev/null || echo "  ⚠️ Metasploit needs database setup"
fi
'