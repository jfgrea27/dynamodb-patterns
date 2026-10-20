port := env_var_or_default("DYNAMODB_PORT", "8000")
export DYNAMODB_ENDPOINT := env_var_or_default("DYNAMODB_ENDPOINT", "http://localhost:" + port)

# list recipes
default:
    @just --list

# install python deps and pull the DynamoDB Local image
setup:
    uv sync
    docker compose pull

# start DynamoDB Local and wait until it answers
up:
    docker compose up -d
    @until curl -s -o /dev/null {{DYNAMODB_ENDPOINT}}; do sleep 0.5; done
    @echo "DynamoDB Local is up on {{DYNAMODB_ENDPOINT}}"

# stop DynamoDB Local (data in docker/dynamodb is kept)
down:
    docker compose down

# stop DynamoDB Local and delete its data
reset: down
    rm -rf docker/dynamodb

# list the patterns
patterns:
    @ls -d patterns/*/[0-9]*/ | sed -E 's#patterns/([^/]+)/([^/]+)/#\1  \2#' | column -t

# run a pattern by number, e.g. `just run 4` (set LOG_REQUESTS=0 to hide requests)
run n:
    #!/usr/bin/env bash
    set -euo pipefail
    num=$(printf '%02d' "$((10#{{n}}))")
    script=$(ls patterns/*/"$num"-*/"$num"-*.py 2>/dev/null) || { echo "no pattern $num (see: just patterns)"; exit 1; }
    uv run python "$script"

# print a pattern's write-up, e.g. `just read 4`
read n:
    #!/usr/bin/env bash
    set -euo pipefail
    num=$(printf '%02d' "$((10#{{n}}))")
    cat patterns/*/"$num"-*/"$num"-*.md

# run every pattern and report failures
run-all:
    #!/usr/bin/env bash
    fail=0
    for script in patterns/*/[0-9]*/[0-9]*.py; do
        if LOG_REQUESTS=0 uv run python "$script" > /dev/null 2> /tmp/dynamodb-patterns.err; then
            echo "ok    $script"
        else
            echo "FAIL  $script"; tail -3 /tmp/dynamodb-patterns.err; fail=1
        fi
    done
    exit $fail
