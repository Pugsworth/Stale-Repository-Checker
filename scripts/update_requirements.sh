#! /bin/bash
echo "Updating requirements.txt"
pipreqs .  --ignore .venv --force
