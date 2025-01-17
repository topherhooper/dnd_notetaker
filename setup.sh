#!/bin/bash
# python3 -m venv venv
# source venv/bin/activate
# pip install -r requirements.txt

# Create config template if it doesn't exist
if [ ! -f config.json ]; then
    echo "Creating config template..."
    cat > config.json << EOF
{
    "email": {
        "email": "your_email@gmail.com",
        "password": "your_password",
        "imap_server": "imap.gmail.com"
    },
    "openai_api_key": "your_openai_api_key"
}
EOF
fi

# Create main script if it doesn't exist
if [ ! -f main.py ]; then
    echo "Creating main script..."
    touch main.py
fi

# Create component files if they don't exist
declare -a components=("email_handler.py" "audio_processor.py" "transcriber.py" "note_generator.py")

for component in "${components[@]}"; do
    if [ ! -f "$component" ]; then
        echo "Creating $component..."
        touch "$component"
    fi
done

# Create README if it doesn't exist
if [ ! -f README.md ]; then
    echo "Creating README..."
    touch README.md
fi

# Create output directory for processed files
echo "Creating output directory..."
mkdir -p output

echo "Setup completed!"
echo "Please update config.json with your credentials before running the scripts."
echo "You can now start using the virtual environment with: source venv/bin/activate"