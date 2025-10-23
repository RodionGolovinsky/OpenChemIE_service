import torch
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from openchemie import OpenChemIE
from molscribe import MolScribe
from huggingface_hub import hf_hub_download
import tempfile
import logging
from utils import _clean_reaction_entities, _clean_molecule_data
from typing import Union
import numpy as np
import cv2
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)

molscribe_model = None
openchemie_model = None
app = FastAPI()


class ParsingResponse(BaseModel):
    response: Union[list, dict, str]
   
    
@app.get("/")
def index():
    return {"response": "Chemical entities parsing using computer vision tools"}


@app.on_event("startup")
def load_models():
    global molscribe_model
    global openchemie_model
    # device = 'cuda' if torch.cuda.is_available() else 'cpu'
    device = 'cpu'
    logging.info(f"Using {device} device")
    molscribe_ckpt_path = hf_hub_download(repo_id='yujieq/MolScribe', filename='swin_base_char_aux_1m.pth')
    molscribe_model = MolScribe(molscribe_ckpt_path, device=device)
    openchemie_model = OpenChemIE(device=device)


@app.post("/extract_reactions_from_pdf/")
async def extract_reactions_from_pdf(pdf_file: UploadFile = File(...)):
    """Extracts reactions from a PDF file."""
    if not pdf_file.filename.lower().endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "File must be a PDF"})
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await pdf_file.read())
        tmp_path = tmp.name
        
    figure_results = openchemie_model.extract_reactions_from_figures_in_pdf(tmp_path)
    for figure in figure_results:
        for reaction in figure.get('reactions', []):
            _clean_reaction_entities(reaction.get('reactants', []))
            _clean_reaction_entities(reaction.get('conditions', []))
            _clean_reaction_entities(reaction.get('products', []))
        figure.pop('figure', None)
    figure_results = [figure for figure in figure_results if len(figure.get('reactions', [])) > 0]
    response = ParsingResponse(response=figure_results)
    return response


@app.post("/extract_reactions_from_figure/")
async def extract_reactions_from_figure(image: UploadFile = File(...)):
    """Extracts reactions from a PDF file."""
    
    contents = await image.read()
    image_array = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
    if image_array is None:
        return JSONResponse(
            status_code=400, 
            content={"error": "Failed to decode image"}
        )
    figure_results = openchemie_model.extract_reactions_from_figures([image_array])
    for figure in figure_results:
        for reaction in figure.get('reactions', []):
            _clean_reaction_entities(reaction.get('reactants', []))
            _clean_reaction_entities(reaction.get('conditions', []))
            _clean_reaction_entities(reaction.get('products', []))
        figure.pop('figure', None)
    figure_results = [figure for figure in figure_results if len(figure.get('reactions', [])) > 0]
    response = ParsingResponse(response=figure_results)
    return response


@app.post("/extract_molecules_from_pdf/")
async def extract_molecules_from_pdf(pdf_file: UploadFile = File(...)):
    """Extracts molecules with identifiers from a PDF file."""
    if not pdf_file.filename.lower().endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "File must be a PDF"})
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await pdf_file.read())
            tmp_path = tmp.name
            
    figure_results = openchemie_model.extract_molecule_corefs_from_figures_in_pdf(tmp_path)
    for figure in figure_results:
        figure['bboxes'] = [
            _clean_molecule_data(bbox, False)
            for bbox in figure.get('bboxes', [])
        ]
    response = ParsingResponse(response=figure_results)
    return response


@app.post("/extract_molecules_from_figure/")
async def extract_molecules_from_figure(image: UploadFile = File(...)):
    """Extracts molecules with identifiers from a PDF file."""

    contents = await image.read()
    image_array = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
    if image_array is None:
        return JSONResponse(
            status_code=400, 
            content={"error": "Failed to decode image"}
        )   
    figure_results = openchemie_model.extract_molecule_corefs_from_figures([image_array])
    for figure in figure_results:
        figure['bboxes'] = [
            _clean_molecule_data(bbox, False)
            for bbox in figure.get('bboxes', [])
        ]
    response = ParsingResponse(response=figure_results)
    return response
    
    
@app.post("/convert_image_to_smiles/")
async def convert_image_to_smiles(image_file: UploadFile = File(...)):
    """Convert image to SMILES."""
    if not image_file.content_type.startswith('image/'):
        return JSONResponse(
            status_code=400, 
            content={"error": "File must be an image"}
        )
    
    contents = await image_file.read()
    image_array = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
    
    if image_array is None:
        return JSONResponse(
            status_code=400, 
            content={"error": "Failed to decode image"}
        )
    
    output = molscribe_model.predict_image(image_array)
    return output.get("smiles", "")
    
    
    
    