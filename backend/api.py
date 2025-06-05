from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from os import path
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
from fastmrz import FastMRZ
import base64
from fastapi.middleware.cors import CORSMiddleware
import img2pdf
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors

from contextlib import asynccontextmanager
from scraper import find_suspicious_links
# Initialize FastMRZ for reading MRZ from passport images
# fast_mrz = FastMRZ(tesseract_path='/usr/bin/tesseract')  # Update this path if necessary
fast_mrz = FastMRZ()  # Use default tesseract path if installed in PATH

# Global variable to store sanctioned persons
SANCTIONED_PERSONS = []

# Path to pickle file
PICKLE_FILE = 'sanctioned_people_simplified.pkl'

# Set up reports directory
REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

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
    report_url: Optional[str] = None

@app.get("/download-report/{filename}")
async def download_report(filename: str):
    """Download a generated PDF report"""
    file_path = os.path.join(REPORTS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
            media_type="application/pdf"
        )
    return JSONResponse(
        status_code=404,
        content={"error": "Report not found"}
    )

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
        mrz = fast_mrz.get_details(image_path)

        if mrz["status"] == "SUCCESS":
            names = mrz['given_name']
            surname = mrz['surname']

            # Create PDF for passport image
            pdf_path = f"{names} {surname} - Passport.pdf" 
            image = Image(image_path)
            pdf_bytes = img2pdf.convert(image.filename)
            file = open(pdf_path, "wb")
            file.write(pdf_bytes)
            image.close()
            file.close()

            # Clean up temporary image file
            os.remove(image_path)

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
    Creates the report related to the person, regardless of sanction status
    """

    # Variable just to indicate if a match was found, for reporting purposes
    found = False
    match = None

    if not name or not sanctioned_persons:
        return None
        
    name = name.lower().strip()
    for person in sanctioned_persons:
        # Check main name
        if person.name and name in person.name.lower():
            found = True
            match = person
            break
            
        # Check aliases
        for alias_type in ['good_quality', 'low_quality']:
            for alias in person.aliases.get(alias_type, []):
                if alias and name in alias.lower():
                    match = person
                    found = True
                    break
        if found:
            break
    return match

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

def create_pdf(response: SanctionsCheckResponse, full_name: str):
    """
    Create a PDF report for the sanctions check response
    """
    # Create filename in format: {full name - Screening Result (MonthYear)}
    current_date = datetime.now()
    filename = f"{full_name} - Screening Result ({current_date.strftime('%B%Y')}).pdf"
    pdf_path = os.path.join(REPORTS_DIR, filename)
    
    pdf = canvas.Canvas(pdf_path)
    pdf.setTitle("Compliance Check Result")

    # Register and set font
    pdf.setFont('Helvetica', 14)
    
    # Title
    pdf.setFillColor(colors.black)
    pdf.drawString(100, 750, "Compliance Check Result")
    
    # Add current date
    pdf.setFont('Helvetica', 10)
    pdf.drawString(100, 720, f"Date: {current_date.strftime('%d %B %Y')}")
    
    # Add checked name
    pdf.drawString(100, 690, f"Name Checked: {full_name}")
    
    # Response details
    y = 660
    if not response.match_found:
        pdf.drawString(100, y, "Result: No match found in sanctions lists")
    else:
        pdf.drawString(100, y, "Result: MATCH FOUND IN SANCTIONS LIST")
        y -= 30

        if response.match_details:
            pdf.drawString(100, y, "Match Details:")
            y -= 20
            
            # Add name
            if "name" in response.match_details:
                pdf.drawString(120, y, f"Listed Name: {response.match_details['name']}")
                y -= 20
            
            # Add aliases if any
            if "aliases" in response.match_details and response.match_details["aliases"]:
                pdf.drawString(120, y, "Known Aliases:")
                y -= 20
                for alias in response.match_details["aliases"]:
                    pdf.drawString(140, y, f"- {alias}")
                    y -= 20
            
            # Add source
            if "source" in response.match_details:
                pdf.drawString(120, y, f"List Source: {response.match_details['source']}")
                y -= 20

    # Add footer
    pdf.setFont('Helvetica', 8)
    pdf.drawString(100, 50, "This report is system-generated and is strictly confidential.")
      # Save PDF
    pdf.save()
    return filename  # Return just the filename, not the full path

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

        # Create report for screening check results
        create_pdf(response, full_name)

        return response
        
    except Exception as e:
        response = SanctionsCheckResponse(
            success=False,
            message=f"Error processing passport: {str(e)}",
            match_found=False
        )

        create_pdf(response, "Unknown")
        return response

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
        
        # Create report for screening check results
        create_pdf(response, full_name)
        
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
                }        # Create report for screening check results
        filename = create_pdf(response, request.full_name)
        response.report_url = f"/download-report/{filename}"
        
        return response
        
    except Exception as e:
        # Handle any errors that occur during the check
        response = SanctionsCheckResponse(
            success=False,
            message=f"Error checking name: {str(e)}",
            match_found=False,
            match_details={"name": request.full_name}
        )
        create_pdf(response, request.full_name)

        return response

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

# Mount the static files directory
if not os.path.exists("static"):
    os.makedirs("static")
static_dir = path.join(path.dirname(path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")