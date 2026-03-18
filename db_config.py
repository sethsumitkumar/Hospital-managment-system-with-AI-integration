import os

# Get the absolute path to the directory where this file is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the path for the SQLite database file (it will be created in your project folder)
# This is much easier for deployment as it's just a local file.
DATABASE_PATH = os.path.join(BASE_DIR, 'hospital.db')

db_config = {
    'database': DATABASE_PATH
}