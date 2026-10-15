#!/bin/bash

for file in parameters/*.json; do
    [ -e "$file" ] || continue
    echo "Processing: $file"
    python app/plot_cli.py "$file"
done
