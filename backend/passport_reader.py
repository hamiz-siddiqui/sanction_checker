from passporteye import read_mrz
import os
import warnings
import re
warnings.filterwarnings("ignore")
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Update this path if necessary

# Path to passport image (ensure it's clear and properly aligned)

files = os.listdir('downloads')
def read_passport(image_path):
    """
    Reads the MRZ from the given image path.
    """
    try:
        # Read the MRZ from the image
        mrz = read_mrz(image_path)

        if mrz is not None:
            mrz_data = mrz.to_dict()
            names = mrz_data['names']
            names = re.split(r'\s+K', names)[0]
            names = names.strip()
            mrz_data['names'] = names
            full_name = f"{mrz_data['names']} {mrz_data['surname'].strip()}"
            print("Extracted Name:", full_name)
        else:
            print("MRZ not detected.")
    except Exception as e:
        print(f"Error reading MRZ: {e}")
        return None
    
for file in files:
    read_passport(os.path.join('downloads', file))