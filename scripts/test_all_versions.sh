#!/bin/bash
# Test solrpy against multiple Solr versions locally.
# Usage: ./scripts/test_all_versions.sh

set -e

SOLR_VERSIONS="6.6 7.7 8.11 9.7 10.0"
CONTAINER_NAME="solr-compat-test"
PORT=8983
RESULTS=()

setup_schema() {
    local version=$1
    local major=${version%%.*}

    # Wait for Solr to start
    for i in $(seq 1 30); do
        if curl -s "http://localhost:${PORT}/solr/core0/admin/ping?wt=json" | grep -q OK; then
            break
        fi
        sleep 1
    done

    # Common fields
    curl -s -X POST "http://localhost:${PORT}/solr/core0/schema" \
      -H "Content-Type: application/json" \
      -d '{
        "add-field": [
          {"name": "user_id", "type": "string", "stored": true, "indexed": true, "multiValued": false},
          {"name": "data", "type": "string", "stored": true, "indexed": true, "multiValued": false},
          {"name": "data_sort", "type": "string", "stored": false, "indexed": true, "multiValued": false},
          {"name": "letters", "type": "string", "stored": true, "indexed": true, "multiValued": true}
        ],
        "add-copy-field": {"source": "data", "dest": "data_sort"}
      }' > /dev/null 2>&1

    # Date/numeric field types: Solr 6 uses tdate/tlong, Solr 7+ uses pdate/plong
    if [ "$major" -ge 7 ]; then
        local date_type="pdate"
        local num_type="plong"
    else
        local date_type="tdate"
        local num_type="tlong"
    fi
    curl -s -X POST "http://localhost:${PORT}/solr/core0/schema" \
      -H "Content-Type: application/json" \
      -d "{\"add-field\": {\"name\": \"creation_time\", \"type\": \"${date_type}\", \"stored\": true, \"indexed\": true, \"multiValued\": false}}" > /dev/null 2>&1
    curl -s -X POST "http://localhost:${PORT}/solr/core0/schema" \
      -H "Content-Type: application/json" \
      -d "{\"add-field\": {\"name\": \"num\", \"type\": \"${num_type}\", \"stored\": true, \"indexed\": true, \"multiValued\": false}}" > /dev/null 2>&1

    # KNN fields for Solr 9+
    if [ "$major" -ge 9 ]; then
        curl -s -X POST "http://localhost:${PORT}/solr/core0/schema" \
          -H "Content-Type: application/json" \
          -d '{
            "add-field-type": {
              "name": "knn_vector",
              "class": "solr.DenseVectorField",
              "vectorDimension": 3,
              "similarityFunction": "cosine"
            }
          }' > /dev/null 2>&1
        curl -s -X POST "http://localhost:${PORT}/solr/core0/schema" \
          -H "Content-Type: application/json" \
          -d '{"add-field": {"name": "embedding", "type": "knn_vector", "stored": true, "indexed": true}}' > /dev/null 2>&1

        # Index vector test data
        curl -s -X POST "http://localhost:${PORT}/solr/core0/update?commit=true" \
          -H "Content-Type: application/json" \
          -d '[
            {"id": "vec1", "data": "first",  "embedding": [1.0, 0.0, 0.0]},
            {"id": "vec2", "data": "second", "embedding": [0.0, 1.0, 0.0]},
            {"id": "vec3", "data": "third",  "embedding": [0.0, 0.0, 1.0]},
            {"id": "vec4", "data": "similar","embedding": [0.9, 0.1, 0.0]},
            {"id": "vec5", "data": "mixed",  "embedding": [0.5, 0.5, 0.0]}
          ]' > /dev/null 2>&1
    fi

    echo "  Schema setup complete"
}

for VERSION in $SOLR_VERSIONS; do
    echo ""
    echo "=========================================="
    echo "Testing against Solr ${VERSION}"
    echo "=========================================="

    # Stop any existing container
    docker stop ${CONTAINER_NAME} > /dev/null 2>&1 || true
    docker rm ${CONTAINER_NAME} > /dev/null 2>&1 || true

    # Start Solr
    echo "  Starting Solr ${VERSION}..."
    docker run -d --name ${CONTAINER_NAME} -p ${PORT}:8983 "solr:${VERSION}" solr-precreate core0 > /dev/null 2>&1

    # Setup schema
    setup_schema "${VERSION}"

    # Run tests
    echo "  Running tests..."
    if poetry run pytest tests/ -q 2>&1 | tee /tmp/solr_test_${VERSION}.log | tail -3; then
        RESULT=$(tail -1 /tmp/solr_test_${VERSION}.log)
        RESULTS+=("Solr ${VERSION}: ${RESULT}")
    else
        RESULTS+=("Solr ${VERSION}: FAILED (see /tmp/solr_test_${VERSION}.log)")
    fi

    # Cleanup
    docker stop ${CONTAINER_NAME} > /dev/null 2>&1
    docker rm ${CONTAINER_NAME} > /dev/null 2>&1
done

echo ""
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
for r in "${RESULTS[@]}"; do
    echo "  $r"
done
