from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import train_parameter

ROOT = Path(__file__).resolve().parents[1]
train_parameter("pH", ROOT / "training_data/ph/labels.csv", ROOT / "training_data/ph/images", ROOT / "models/ph_model.pkl")
