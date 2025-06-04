from passporteye import read_mrz
from fastmrz import FastMRZ
import json
import os
import warnings
import re
warnings.filterwarnings("ignore")
import pytesseract
fast_mrz = FastMRZ(tesseract_path='/usr/bin/tesseract')  # Update this path if necessary

# Path to passport image (ensure it's clear and properly aligned)

files = os.listdir(r'D:\Work\sanctions\downloads')
def read_passport(image_path):
    """
    Reads the MRZ from the given image path.
    """
    try:
        # Read the MRZ from the image
        mrz = fast_mrz.get_details(image_path)
        if mrz['status'] == 'SUCCESS':
            name = f"{mrz['given_name']} {mrz['surname']}"
            return name
        else:
            return ""
    except Exception as e:
        print(f"Error reading MRZ: {e}")
        return None
    
# read_passport(r'D:\Work\sanctions\downloads\Specimen_Personal_Information_Page_South_Korean_Passport.jpg')
for file in files:
    read_passport(os.path.join(r'D:\Work\sanctions\downloads', file))