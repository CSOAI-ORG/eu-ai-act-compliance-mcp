"""
MEOK Labs — Compliance Neural Learning Module
==============================================
A lightweight neural network that learns from compliance check patterns
to improve risk scoring, predict common violations, and suggest remediations.

Uses only Python stdlib — no numpy, torch, or sklearn required.
Persists learned weights to SQLite via the shared persistence layer.

Usage in any compliance server.py:
    import sys, os
    sys.path.insert(0, os.path.expanduser("~/clawd/meok-labs-engine/shared"))
    from compliance_neural import ComplianceNeuralNet

    nn = ComplianceNeuralNet("eu-ai-act")
    nn.learn_from_check(features, outcome)
    prediction = nn.predict_risk(features)
    insights = nn.get_insights()
"""

import math
import json
import os
import sqlite3
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Union


def _sigmoid(x: float) -> float:
    """Sigmoid activation, clamped to prevent overflow."""
    x = max(-500.0, min(500.0, x))
    return 1.0 / (1.0 + math.exp(-x))


def _relu(x: float) -> float:
    return max(0.0, x)


class ComplianceNeuralNet:
    """
    A 3-layer neural network (input → hidden → output) that learns from
    compliance check outcomes to improve future predictions.

    Feature vector (12 dimensions):
        0: system_complexity      (0.0-1.0) — number of components / max
        1: data_sensitivity        (0.0-1.0) — PII, biometric, health, financial
        2: autonomy_level         (0.0-1.0) — human oversight degree
        3: affected_population    (0.0-1.0) — scale of impact
        4: sector_risk            (0.0-1.0) — based on industry vertical
        5: existing_controls      (0.0-1.0) — current mitigation measures
        6: documentation_quality  (0.0-1.0) — completeness of technical docs
        7: prior_violations       (0.0-1.0) — history of non-compliance
        8: cross_border           (0.0-1.0) — multi-jurisdiction deployment
        9: model_transparency     (0.0-1.0) — explainability of AI model
        10: update_frequency      (0.0-1.0) — how often the system changes
        11: vulnerability_exposure (0.0-1.0) — attack surface assessment

    Output (4 dimensions):
        0: overall_risk_score     (0.0-1.0)
        1: violation_probability  (0.0-1.0)
        2: remediation_urgency    (0.0-1.0)
        3: audit_priority         (0.0-1.0)
    """

    INPUT_DIM = 12
    HIDDEN_DIM = 16
    OUTPUT_DIM = 4
    LEARNING_RATE = 0.01

    FEATURE_NAMES = [
        "system_complexity", "data_sensitivity", "autonomy_level",
        "affected_population", "sector_risk", "existing_controls",
        "documentation_quality", "prior_violations", "cross_border",
        "model_transparency", "update_frequency", "vulnerability_exposure",
    ]

    OUTPUT_NAMES = [
        "overall_risk_score", "violation_probability",
        "remediation_urgency", "audit_priority",
    ]

    def __init__(self, server_name: str):
        self.server_name = server_name
        self.db_path = os.path.expanduser(f"~/.meok/data/{server_name}_neural.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self._init_db()
        self._load_or_init_weights()
        self.check_count = self._get_check_count()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS weights (
                layer TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS check_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                features TEXT NOT NULL,
                outcome TEXT NOT NULL,
                prediction TEXT,
                loss REAL,
                timestamp REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL
            )
        """)
        conn.commit()
        conn.close()

    def _load_or_init_weights(self):
        """Load persisted weights or initialize with Xavier initialization."""
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT data FROM weights WHERE layer='all'").fetchone()
        conn.close()

        if row:
            data = json.loads(row[0])
            self.w_ih = data["w_ih"]  # input → hidden
            self.b_h = data["b_h"]
            self.w_ho = data["w_ho"]  # hidden → output
            self.b_o = data["b_o"]
        else:
            # Xavier initialization
            scale_ih = math.sqrt(2.0 / (self.INPUT_DIM + self.HIDDEN_DIM))
            scale_ho = math.sqrt(2.0 / (self.HIDDEN_DIM + self.OUTPUT_DIM))

            import random
            random.seed(42)

            self.w_ih = [
                [random.gauss(0, scale_ih) for _ in range(self.INPUT_DIM)]
                for _ in range(self.HIDDEN_DIM)
            ]
            self.b_h = [0.0] * self.HIDDEN_DIM

            self.w_ho = [
                [random.gauss(0, scale_ho) for _ in range(self.HIDDEN_DIM)]
                for _ in range(self.OUTPUT_DIM)
            ]
            self.b_o = [0.0] * self.OUTPUT_DIM

            self._save_weights()

    def _save_weights(self):
        data = json.dumps({
            "w_ih": self.w_ih,
            "b_h": self.b_h,
            "w_ho": self.w_ho,
            "b_o": self.b_o,
        })
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO weights (layer, data, updated_at) VALUES ('all', ?, ?)",
            (data, time.time())
        )
        conn.commit()
        conn.close()

    def _get_check_count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT COUNT(*) FROM check_log").fetchone()
        conn.close()
        return row[0] if row else 0

    def _forward(self, features: List[float]) -> Tuple[List[float], List[float]]:
        """Forward pass. Returns (hidden_activations, output)."""
        # Input → Hidden (ReLU)
        hidden = []
        for j in range(self.HIDDEN_DIM):
            z = self.b_h[j]
            for i in range(self.INPUT_DIM):
                z += self.w_ih[j][i] * features[i]
            hidden.append(_relu(z))

        # Hidden → Output (Sigmoid)
        output = []
        for k in range(self.OUTPUT_DIM):
            z = self.b_o[k]
            for j in range(self.HIDDEN_DIM):
                z += self.w_ho[k][j] * hidden[j]
            output.append(_sigmoid(z))

        return hidden, output

    def _backprop(self, features: List[float], hidden: List[float],
                  output: List[float], target: List[float]):
        """Single-sample backpropagation with SGD."""
        lr = self.LEARNING_RATE

        # Output layer gradients
        d_output = []
        for k in range(self.OUTPUT_DIM):
            err = output[k] - target[k]
            d_output.append(err * output[k] * (1.0 - output[k]))

        # Update hidden → output weights
        for k in range(self.OUTPUT_DIM):
            for j in range(self.HIDDEN_DIM):
                self.w_ho[k][j] -= lr * d_output[k] * hidden[j]
            self.b_o[k] -= lr * d_output[k]

        # Hidden layer gradients (ReLU derivative)
        d_hidden = []
        for j in range(self.HIDDEN_DIM):
            err = sum(d_output[k] * self.w_ho[k][j] for k in range(self.OUTPUT_DIM))
            d_hidden.append(err * (1.0 if hidden[j] > 0 else 0.0))

        # Update input → hidden weights
        for j in range(self.HIDDEN_DIM):
            for i in range(self.INPUT_DIM):
                self.w_ih[j][i] -= lr * d_hidden[j] * features[i]
            self.b_h[j] -= lr * d_hidden[j]

    def predict_risk(self, features: Union[dict, list]) -> dict:
        """
        Predict compliance risk from feature vector.

        Args:
            features: dict with FEATURE_NAMES keys (0.0-1.0) or list of 12 floats

        Returns:
            dict with risk scores, confidence, and feature importance
        """
        if isinstance(features, dict):
            fvec = [float(features.get(name, 0.0)) for name in self.FEATURE_NAMES]
        else:
            fvec = [float(x) for x in features[:self.INPUT_DIM]]
            fvec.extend([0.0] * (self.INPUT_DIM - len(fvec)))

        hidden, output = self._forward(fvec)

        # Compute feature importance via input gradient approximation
        importance = {}
        for i, name in enumerate(self.FEATURE_NAMES):
            grad_sum = sum(
                abs(self.w_ih[j][i]) * (1.0 if hidden[j] > 0 else 0.0)
                for j in range(self.HIDDEN_DIM)
            )
            importance[name] = round(grad_sum, 4)

        # Sort by importance
        top_factors = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]

        confidence = min(1.0, self.check_count / 100.0)  # Confidence grows with training data

        return {
            "predictions": {
                name: round(val, 4) for name, val in zip(self.OUTPUT_NAMES, output)
            },
            "confidence": round(confidence, 3),
            "checks_learned_from": self.check_count,
            "top_risk_factors": [
                {"factor": name, "weight": w} for name, w in top_factors
            ],
            "model": f"meok-compliance-nn-{self.server_name}",
        }

    def learn_from_check(self, features: Union[dict, list], outcome: Union[dict, list]) -> dict:
        """
        Train the network from a compliance check result.

        Args:
            features: input feature vector (dict or list)
            outcome: target output vector (dict with OUTPUT_NAMES or list of 4 floats)

        Returns:
            dict with loss and training stats
        """
        if isinstance(features, dict):
            fvec = [float(features.get(name, 0.0)) for name in self.FEATURE_NAMES]
        else:
            fvec = [float(x) for x in features[:self.INPUT_DIM]]
            fvec.extend([0.0] * (self.INPUT_DIM - len(fvec)))

        if isinstance(outcome, dict):
            tvec = [float(outcome.get(name, 0.5)) for name in self.OUTPUT_NAMES]
        else:
            tvec = [float(x) for x in outcome[:self.OUTPUT_DIM]]
            tvec.extend([0.5] * (self.OUTPUT_DIM - len(tvec)))

        # Forward
        hidden, output = self._forward(fvec)

        # Compute loss (MSE)
        loss = sum((output[k] - tvec[k]) ** 2 for k in range(self.OUTPUT_DIM)) / self.OUTPUT_DIM

        # Backward
        self._backprop(fvec, hidden, output, tvec)

        # Persist
        self._save_weights()
        self.check_count += 1

        # Log the check
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO check_log (features, outcome, prediction, loss, timestamp) VALUES (?, ?, ?, ?, ?)",
            (json.dumps(fvec), json.dumps(tvec), json.dumps(output), loss, time.time())
        )
        conn.commit()
        conn.close()

        # Update insights periodically
        if self.check_count % 10 == 0:
            self._update_insights()

        return {
            "loss": round(loss, 6),
            "check_number": self.check_count,
            "prediction_before": {name: round(v, 4) for name, v in zip(self.OUTPUT_NAMES, output)},
            "target": {name: round(v, 4) for name, v in zip(self.OUTPUT_NAMES, tvec)},
            "model_updated": True,
        }

    def _update_insights(self):
        """Compute and persist aggregate insights from training history."""
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT features, outcome, loss FROM check_log ORDER BY id DESC LIMIT 100"
        ).fetchall()
        conn.close()

        if not rows:
            return

        # Average feature values across recent checks
        avg_features = [0.0] * self.INPUT_DIM
        avg_outcomes = [0.0] * self.OUTPUT_DIM
        avg_loss = 0.0

        for fstr, ostr, loss in rows:
            fvec = json.loads(fstr)
            ovec = json.loads(ostr)
            for i in range(min(len(fvec), self.INPUT_DIM)):
                avg_features[i] += fvec[i]
            for k in range(min(len(ovec), self.OUTPUT_DIM)):
                avg_outcomes[k] += ovec[k]
            avg_loss += loss or 0.0

        n = len(rows)
        avg_features = [v / n for v in avg_features]
        avg_outcomes = [v / n for v in avg_outcomes]
        avg_loss /= n

        insights = {
            "total_checks": self.check_count,
            "avg_loss_last_100": round(avg_loss, 6),
            "avg_feature_profile": {
                name: round(v, 3) for name, v in zip(self.FEATURE_NAMES, avg_features)
            },
            "avg_outcome_profile": {
                name: round(v, 3) for name, v in zip(self.OUTPUT_NAMES, avg_outcomes)
            },
            "highest_risk_dimension": self.FEATURE_NAMES[
                avg_features.index(max(avg_features))
            ] if any(v > 0 for v in avg_features) else "none",
            "model_maturity": "initial" if self.check_count < 50
                else "developing" if self.check_count < 200
                else "trained" if self.check_count < 1000
                else "mature",
        }

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO insights (key, value, updated_at) VALUES ('summary', ?, ?)",
            (json.dumps(insights), time.time())
        )
        conn.commit()
        conn.close()

    def get_insights(self) -> dict:
        """Get aggregate learning insights."""
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT value FROM insights WHERE key='summary'").fetchone()
        conn.close()

        if row:
            return json.loads(row[0])

        return {
            "total_checks": self.check_count,
            "model_maturity": "untrained",
            "message": "Run compliance checks to train the neural learning module.",
        }

    def extract_features_from_system(
        self,
        system_name: str,
        system_type: str = "",
        uses_biometric: bool = False,
        uses_health_data: bool = False,
        uses_financial_data: bool = False,
        has_human_oversight: bool = True,
        affected_users: int = 0,
        sector: str = "",
        has_documentation: bool = False,
        prior_incidents: int = 0,
        deployed_cross_border: bool = False,
        model_explainable: bool = True,
        update_frequency_days: int = 30,
    ) -> dict:
        """
        Convert human-readable system description into a feature vector.
        Helper for users who don't want to construct raw features.
        """
        sector_risk_map = {
            "healthcare": 0.9, "finance": 0.85, "law_enforcement": 0.95,
            "education": 0.7, "employment": 0.8, "critical_infrastructure": 0.95,
            "social_media": 0.6, "entertainment": 0.3, "agriculture": 0.4,
            "retail": 0.5, "manufacturing": 0.6, "government": 0.85,
        }

        data_sensitivity = 0.2
        if uses_biometric:
            data_sensitivity = max(data_sensitivity, 0.9)
        if uses_health_data:
            data_sensitivity = max(data_sensitivity, 0.85)
        if uses_financial_data:
            data_sensitivity = max(data_sensitivity, 0.8)

        pop_scale = min(1.0, affected_users / 1_000_000) if affected_users > 0 else 0.1

        features = {
            "system_complexity": 0.5,  # Default medium
            "data_sensitivity": data_sensitivity,
            "autonomy_level": 0.3 if has_human_oversight else 0.8,
            "affected_population": pop_scale,
            "sector_risk": sector_risk_map.get(sector.lower(), 0.5),
            "existing_controls": 0.6 if has_human_oversight else 0.2,
            "documentation_quality": 0.7 if has_documentation else 0.1,
            "prior_violations": min(1.0, prior_incidents / 5.0),
            "cross_border": 0.8 if deployed_cross_border else 0.2,
            "model_transparency": 0.8 if model_explainable else 0.2,
            "update_frequency": min(1.0, 30.0 / max(1, update_frequency_days)),
            "vulnerability_exposure": 0.5,  # Default medium
        }

        return features
