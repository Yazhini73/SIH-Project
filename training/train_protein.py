from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import train_parameter

ROOT = Path(__file__).resolve().parents[1]
train_parameter("Protein", ROOT / "training_data/protein/labels.csv", ROOT / "training_data/protein/images", ROOT / "models/protein_model.pkl")
