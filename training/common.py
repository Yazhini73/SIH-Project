"""Shared training helpers; training datasets remain parameter-specific."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
import joblib

from image_processing.features import feature_vector


def train_parameter(parameter: str, label_file: str, image_dir: str, model_file: str) -> None:
    labels_path = Path(label_file)
    images_path = Path(image_dir)
    if not labels_path.exists() or not images_path.exists():
        print("No labeled image training data found.")
        return
    labels = pd.read_csv(labels_path)
    required = {"image_name", "numerical_value"}
    if not required.issubset(labels.columns) or labels.empty:
        print("No labeled image training data found.")
        return
    features, targets = [], []
    for row in labels.to_dict("records"):
        image_path = images_path / str(row["image_name"])
        if not image_path.exists():
            continue
        try:
            features.append(feature_vector(image_path)[0])
            targets.append(float(row["numerical_value"]))
        except (OSError, ValueError):
            continue
    if len(features) < 2:
        print("No labeled image training data found.")
        return
    x_train, x_test, y_train, y_test = train_test_split(features, targets, test_size=0.2, random_state=42)
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    print(f"{parameter} MAE: {mean_absolute_error(y_test, predictions):.4f}")
    if len(y_test) > 1:
        print(f"{parameter} R2: {r2_score(y_test, predictions):.4f}")
    Path(model_file).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_file)
    print(f"Saved model: {model_file}")
