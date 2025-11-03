#!/bin/bash
# Quick test script to run benchmarks once server is ready

# Try both common localhost addresses (some systems prefer one over the other)
SERVER_URL="http://127.0.0.1:8000"
ALT_SERVER_URL="http://127.0.0.1:8000"

echo "Waiting for server to be ready..."
SERVER_READY=false

for i in {1..30}; do
    # Try 127.0.0.1 first
    if curl -s $SERVER_URL/health 2>/dev/null | grep -q '"status":"ok"'; then
        echo "✓ Server is ready at $SERVER_URL!"
        SERVER_READY=true
        break
    fi
    # Try hostname
    if curl -s $ALT_SERVER_URL/health 2>/dev/null | grep -q '"status":"ok"'; then
        echo "✓ Server is ready at $ALT_SERVER_URL!"
        SERVER_URL=$ALT_SERVER_URL
        SERVER_READY=true
        break
    fi
    echo "  Attempt $i/30..."
    sleep 2
done

if [ "$SERVER_READY" = false ]; then
    echo "❌ Server not responding at $SERVER_URL or $ALT_SERVER_URL"
    echo "Make sure server is running with: ./launch.sh"
    exit 1
fi

echo ""
echo "==================== TEXT-ONLY BENCHMARK ===================="
echo ""
source .venv/bin/activate
python ./scripts/bench_holo15.py --server $SERVER_URL --runs 10 --prompt "Say hello in one sentence."

echo ""
echo ""
echo "==================== IMAGE BENCHMARK ===================="
echo ""
python ./scripts/bench_holo15.py --server $SERVER_URL --runs 10 --image cat_image.jpg --prompt "What do you see in this image?"

echo ""
echo "✅ Benchmarks complete!"
echo ""
echo "Check the results:"
echo "  - bench_results.csv (CSV data)"
echo "  - bench_report.md (formatted report)"
