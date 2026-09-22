from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import train_parameter

ROOT = Path(__file__).resolve().parents[1]
train_parameter("Ammonia", ROOT / "training_data/ammonia/labels.csv", ROOT / "training_data/ammonia/images", ROOT / "models/ammonia_model.pkl")
