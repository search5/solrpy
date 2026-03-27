#!/bin/bash
# Test SolrCloud against multiple Solr versions.
# Usage: ./scripts/test_cloud_versions.sh

set -e

SOLR_VERSIONS="6.6 7.7 8.11 9.7 10.0"
RESULTS=()

cleanup() {
    echo "  Cleaning up..."
    docker-compose -f docker/docker-compose-cloud.yml down -v > /dev/null 2>&1 || true
    # Also stop standalone solr10 if running
    docker stop solr10-dev > /dev/null 2>&1 || true
}

for VERSION in $SOLR_VERSIONS; do
    echo ""
    echo "=========================================="
    echo "Testing SolrCloud with Solr ${VERSION}"
    echo "=========================================="

    cleanup

    # Update docker-compose with the target version and appropriate command
    local major=${VERSION%%.*}
    sed -i "s|image: solr:.*|image: solr:${VERSION}|g" docker/docker-compose-cloud.yml
    if [ "$major" -ge 10 ]; then
        sed -i "s|command: .*|command: solr start -f -z zoo:2181|g" docker/docker-compose-cloud.yml
    else
        sed -i "s|command: .*|command: solr start -f -cloud -z zoo:2181|g" docker/docker-compose-cloud.yml
    fi

    echo "  Starting ZooKeeper + 3 Solr ${VERSION} nodes..."
    docker-compose -f docker/docker-compose-cloud.yml up -d 2>&1 | tail -1

    # Wait for cluster
    echo "  Waiting for cluster..."
    for i in $(seq 1 40); do
        if curl -s "http://localhost:8985/solr/admin/collections?action=CLUSTERSTATUS&wt=json" 2>/dev/null | grep -q "live_nodes"; then
            break
        fi
        sleep 2
    done

    # Check live nodes
    NODES=$(curl -s "http://localhost:8985/solr/admin/collections?action=CLUSTERSTATUS&wt=json" 2>/dev/null | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('cluster',{}).get('live_nodes',[])))" 2>/dev/null || echo "0")
    echo "  Live nodes: ${NODES}"

    if [ "$NODES" -lt 2 ]; then
        echo "  ❌ Cluster not ready, skipping"
        RESULTS+=("Solr ${VERSION}: SKIPPED (cluster not ready)")
        continue
    fi

    # Create test collection via Solr CLI (works across all versions)
    echo "  Creating collection..."
    SOLR_CONTAINER=$(docker-compose -f docker/docker-compose-cloud.yml ps -q solr1)
    docker exec "${SOLR_CONTAINER}" solr create_collection -c testcol -shards 2 -replicationFactor 2 -p 8983 > /dev/null 2>&1 || \
      curl -s "http://localhost:8985/solr/admin/collections?action=CREATE&name=testcol&numShards=2&replicationFactor=2&wt=json" > /dev/null 2>&1
    sleep 5

    # Also start standalone Solr 10 on port 8983 for non-cloud tests
    docker run -d --name solr10-dev -p 8983:8983 solr:10.0 solr-precreate core0 > /dev/null 2>&1
    sleep 8
    # Setup standalone schema
    curl -s -X POST "http://localhost:8983/solr/core0/schema" \
      -H "Content-Type: application/json" \
      -d '{
        "add-field": [
          {"name": "user_id", "type": "string", "stored": true, "indexed": true, "multiValued": false},
          {"name": "data", "type": "string", "stored": true, "indexed": true, "multiValued": false},
          {"name": "data_sort", "type": "string", "stored": false, "indexed": true, "multiValued": false},
          {"name": "letters", "type": "string", "stored": true, "indexed": true, "multiValued": true},
          {"name": "creation_time", "type": "pdate", "stored": true, "indexed": true, "multiValued": false},
          {"name": "num", "type": "plong", "stored": true, "indexed": true, "multiValued": false}
        ],
        "add-copy-field": {"source": "data", "dest": "data_sort"},
        "add-field-type": {"name": "knn_vector", "class": "solr.DenseVectorField", "vectorDimension": 3, "similarityFunction": "cosine"}
      }' > /dev/null 2>&1
    curl -s -X POST "http://localhost:8983/solr/core0/schema" \
      -H "Content-Type: application/json" \
      -d '{"add-field": {"name": "embedding", "type": "knn_vector", "stored": true, "indexed": true}}' > /dev/null 2>&1

    # Run cloud tests only
    echo "  Running cloud tests..."
    if poetry run pytest tests/test_cloud.py -q 2>&1 | tee /tmp/solr_cloud_${VERSION}.log | tail -3; then
        RESULT=$(tail -1 /tmp/solr_cloud_${VERSION}.log)
        RESULTS+=("Solr ${VERSION}: ${RESULT}")
    else
        RESULTS+=("Solr ${VERSION}: FAILED (see /tmp/solr_cloud_${VERSION}.log)")
    fi

    # Stop standalone
    docker stop solr10-dev > /dev/null 2>&1 || true
    docker rm solr10-dev > /dev/null 2>&1 || true
done

cleanup
# Restore docker-compose to default version
sed -i "s|image: solr:.*|image: solr:9.7|g" docker/docker-compose-cloud.yml

echo ""
echo "=========================================="
echo "SOLRCLOUD TEST SUMMARY"
echo "=========================================="
for r in "${RESULTS[@]}"; do
    echo "  $r"
done
