# FeedSense AI

Smart Rapid Feed & Silage Quality Testing System for Dairy Farmers.

## Current status

The Flask backend, full-strip chamber pipeline, separate model training scripts, Scan/Results UI, history, PDF endpoint, and strict bilingual voice selection are implemented. Analysis intentionally refuses to fabricate results until calibrated strip coordinates, authoritative reference rows, and labeled chamber images/models are supplied.

## Windows setup

From the project folder in the VS Code terminal:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Run the application:

```powershell
python app.py
```

Open `http://127.0.0.1:5000/`.

## Add real data

Place authoritative reference tables in `dataset/ph/ph_reference.csv`, `dataset/ammonia/ammonia_reference.csv`, and `dataset/protein/protein_reference.csv`. The required numeric columns are `ph_value`, `ppm`, and `protein_value`, respectively; all three also require `condition`, `problem`, and `remedy`.

Place labeled chamber images and numerical labels in each `training_data/<parameter>/images` directory and its `labels.csv`, then run:

```powershell
python training/train_ph.py
python training/train_ammonia.py
python training/train_protein.py
```

Calibrate the normalized chamber boxes and strip frame in `config/strip_config.json` against a real complete strip image before analysis.

## Honest limitations

The repository does not contain scientific reference values, a strip photograph, or labeled image training data. Therefore no prediction, threshold, accuracy, confidence, or scientific claim is fabricated. The application reports the missing model/reference/calibration requirement instead.
