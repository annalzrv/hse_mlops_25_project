#!/bin/bash

echo "=========================================="
echo "Real Estate Pipeline Progress Monitor"
echo "=========================================="
echo ""

# Check database count
echo "📊 Database Statistics:"
DB_COUNT=$(docker-compose exec -T postgres psql -U mlops -d real_estate -t -c "SELECT COUNT(*) FROM listings;" 2>/dev/null | tr -d ' ' || echo "N/A")
echo "  Total listings in database: $DB_COUNT"

# Check today's new listings
TODAY_COUNT=$(docker-compose exec -T postgres psql -U mlops -d real_estate -t -c "SELECT COUNT(*) FROM listings WHERE DATE(created_at) = CURRENT_DATE;" 2>/dev/null | tr -d ' ' || echo "N/A")
echo "  New listings today: $TODAY_COUNT"

# Check pipeline container status
echo ""
echo "🔄 Pipeline Status:"
CONTAINER_STATUS=$(docker-compose ps data_loader --format json 2>/dev/null | grep -o '"State":"[^"]*"' | cut -d'"' -f4 || echo "N/A")
echo "  Container status: $CONTAINER_STATUS"

if [ "$CONTAINER_STATUS" = "running" ]; then
    echo "  ✅ Pipeline is running"
    
    echo ""
    echo "📝 Recent Logs (last 10 lines):"
    docker-compose logs --tail=10 data_loader 2>&1 | sed 's/^/  /'
else
    echo "  ⚠️  Pipeline is not running"
fi

echo ""
echo "=========================================="
