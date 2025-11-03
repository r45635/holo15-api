#!/bin/bash
# Quick security tests with curl

API_URL="http://127.0.0.1:8000"
API_KEY="mplkhLEdJ-LJ-RJm29OIIToQ1pw16rwc"

echo "========================================"
echo "Holo 1.5 API - Quick Security Tests"
echo "========================================"

echo ""
echo "Test 1: Health check (no auth)"
curl -s "$API_URL/health" | jq '.'

echo ""
echo "Test 2: No authentication (should fail 401)"
curl -s -X POST "$API_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model":"Hcompany/Holo1.5-7B","messages":[{"role":"user","content":"Hi"}],"max_tokens":10}' \
  | jq '.'

echo ""
echo "Test 3: With valid authentication"
curl -s -X POST "$API_URL/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"Hcompany/Holo1.5-7B","messages":[{"role":"user","content":"Say hello in one word"}],"max_tokens":10}' \
  | jq '.'

echo ""
echo "Test 4: Check metrics"
curl -s "$API_URL/metrics" \
  -H "Authorization: Bearer $API_KEY" \
  | jq '.'

echo ""
echo "========================================"
echo "Tests completed!"
echo "========================================"
