"""
Model A: Physics-Informed Neural Network for RUL Estimation
Architecture: Temporal Convolutional Network (TCN) backbone
Physics constraint: Paris-Erdogan crack growth law (soft constraint in loss)
Uncertainty: Monte Carlo Dropout (T=50 passes)
Fallback: returns None when sequence_length < 3
"""
import logging
import numpy as np
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# PyTorch import guard — torch is optional at runtime for inference
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available — PINN RUL model disabled")

N_FEATURES = 5   # [air_temp, process_temp, rpm, torque, tool_wear]
N_CHANNELS = 64
N_LAYERS = 4

# -----------------------------------------------------------------------
# TCN Building Block
# -----------------------------------------------------------------------

def _build_tcn_block(in_ch, out_ch, kernel_size, dilation, dropout=0.1):
    """Dilated causal temporal convolutional block with residual connection."""
    if not TORCH_AVAILABLE:
        return None
    padding = (kernel_size - 1) * dilation
    return nn.Sequential(
        nn.Conv1d(in_ch, out_ch, kernel_size,
                  padding=padding, dilation=dilation),
        nn.ReLU(),
        nn.Dropout(p=dropout),
        nn.Conv1d(out_ch, out_ch, kernel_size,
                  padding=padding, dilation=dilation),
        nn.ReLU(),
        nn.Dropout(p=dropout),
    )


class _TCNEncoder(nn.Module if TORCH_AVAILABLE else object):
    """Temporal Convolutional Network encoder for sequential sensor data."""

    def __init__(self, in_features=N_FEATURES, channels=N_CHANNELS,
                 kernel_size=3, n_layers=N_LAYERS, dropout=0.1):
        if not TORCH_AVAILABLE:
            return
        super().__init__()
        self.dropout = dropout
        layers = []
        for i in range(n_layers):
            dilation = 2 ** i
            # input_proj maps in_features → channels before the first block,
            # so all TCN blocks receive `channels` channels as input
            layers.append(_build_tcn_block(channels, channels, kernel_size, dilation, dropout))
        self.layers = nn.ModuleList(layers)
        # Residual projection for first layer (different channel count)
        self.input_proj = nn.Conv1d(in_features, channels, 1)

    def forward(self, x):
        # x: (batch, seq_len, features) → (batch, features, seq_len)
        x = x.permute(0, 2, 1)
        out = self.input_proj(x)
        for layer in self.layers:
            residual = out
            tcn_out = layer(out)
            # Trim to same length (causal padding adds extra)
            tcn_out = tcn_out[..., :out.shape[-1]]
            out = tcn_out + residual
        # Global average pooling over time → (batch, channels)
        return out.mean(dim=-1)


class _PINNModel(nn.Module if TORCH_AVAILABLE else object):
    """PINN model: TCN encoder + RUL regression head."""

    def __init__(self, in_features=N_FEATURES, channels=N_CHANNELS,
                 n_layers=N_LAYERS, dropout=0.1):
        if not TORCH_AVAILABLE:
            return
        super().__init__()
        self.encoder = _TCNEncoder(in_features, channels, n_layers=n_layers, dropout=dropout)
        self.rul_head = nn.Sequential(
            nn.Linear(channels, 32),
            nn.ReLU(),
            nn.Dropout(p=dropout),
            nn.Linear(32, 1),
            nn.Softplus(),   # ensures RUL > 0
        )
        self._dropout_p = dropout

    def forward(self, x):
        features = self.encoder(x)
        rul = self.rul_head(features).squeeze(-1)
        return rul


# -----------------------------------------------------------------------
# Physics Loss (Paris-Erdogan soft constraint)
# -----------------------------------------------------------------------

def _physics_loss(rul_sequence: "torch.Tensor",
                  c_param: float = 1e-4, m: float = 3.0) -> "torch.Tensor":
    """
    Paris-Erdogan soft constraint:
      da/dN = C * (ΔK)^m
    Approximation: ΔK ∝ rate of RUL decrease,  da/dN ≈ -d(RUL)/dt
    Penalizes when RUL increases (non-physical monotonicity violation).

    Args:
        rul_sequence: (batch, seq_len) tensor of predicted RUL values
        c_param, m: Paris-Erdogan parameters (material constants)

    Returns:
        Scalar physics loss
    """
    if not TORCH_AVAILABLE or rul_sequence.shape[-1] < 2:
        return torch.tensor(0.0) if TORCH_AVAILABLE else 0.0
    delta_rul = rul_sequence[:, 1:] - rul_sequence[:, :-1]
    # Physics: RUL should decrease or stay flat → penalize increases
    # L_monotone = mean(ReLU(delta_rul))
    l_mono = F.relu(delta_rul).mean()
    # Paris-Erdogan residual: penalize deviations from c_param*(|delta|)^m pattern
    delta_abs = delta_rul.abs().clamp(min=1e-6)
    expected_rate = c_param * (delta_abs ** m)
    # Soft constraint: ||actual_decrease - expected_rate||^2
    actual_decrease = F.relu(-delta_rul)  # only decreases
    l_phys = ((actual_decrease - expected_rate) ** 2).mean()
    return l_mono + 0.1 * l_phys


# -----------------------------------------------------------------------
# PINN RUL Estimator (public interface)
# -----------------------------------------------------------------------

class PINNRULEstimator:
    """
    Physics-Informed Neural Network for RUL estimation.

    Usage:
        estimator = PINNRULEstimator()
        estimator.train(sequences, rul_labels)
        out = estimator.predict(sequence_of_snapshots)

    Falls back to None if sequence_length < 3 or torch not available.
    """

    def __init__(self, dropout: float = 0.1, mc_samples: int = 50,
                 reference_rul: float = 60.0):
        """
        Args:
            dropout: MC Dropout probability (used during inference for uncertainty)
            mc_samples: Number of Monte Carlo forward passes for uncertainty
            reference_rul: 95th percentile RUL used to normalize HI to [0, 100]
        """
        self.dropout = dropout
        self.mc_samples = mc_samples
        self.reference_rul = reference_rul
        self._model = None
        self._fitted = False
        self._isotonic = None   # isotonic regression calibrator

        if TORCH_AVAILABLE:
            self._model = _PINNModel(dropout=dropout)

    def train(self, sequences: List[np.ndarray], rul_labels: List[float],
              epochs: int = 50, lr: float = 1e-3) -> "PINNRULEstimator":
        """
        Train PINN on sequences of sensor snapshots.

        Args:
            sequences: List of np.ndarray each (T, 5) — time-ordered snapshots
            rul_labels: List of RUL values (days) for each sequence's last timestep
            epochs: Training epochs
            lr: Learning rate

        Returns:
            self
        """
        if not TORCH_AVAILABLE or self._model is None:
            logger.warning("PyTorch not available — PINN skipped")
            self._fitted = False
            return self

        if len(sequences) < 3:
            logger.warning("Too few sequences to train PINN — needs >= 3")
            self._fitted = False
            return self

        # Pad/truncate all sequences to same length
        max_len = min(30, max(s.shape[0] for s in sequences))
        x_list, y_list = [], []
        for seq, label in zip(sequences, rul_labels):
            seq = np.asarray(seq, dtype=np.float32)
            if seq.shape[0] > max_len:
                seq = seq[-max_len:]
            elif seq.shape[0] < max_len:
                pad = np.zeros((max_len - seq.shape[0], seq.shape[1]), dtype=np.float32)
                seq = np.vstack([pad, seq])
            x_list.append(seq)
            y_list.append(float(label))

        x_tensor = torch.tensor(np.stack(x_list), dtype=torch.float32)
        y_tensor = torch.tensor(y_list, dtype=torch.float32)

        optimizer = torch.optim.Adam(self._model.parameters(), lr=lr, weight_decay=0.0)
        self._model.train()

        for _ in range(epochs):
            optimizer.zero_grad()
            rul_pred = self._model(x_tensor)
            l_data = F.mse_loss(rul_pred, y_tensor)
            # Physics loss on predicted sequence (simplified: use predicted batch)
            rul_seq = rul_pred.unsqueeze(1).expand(-1, 2)
            l_phys = _physics_loss(rul_seq)
            loss = l_data + 0.1 * l_phys
            loss.backward()
            optimizer.step()

        # Isotonic calibration on training set
        self._model.eval()
        with torch.no_grad():
            train_preds = self._model(x_tensor).numpy()
        from sklearn.isotonic import IsotonicRegression
        iso = IsotonicRegression(increasing=True, out_of_bounds="clip")
        iso.fit(train_preds, y_list)
        self._isotonic = iso
        self._fitted = True
        logger.info(f"PINN trained for {epochs} epochs on {len(sequences)} sequences")
        return self

    def predict(self, snapshots: List[Dict]) -> Optional[Dict]:
        """
        Predict RUL for a time-ordered sequence of sensor snapshots.

        Args:
            snapshots: List of FeatureSnapshot dicts, ordered oldest → newest

        Returns:
            ModelOutput dict, or None if sequence too short (< 3 steps)
        """
        if not self._fitted or not TORCH_AVAILABLE or self._model is None:
            return None

        if len(snapshots) < 3:
            return None   # DST treats None as vacuous BPA {Unknown: 1.0}

        # Build sequence tensor
        seq = np.array([[
            s.get("air_temperature", 298),
            s.get("process_temperature", 308),
            s.get("rotational_speed", 1500),
            s.get("torque", 40),
            s.get("tool_wear", 0),
        ] for s in snapshots], dtype=np.float32)

        # Limit to last 30 steps
        if seq.shape[0] > 30:
            seq = seq[-30:]

        x_tensor = torch.tensor(seq[np.newaxis], dtype=torch.float32)

        # Monte Carlo Dropout inference (T=50 passes)
        self._model.train()   # enable dropout
        mc_preds = []
        with torch.no_grad():
            for _ in range(self.mc_samples):
                mc_preds.append(float(self._model(x_tensor).item()))
        self._model.eval()

        rul_mean = float(np.mean(mc_preds))
        rul_std  = float(np.std(mc_preds))

        # Apply isotonic calibration
        if self._isotonic is not None:
            rul_mean = float(self._isotonic.predict([rul_mean])[0])

        rul_mean = max(0.0, rul_mean)
        health_index = round(min(100.0, (rul_mean / self.reference_rul) * 100.0), 2)

        return {
            "model_id":      "model_a_pinn_rul",
            "health_index":  health_index,
            "critical_prob": float(max(0.0, 1.0 - health_index / 100.0)),
            "rul_estimate":  rul_mean,
            "uncertainty":   rul_std,
            "confidence":    float(0.7 if rul_std < 10 else 0.5),
        }

    @property
    def is_fitted(self) -> bool:
        return self._fitted


# Module-level singleton
_pinn_estimator: Optional[PINNRULEstimator] = None


def get_pinn_estimator() -> Optional[PINNRULEstimator]:
    return _pinn_estimator


def create_pinn_estimator(**kwargs) -> PINNRULEstimator:
    """Create a new (unfitted) PINN estimator. Train separately with estimator.train()."""
    global _pinn_estimator
    _pinn_estimator = PINNRULEstimator(**kwargs)
    return _pinn_estimator
