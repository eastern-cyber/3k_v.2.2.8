# KokKokKok 3k_v.2.2.7

## Requirements
Python: https://www.python.org/ 
Visual Studio Code: https://code.visualstudio.com/ (or any other editor)

## Set up environment
Open project folder in editor eg. Visual Studio Code
Open terminal in the project directory


## Install Dependencies with uv (Recommended)
uv: https://docs.astral.sh/uv/ 

### Install dependencies
uv sync

### Migrate to database
uv run manage.py makemigrations
uv run manage.py migrate
uv run manage.py createsuperuser

### Run application
uv run manage.py runserver
http://localhost:8000


## Install Dependencies with pip

### Create virtual environment (Mac / Linux)
python3 -m venv .venv
source .venv/bin/activate

### Install dependencies
pip install -r requirements.txt

## Migrate to database
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

## Run application
python manage.py runserver
http://localhost:8000

# 3k_v.2.2.7
# 3k_v.2.2.8
