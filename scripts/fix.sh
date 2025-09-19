#!/bin/bash
# Auto-fix script for the secure package manager backend

echo "Running auto-fix for formatting issues..."

# Change to backend directory
cd backend

# Run black to fix formatting
echo "Running black (auto-format)..."
python -m black .

if [ $? -eq 0 ]; then
    echo "Black formatting applied!"
else
    echo "Black formatting failed!"
fi

# Run isort to fix import sorting
echo "Running isort (auto-fix imports)..."
python -m isort .

if [ $? -eq 0 ]; then
    echo "isort import sorting applied!"
else
    echo "isort import sorting failed!"
fi

# Return to original directory
cd ..

echo "Auto-fix completed!"
echo "Note: Multi-line f-string issues need to be fixed manually."
