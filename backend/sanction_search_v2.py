import pdfplumber
from typing import List, Dict, Optional
import re
import warnings
import pandas  # Used in uae_list
from dataclasses import dataclass
import pickle
from tqdm import tqdm
import os
import PyPDF2 # For PDF splitting

# --- Global Settings ---
warnings.filterwarnings('ignore')

# --- Data Class ---
@dataclass
class SanctionedPerson:
    id: Optional[str] # Made Optional as sometimes it's None
    name: str
    original_name: Optional[str]
    title: Optional[str]
    designation: List[str]
    dob: Optional[str]
    aliases: Dict[str, List[str]]
    nationality: Optional[str]
    passport_no: Optional[str]
    national_id: Optional[str]
    source: str  # Source of the sanction (UAE, SDN, or UN)

# --- Helper Functions ---
def clean_text(text: str) -> str:
    """Clean text by removing CID characters and normalizing spaces."""
    if not isinstance(text, str):
        return str(text)
    cleaned = re.sub(r'\(cid:\d+\)', '', text)
    cleaned = ' '.join(cleaned.split())
    return cleaned.strip()

# --- PDF Parsing Functions ---

def _process_page_for_merged_columns(page: pdfplumber.page.Page, 
                                     page_num_in_chunk: int, 
                                     is_first_page_of_original_document: bool) -> str:
    """
    Processes a single page to extract text from three predefined columns.
    Handles special "List." removal for the very first page of the original document.
    """
    try:
        width = page.width
        height = page.height
        col_width = width / 3
        margin = 40  # Margin adjustment from original code

        text_parts = []
        # Column bounding boxes from original code
        col_bounds_list = [
            (0, 0, col_width, height),
            (col_width, 0, 2 * col_width, height),
            (width - (col_width + margin), 0, width, height)
        ]

        for col_bounds in col_bounds_list:
            cropped_page = page.within_bbox(col_bounds)
            col_text = cropped_page.extract_text(x_tolerance=2, y_tolerance=2)
            if col_text:
                lines = col_text.split('\n')
                text_parts.append(' '.join(lines))
        
        # Handle "List." removal on the very first page of the original document
        if is_first_page_of_original_document and page_num_in_chunk == 0 and text_parts:
            try:
                first_col_text = text_parts[0]
                # More robust check for "List." at the beginning of the text
                if first_col_text.lstrip().startswith('List.'):
                    list_idx = first_col_text.find('List.')
                    text_parts[0] = first_col_text[list_idx + len('List.'):].strip()
            except ValueError: # Should not happen with find()
                pass 
            except IndexError: # If text_parts is empty after all, though checked
                pass
        
        return ' '.join(text_parts)
    except Exception as e:
        # Provide page number within its chunk for better debugging
        pdf_name = os.path.basename(page.pdf.stream.name) if hasattr(page.pdf.stream, 'name') else "Unknown PDF"
        print(f"Error processing page {page_num_in_chunk + 1} in chunk '{pdf_name}': {str(e)}")
        return ""

def extract_text_from_pdf_chunk_merged_columns(pdf_chunk_path: str, 
                                               is_first_chunk_of_original_document: bool) -> str:
    """
    Extracts and merges column text from all pages of a given (small) PDF chunk.
    `is_first_chunk_of_original_document` helps identify the absolute first page for special processing.
    """
    all_text_from_this_chunk = []
    try:
        with pdfplumber.open(pdf_chunk_path) as pdf:
            for i, page_obj in enumerate(pdf.pages):
                # The "very first page" condition is true if this is the first chunk AND it's the first page of this chunk.
                is_very_first_page_of_original = (is_first_chunk_of_original_document and i == 0)
                
                page_text = _process_page_for_merged_columns(page_obj, i, is_very_first_page_of_original)
                if page_text:
                    all_text_from_this_chunk.append(page_text)
        return " ".join(all_text_from_this_chunk).strip()
    except Exception as e:
        print(f"Error in extract_text_from_pdf_chunk_merged_columns for '{pdf_chunk_path}': {e}")
        return ""

def _split_pdf_into_temporary_chunks(input_pdf_path: str, output_folder: str, pages_per_chunk: int = 20) -> List[str]:
    """
    Splits the input PDF into temporary smaller PDF files using PyPDF2.
    Returns a list of paths to the created chunk files.
    """
    temp_file_paths = []
    try:
        if not os.path.exists(input_pdf_path):
            print(f"Error: Input PDF for splitting not found at '{input_pdf_path}'")
            return []
        if pages_per_chunk <= 0:
            print("Error: 'pages_per_chunk' must be a positive integer.")
            return []

        os.makedirs(output_folder, exist_ok=True)

        with open(input_pdf_path, 'rb') as infile:
            reader = PyPDF2.PdfReader(infile)
            total_pages = len(reader.pages)

            if total_pages == 0:
                print(f"The PDF '{input_pdf_path}' has no pages.")
                return []

            print(f"Splitting '{os.path.basename(input_pdf_path)}' ({total_pages} pages) into chunks of ~{pages_per_chunk} pages in '{output_folder}'.")
            original_filename = os.path.splitext(os.path.basename(input_pdf_path))[0]

            for i in range(0, total_pages, pages_per_chunk):
                writer = PyPDF2.PdfWriter()
                start_page_idx = i
                end_page_idx = min(i + pages_per_chunk, total_pages)
                
                for page_num_in_original in range(start_page_idx, end_page_idx):
                    writer.add_page(reader.pages[page_num_in_original])

                if len(writer.pages) > 0:
                    chunk_number = (i // pages_per_chunk) + 1
                    temp_chunk_filename = f"{original_filename}_temp_chunk_{chunk_number:03d}.pdf"
                    temp_chunk_filepath = os.path.join(output_folder, temp_chunk_filename)
                    with open(temp_chunk_filepath, 'wb') as outfile:
                        writer.write(outfile)
                    temp_file_paths.append(temp_chunk_filepath)
        
        print(f"Splitting complete. {len(temp_file_paths)} chunks created.")
        return temp_file_paths

    except PyPDF2.errors.PdfReadError as e:
        print(f"PyPDF2 Error reading PDF '{input_pdf_path}' for splitting: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during PDF splitting: {e}")
    
    # Clean up any created chunks if splitting failed midway or returned early
    for path in temp_file_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError: pass
    return [] # Return empty if error before full completion

def sdnlist(main_pdf_path="sdnlist.pdf", pages_per_chunk=20, temp_chunk_folder="temp_sdn_chunks") -> List[SanctionedPerson]:
    """
    Parse SDN list by:
    1. Splitting the main PDF into smaller temporary PDF chunks using PyPDF2.
    2. Extracting text from each chunk using `extract_text_from_pdf_chunk_merged_columns`.
    3. Concatenating all extracted text.
    4. Parsing the concatenated text into SanctionedPerson objects.
    """
    if not os.path.exists(main_pdf_path):
        print(f"Error: SDN PDF not found at '{main_pdf_path}'. Cannot process.")
        return []

    print(f"Starting to process '{main_pdf_path}' with chunking...")
    temp_chunk_files = _split_pdf_into_temporary_chunks(main_pdf_path, temp_chunk_folder, pages_per_chunk)
    
    if not temp_chunk_files:
        print("No temporary chunk files were created. Aborting sdnlist processing.")
        if os.path.exists(temp_chunk_folder) and not os.listdir(temp_chunk_folder):
            try: os.rmdir(temp_chunk_folder)
            except OSError: pass
        return []
    
    all_text_from_chunks = []
    print(f"Extracting text from {len(temp_chunk_files)} PDF chunks...")
    for i, chunk_file_path in enumerate(tqdm(temp_chunk_files, desc="Processing PDF chunks")):
        is_first_chunk = (i == 0)
        text_from_chunk = extract_text_from_pdf_chunk_merged_columns(chunk_file_path, is_first_chunk)
        if text_from_chunk:
            all_text_from_chunks.append(text_from_chunk)
        else:
            print(f"Warning: No text extracted from chunk '{chunk_file_path}'.")
        
        try:
            os.remove(chunk_file_path)
        except OSError as e:
            print(f"Warning: Error removing temporary chunk file {chunk_file_path}: {e}")
            
    try:
        if os.path.exists(temp_chunk_folder) and not os.listdir(temp_chunk_folder):
            os.rmdir(temp_chunk_folder)
            print(f"Successfully removed temporary chunk folder: '{temp_chunk_folder}'")
        elif os.path.exists(temp_chunk_folder) and os.listdir(temp_chunk_folder): # Check if it's not empty
            print(f"Warning: Temporary chunk folder '{temp_chunk_folder}' is not empty. Manual cleanup might be needed.")
    except Exception as e:
        print(f"Warning: Error cleaning up temporary folder '{temp_chunk_folder}': {e}")

    if not all_text_from_chunks:
        print("No text was extracted from any of the PDF chunks. Returning empty list.")
        return []

    print("Concatenating text from all chunks...")
    full_text = " ".join(all_text_from_chunks) # Ensure space separation
    
    print("Splitting concatenated text into entries...")
    entries = re.split(r'\]\.(?=\s[A-Z0-9])', full_text)

    sanctioned_persons = []
    print(f"Parsing {len(entries)} potential SDN entries...")
    for entry_text in tqdm(entries, desc="Parsing SDN entries"):
        entry_text = entry_text.strip()
        if not entry_text:
            continue
        
        if not entry_text.endswith('].'):
            if not re.search(r'\[[A-Z0-9\-]+\]$', entry_text):
                 entry_text += '].'

        if not re.search(r'\[[A-Z0-9\-]+\]', entry_text):
            continue
            
        person = parse_sdn_entry(entry_text)
        if person:
            sanctioned_persons.append(person)
            
    print(f"Successfully parsed {len(sanctioned_persons)} SDN entries.")
    return sanctioned_persons

def parse_sdn_entry(text: str) -> Optional[SanctionedPerson]:
    """Parse a single SDN entry text into a SanctionedPerson object."""
    try:
        name_match = re.match(r'^(.*?)(?=\s*\(a\.k\.a\.|,\s)', text)
        name = name_match.group(1).strip() if name_match else "Unknown Name"
        
        aliases_found = []
        for m in re.finditer(r'\(a\.k\.a\.\s*([^);]+)(?:;|\))', text):
            alias = m.group(1).strip()
            if 'Cyrillic:' in alias:
                cyrillic_match = re.search(r'Cyrillic:\s*([^)]+)', alias)
                if cyrillic_match:
                    aliases_found.append(cyrillic_match.group(1).strip())
                non_cyrillic = re.sub(r'\(Cyrillic:[^)]+\)', '', alias).strip()
                if non_cyrillic:
                    aliases_found.append(non_cyrillic)
            else:
                aliases_found.append(alias)
        aliases_found += re.findall(r'"([^"]+)"', text)
        
        return SanctionedPerson(
            id=None, name=name, original_name=None, title=None, designation=[],
            dob=None, aliases={'good_quality': [a for a in aliases_found if a], 'low_quality': []},
            nationality=None, passport_no=None, national_id=None, source="SDN"
        )
    except Exception as e:
        # print(f"Error parsing SDN entry: {e} for text: {text[:100]}...")
        return None

def uae_list(pdf_path='Copy of SL_1 (24052021) V.2 (1).pdf') -> List[SanctionedPerson]:
    """Parses the UAE sanctions list from a PDF (primarily table-based)."""
    uae_text_content = "" # Keep for potential future use, though not directly used for SanctionedPerson now
    uae_tables_data = []

    if not os.path.exists(pdf_path):
        print(f"Warning: UAE PDF not found at '{pdf_path}'. Skipping uae_list.")
        return []
        
    with pdfplumber.open(pdf_path) as pdf:
        for page in tqdm(pdf.pages, desc="Processing UAE PDF"):
            tables = page.extract_tables()
            if tables:
                uae_tables_data.extend(tables)
            text = page.extract_text() # Extract text as well, might be useful
            if text:
                uae_text_content += text + "\n"

    all_rows = []
    for table in uae_tables_data:
        for row in table:
            cleaned_row = [clean_text(cell) if cell else '' for cell in row]
            if any(cell.strip() for cell in cleaned_row): # Ensure row is not completely empty
                all_rows.append(cleaned_row)

    sanctioned_persons = []
    if all_rows:
        df = pandas.DataFrame(all_rows)
        # Assuming name is in column 12 based on original code. Add error handling.
        if 12 < df.shape[1]:
            for name_val in df[12]:
                if pandas.notna(name_val) and str(name_val).strip(): # Ensure name is not NaN or empty
                    sanctioned_persons.append(SanctionedPerson(
                        id=None, name=str(name_val).strip(), original_name=None, title=None, designation=[],
                        dob=None, aliases={'good_quality': [], 'low_quality': []},
                        nationality=None, passport_no=None, national_id=None, source="UAE"
                    ))
        else:
            print(f"Warning: Column 12 (for names) not found or out of bounds in UAE PDF table data from '{pdf_path}'.")
    else:
        print(f"Warning: No table data extracted from UAE PDF '{pdf_path}'.")
    return sanctioned_persons


def parse_sanction_entry(text: str) -> Optional[SanctionedPerson]:
    """Parse a single UN-style sanction entry text into a SanctionedPerson object."""
    try:
        id_match = re.search(r'TAi\.(\d+)', text)
        if not id_match: return None # Essential identifier
        
        name_match = re.search(r'Name: 1: (.*?) 2: (.*?) 3: (.*?) 4: (.*?)\n', text)
        if not name_match: return None # Name is essential
        
        name_parts = [part.strip() for part in name_match.groups() if part and part.lower() != 'na']
        full_name = ' '.join(name_parts)
        if not full_name: return None # Ensure name is not empty after processing

        original_name_match = re.search(r'Name \(original script\): (.*?)\n', text)
        title_match = re.search(r'Title: (.*?)\n', text)
        designation_match = re.search(r'Designation: (.*?)\n', text)
        dob_match = re.search(r'DOB: (.*?)\n', text)
        nationality_match = re.search(r'Nationality: (.*?)\n', text)
        passport_match = re.search(r'Passport no: (.*?)\n', text)
        national_id_match = re.search(r'National identification no: (.*?)\n', text)
        
        good_aliases_text = re.search(r'Good quality a\.k\.a\.:(.*?)\n', text, re.IGNORECASE)
        low_aliases_text = re.search(r'Low quality a\.k\.a\.:(.*?)\n', text, re.IGNORECASE)

        good_aliases = []
        if good_aliases_text and good_aliases_text.group(1).strip():
            good_aliases = [a.strip() for a in re.split(r'\b[a-z]\)\s*', good_aliases_text.group(1).strip()) if a.strip()]
        
        low_aliases = []
        if low_aliases_text and low_aliases_text.group(1).strip():
            low_aliases = [a.strip() for a in re.split(r'\b[a-z]\)\s*', low_aliases_text.group(1).strip()) if a.strip()]
        
        designations = []
        if designation_match and designation_match.group(1).strip():
             designations = [d.strip() for d in re.split(r'\b[a-z]\)\s*', designation_match.group(1).strip()) if d.strip()]


        return SanctionedPerson(
            id=id_match.group(0), name=full_name,
            original_name=original_name_match.group(1).strip() if original_name_match and original_name_match.group(1).strip() else None,
            title=title_match.group(1).strip() if title_match and title_match.group(1).strip() else None,
            designation=designations,
            dob=dob_match.group(1).strip() if dob_match and dob_match.group(1).strip() else None,
            aliases={'good_quality': good_aliases, 'low_quality': low_aliases},
            nationality=nationality_match.group(1).strip() if nationality_match and nationality_match.group(1).strip() else None,
            passport_no=passport_match.group(1).strip() if passport_match and passport_match.group(1).strip() else None,
            national_id=national_id_match.group(1).strip() if national_id_match and national_id_match.group(1).strip() else None,
            source="UN"
        )
    except Exception as e:
        # print(f"Error parsing UN-style entry: {e} for text: {text[:100]}...")
        return None

def unsanctionslist(pdf_path='unsanctions.pdf') -> List[SanctionedPerson]:
    """Parses the UN sanctions list from a PDF (text-based entries)."""
    un_text_content = ""
    sanctioned_persons = []

    if not os.path.exists(pdf_path):
        print(f"Warning: UN PDF not found at '{pdf_path}'. Skipping unsanctionslist.")
        return []

    with pdfplumber.open(pdf_path) as pdf:
        for page in tqdm(pdf.pages, desc="Processing UN PDF"):
            text = page.extract_text()
            if text:
                un_text_content += text + "\n" # Add newline to separate page contents
    
    # Split text into individual entries based on the "TAi.ddd" pattern
    # The lookahead (?=...) ensures the delimiter is part of the next split item.
    entries = re.split(r'(?=TAi\.\d+)', un_text_content)
    
    for entry_text in tqdm(entries, desc="Parsing UN entries"):
        entry_text = entry_text.strip()
        if entry_text.startswith("TAi."): # Ensure it's a valid entry start
            person = parse_sanction_entry(entry_text)
            if person:
                sanctioned_persons.append(person)
    
    return sanctioned_persons

# --- Search and Persistence ---
def search_by_name(sanctioned_persons: List[SanctionedPerson], query: str) -> Optional[SanctionedPerson]:
    """Search for sanctioned persons by name. Returns the first match or None."""
    query = query.lower().strip()
    if not query: return None

    for person in sanctioned_persons:
        if person.name and query in person.name.lower():
            return person
        # Original alias search was commented out, keeping it that way.
        # If needed, uncomment and adapt:
        # for alias_type in ['good_quality', 'low_quality']:
        #     for alias in person.aliases.get(alias_type, []):
        #         if alias and query in alias.lower():
        #             return person
    return None

def save_sanctioned_persons(persons: List[SanctionedPerson], filename: str):
    """Saves a list of SanctionedPerson objects to a pickle file."""
    with open(filename, 'wb') as f:
        pickle.dump(persons, f)
    print(f"Saved {len(persons)} entries to '{filename}'.")

def load_sanctioned_persons(filename: str) -> List[SanctionedPerson]:
    """Loads a list of SanctionedPerson objects from a pickle file."""
    if not os.path.exists(filename):
        print(f"Pickle file '{filename}' not found. Returning empty list.")
        return []
    try:
        with open(filename, 'rb') as f:
            persons = pickle.load(f)
        print(f"Loaded {len(persons)} entries from '{filename}'.")
        return persons
    except Exception as e:
        print(f"Error loading pickle file '{filename}': {e}. Returning empty list.")
        return []

# --- Main Execution ---
if __name__ == "__main__":
    # Configuration for PDF paths
    SDN_PDF_PATH = "sdnlist.pdf"
    UN_PDF_PATH = "unsanctions.pdf"
    UAE_PDF_PATH = "Copy of SL_1 (24052021) V.2 (1).pdf" # Original filename
    
    PICKLE_FILE = 'sanctioned_people_simplified.pkl' # Changed name to reflect simplification
    REPROCESS_DATA = True  # Set to True to re-parse PDFs, False to load from pickle

    all_sanctioned_persons = []

    if REPROCESS_DATA or not os.path.exists(PICKLE_FILE):
        print("Reprocessing data from PDF files...")
        
        print(f"\n--- Processing SDN List ('{SDN_PDF_PATH}') ---")
        sdn_persons = sdnlist(main_pdf_path=SDN_PDF_PATH, pages_per_chunk=10, temp_chunk_folder="temp_sdn_chunks_simplified")
        all_sanctioned_persons.extend(sdn_persons)
        print(f"Found {len(sdn_persons)} entries from SDN list.")

        print(f"\n--- Processing UN Sanctions List ('{UN_PDF_PATH}') ---")
        un_persons = unsanctionslist(pdf_path=UN_PDF_PATH)
        all_sanctioned_persons.extend(un_persons)
        print(f"Found {len(un_persons)} entries from UN list.")
        
        print(f"\n--- Processing UAE List ('{UAE_PDF_PATH}') ---")
        uae_persons = uae_list(pdf_path=UAE_PDF_PATH)
        all_sanctioned_persons.extend(uae_persons)
        print(f"Found {len(uae_persons)} entries from UAE list.")

        print(f"\nTotal sanctioned entities from all lists: {len(all_sanctioned_persons)}")
        
        if all_sanctioned_persons:
            save_sanctioned_persons(all_sanctioned_persons, PICKLE_FILE)
    else:
        all_sanctioned_persons = load_sanctioned_persons(PICKLE_FILE)
    queries = ['ASHRAF MUHAMMAD YUSUF UTHMAN ABD ALSALAM', 'MUHAMMAD TAHER ANWARI', '3LOGIC GROUP', '3RD TECHNICAL SURVEILLANCE BUREAU', 'JOE BIDEN']
    if all_sanctioned_persons:
        for search_query in queries:        
            found_person = search_by_name(all_sanctioned_persons, search_query)
            
            if found_person:
                print(f"Search result for '{search_query}':")
                print(f"  Name: {found_person.name}")
                print(f"  ID: {found_person.id}")
                print(f"  Source: {found_person.source}")
                print(f"  Aliases: {found_person.aliases.get('good_quality', [])}")
            else:
                print(f"No results found for '{search_query}'.")
    else:
        print("No data loaded or processed for searching.")