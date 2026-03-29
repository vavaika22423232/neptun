#!/bin/bash
set -euo pipefail

# Cloudflare-only firewall: allow HTTP/HTTPS only from Cloudflare IPs.
# Blocks direct access to the origin server, preventing DDoS bypass.
#
# After running, persist with:
#   iptables-save > /etc/iptables/rules.v4
#   ip6tables-save > /etc/iptables/rules.v6

CHAIN="CLOUDFLARE"

iptables -N "$CHAIN" 2>/dev/null || iptables -F "$CHAIN"

# Cloudflare IPv4 ranges (https://www.cloudflare.com/ips-v4)
for cidr in \
  173.245.48.0/20 \
  103.21.244.0/22 \
  103.22.200.0/22 \
  103.31.4.0/22 \
  141.101.64.0/18 \
  108.162.192.0/18 \
  190.93.240.0/20 \
  188.114.96.0/20 \
  197.234.240.0/22 \
  198.41.128.0/17 \
  162.158.0.0/15 \
  104.16.0.0/13 \
  104.24.0.0/14 \
  172.64.0.0/13 \
  131.0.72.0/22; do
  iptables -A "$CHAIN" -s "$cidr" -j ACCEPT
done

# Localhost
iptables -A "$CHAIN" -s 127.0.0.1 -j ACCEPT

# Drop everything else
iptables -A "$CHAIN" -j DROP

# Remove old jump rules if present
iptables -D INPUT -p tcp --dport 80 -j "$CHAIN" 2>/dev/null || true
iptables -D INPUT -p tcp --dport 443 -j "$CHAIN" 2>/dev/null || true

# Insert jump rules
iptables -I INPUT -p tcp --dport 80 -j "$CHAIN"
iptables -I INPUT -p tcp --dport 443 -j "$CHAIN"

echo "Cloudflare-only firewall applied."
