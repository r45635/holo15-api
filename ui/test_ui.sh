#!/bin/bash
# Quick test to verify UI is working
echo "Testing UI components..."

cd "$(dirname "$0")"

# Check if files exist
echo "✓ Checking files..."
for file in index.html app.js styles.css; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing: $file"
        exit 1
    fi
    echo "  ✓ $file exists"
done

# Check JavaScript syntax
echo "✓ Checking JavaScript syntax..."
if command -v node &> /dev/null; then
    if node --check app.js 2>/dev/null; then
        echo "  ✓ JavaScript syntax OK"
    else
        echo "  ❌ JavaScript syntax errors"
        node --check app.js
        exit 1
    fi
else
    echo "  ⚠️  Node.js not found, skipping syntax check"
fi

# Check if server is running
echo "✓ Checking API server..."
if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "  ✓ API server is running on 127.0.0.1:8000"
else
    echo "  ⚠️  API server not running on 127.0.0.1:8000"
    echo "     Start it with: ../launch.sh"
fi

echo ""
echo "✅ All checks passed!"
echo ""
echo "To start the UI server:"
echo "  python3 -m http.server 5500"
echo ""
echo "Then open: http://127.0.0.1:5500"
