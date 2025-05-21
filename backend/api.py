from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from sanction_search_v2 import sdnlist, uae_list, unsanctionslist, SanctionedPerson
import numpy as np
import cv2
from datetime import datetime
import os
import re
import argparse
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from typing import Optional, Dict, Any, List, Tuple
import pickle
from pydantic import BaseModel
from tqdm import tqdm
from passporteye import read_mrz
import base64
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from scraper import find_suspicious_links

# Global variable to store sanctioned persons
SANCTIONED_PERSONS = []

# Path to pickle file
PICKLE_FILE = 'sanctioned_people_simplified.pkl'

@asynccontextmanager
async def lifespan(app: FastAPI):
    SANCTIONED_PERSONS = load_sanctions_list(PICKLE_FILE)
    yield
    # Cleanup code
    SANCTIONED_PERSONS = []
    # Shutdown the scheduler when the app is stopped
    scheduler.shutdown()

app = FastAPI(title="Sanctions Check API", description="API for checking passport images against sanctions lists", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SanctionsCheckResponse(BaseModel):
    success: bool
    message: str
    match_found: bool
    match_details: Optional[Dict[str, Any]] = None

def read_passport_image(image) -> Optional[Tuple[str, str]]:
    """
    Reads the MRZ from a passport image and returns the full name.
    Returns tuple of (given_names, surname) or None if failed
    """
    try:
        # Convert numpy array to temporary image file if needed
        if isinstance(image, np.ndarray):
            cv2.imwrite('temp_passport.jpg', image)
            image_path = 'temp_passport.jpg'
        else:
            image_path = image

        # Read the MRZ from the image
        mrz = read_mrz(image_path)
        
        # Clean up temporary file if it was created
        if isinstance(image, np.ndarray) and os.path.exists('temp_passport.jpg'):
            os.remove('temp_passport.jpg')

        if mrz is not None:
            mrz_data = mrz.to_dict()
            # Clean up the names
            names = mrz_data['names']
            names = re.split(r'\s+K', names)[0]  # Remove any K suffix
            names = names.strip()
            surname = mrz_data['surname'].strip()
            return (names, surname)
        else:
            print("MRZ not detected.")
            return None
    except Exception as e:
        print(f"Error reading MRZ: {e}")
        return None

def load_sanctions_list(pickle_file='sanctioned_people_simplified.pkl'):
    """Load the sanctions list from pickle file"""
    try:
        with open(pickle_file, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"Error loading sanctions list: {e}")
        return []

def check_sanctions(name: str, sanctioned_persons) -> Optional[dict]:
    """
    Check if a name appears in the sanctions list
    Returns the sanctioned person's details if found, None otherwise
    """
    if not name or not sanctioned_persons:
        return None
        
    name = name.lower().strip()
    for person in sanctioned_persons:
        # Check main name
        if person.name and name in person.name.lower():
            return person
            
        # Check aliases
        for alias_type in ['good_quality', 'low_quality']:
            for alias in person.aliases.get(alias_type, []):
                if alias and name in alias.lower():
                    return person
    return None


def reprocess_sanctions_data():
    """Reprocess sanctions data from PDFs and update pickle file"""
    try:
        print("Starting sanctions data reprocessing...")
        
        # Process all sanctions lists
        all_sanctioned_persons = []
        
        # Process SDN list
        if os.path.exists("sdnlist.pdf"):
            sdn_persons = sdnlist()
            all_sanctioned_persons.extend(sdn_persons)
        
        # Process UN sanctions
        if os.path.exists("unsanctions.pdf"):
            un_persons = unsanctionslist()
            all_sanctioned_persons.extend(un_persons)
        
        # Process UAE sanctions
        uae_pdf = 'Copy of SL_1 (24052021) V.2 (1).pdf'
        if os.path.exists(uae_pdf):
            uae_persons = uae_list(uae_pdf)
            all_sanctioned_persons.extend(uae_persons)
        
        # Save processed data
        with open(PICKLE_FILE, 'wb') as f:
            pickle.dump(all_sanctioned_persons, f)
        
        # Update global variable
        global SANCTIONED_PERSONS
        SANCTIONED_PERSONS = all_sanctioned_persons
        
        print(f"Reprocessing complete. Total entries: {len(all_sanctioned_persons)}")
        return True
    except Exception as e:
        print(f"Error during reprocessing: {e}")
        return False

def load_sanctioned_data():
    """Load sanctions data from pickle file"""
    global SANCTIONED_PERSONS
    try:
        SANCTIONED_PERSONS = load_sanctions_list(PICKLE_FILE)
        print(f"Loaded {len(SANCTIONED_PERSONS)} sanctioned persons from pickle file")
    except Exception as e:
        print(f"Error loading sanctions data: {e}")
        SANCTIONED_PERSONS = []

# Initialize scheduler
scheduler = BackgroundScheduler()
# Set to 1 week interval
interval = IntervalTrigger(weeks=1)
scheduler.start()
scheduler.add_job(reprocess_sanctions_data, interval)

def initialize_data(force_reprocess: bool = False):
    """Initialize sanctions data, optionally forcing reprocessing"""
    if force_reprocess or not os.path.exists(PICKLE_FILE):
        print("Forcing reprocessing of sanctions data...")
        reprocess_sanctions_data()
    else:
        print("Loading existing sanctions data...")
        load_sanctioned_data()

class Base64Request(BaseModel):
    image_data: str  # Base64 encoded image string

@app.post("/check-passport-base64/", response_model=SanctionsCheckResponse)
async def check_passport_base64(request: Base64Request):
    """
    Check a passport image from base64 encoded string against sanctions lists
    """
    try:
        # Decode base64 image
        image_bytes = base64.b64decode(request.image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Process passport
        name_parts = read_passport_image(image)
        
        if not name_parts:
            return SanctionsCheckResponse(
                success=True,
                message="Could not read passport MRZ data",
                match_found=False
            )
        
        given_names, surname = name_parts
        full_name = f"{given_names} {surname}"
        
        # Check sanctions
        match = check_sanctions(full_name, SANCTIONED_PERSONS)
        
        response = SanctionsCheckResponse(
            success=True,
            message=f"Successfully processed passport for: {full_name}",
            match_found=bool(match)
        )
        
        if match:
            response.match_details = {
                "name": match.name,
                "aliases": match.aliases.get('good_quality', []),
                "nationality": match.nationality,
                "dob": match.dob
            }
        
        return response
        
    except Exception as e:
        return SanctionsCheckResponse(
            success=False,
            message=f"Error processing passport: {str(e)}",
            match_found=False
        )

@app.post("/check-passport-file/", response_model=SanctionsCheckResponse)
async def check_passport_file(file: UploadFile = File(...)):
    """
    Check a passport image file against sanctions lists
    """
    try:
        # Read the file
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Process passport
        name_parts = read_passport_image(image)
        
        if not name_parts:
            return SanctionsCheckResponse(
                success=True,
                message="Could not read passport MRZ data",
                match_found=False
            )
        
        given_names, surname = name_parts
        full_name = f"{given_names} {surname}"
        
        # Check sanctions
        match = check_sanctions(full_name, SANCTIONED_PERSONS)
        
        response = SanctionsCheckResponse(
            success=True,
            message=f"Successfully processed passport for: {full_name}",
            match_found=bool(match)
        )
        
        links = find_suspicious_links(full_name)
        if match:
            if links:
                response.match_details = {
                    "name": match.name,
                    "aliases": match.aliases.get('good_quality', []),
                    "source": match.source,
                    "links": links
                }
            else:
                response.match_details = {
                "name": match.name,
                "aliases": match.aliases.get('good_quality', []),
                "source": match.source,
                "links": None
                }
        
        return response
        
    except Exception as e:
        return SanctionsCheckResponse(
            success=False,
            message=f"Error processing passport: {str(e)}",
            match_found=False
        )
    
class NameCheckRequest(BaseModel):
    full_name: str

@app.post("/check-name/", response_model=SanctionsCheckResponse)
async def check_name(request: NameCheckRequest):
    """
    Check a person's full name against sanctions lists
    """
    try:
        # Check sanctions
        match = check_sanctions(request.full_name, SANCTIONED_PERSONS)
        
        response = SanctionsCheckResponse(
            success=True,
            message=f"Successfully checked name: {request.full_name}",
            match_found=bool(match)
        )
        
        links = find_suspicious_links(request.full_name)
        if match:
            if links:
                response.match_details = {
                    "name": match.name,
                    "aliases": match.aliases.get('good_quality', []),
                    "source": match.source,
                    "links": links
                }
            else:
                response.match_details = {
                "name": match.name,
                "aliases": match.aliases.get('good_quality', []),
                "source": match.source,
                "links": None
                }
        
        return response
        
    except Exception as e:
        return SanctionsCheckResponse(
            success=False,
            message=f"Error checking name: {str(e)}",
            match_found=False
        )

@app.post("/reprocess-sanctions/")
async def trigger_reprocess(background_tasks: BackgroundTasks):
    """
    Manually trigger reprocessing of sanctions data
    """
    background_tasks.add_task(reprocess_sanctions_data)
    return {"message": "Reprocessing started in background"}


@app.get("/sanctions-status/")
async def get_sanctions_status():
    """
    Get current status of sanctions data
    """
    try:
        last_modified = datetime.fromtimestamp(os.path.getmtime(PICKLE_FILE))
        return {
            "status": "active",
            "total_entries": len(SANCTIONED_PERSONS),
            "last_updated": last_modified.isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    
if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Sanctions Check API')
    parser.add_argument('--reprocess', action='store_true',
                      help='Force reprocessing of sanctions data on startup')
    args = parser.parse_args()

    # Initialize data based on command line argument
    initialize_data(args.reprocess)

    # Start the API server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
else:
    # When imported as a module (e.g., by uvicorn), just load the data
    initialize_data(False)