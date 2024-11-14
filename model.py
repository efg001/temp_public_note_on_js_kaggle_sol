import torch
from torch import nn

class SimpleMLP(nn.Module):
    def __init__(self, config, input_dim, output_dim, hidden_dim, dropout=0.0, zeroinit=False):
        super(SimpleMLP, self).__init__()
        self.config = config

        # Input layer
        layers = [
            nn.Linear(input_dim, hidden_dim[0]),
            nn.ReLU(),
            nn.Dropout(dropout) if dropout > 0 else nn.Identity()
        ]
        self.mlp = nn.Sequential(*layers)
        
        if zeroinit:
            nn.init.zeros_(self.mlp[0].weight)

        # Hidden layers
        for i in range(1, len(hidden_dim)):
            hidden_layer = nn.Sequential(
                nn.Linear(hidden_dim[i - 1], hidden_dim[i]),
                nn.ReLU(),
                nn.Dropout(dropout) if dropout > 0 else nn.Identity()
            )
            self.mlp.add_module(f"hidden_{i}", hidden_layer)
            if zeroinit:
                nn.init.zeros_(self.mlp[-1][0].weight)

        # Output layer
        self.output_layer = nn.Linear(hidden_dim[-1], output_dim)

    def forward(self, x):
        x_hidden = self.mlp(x)
        x = self.output_layer(x_hidden)
        return x, x_hidden


class Model(nn.Module):
    """A model consisting of two SimpleMLP networks."""

    def __init__(self, config, n_layer=1, dropout=0.0):
        super(Model, self).__init__()
        self.config = config
        self.n_embd = config.d_model
        self.n_layer = n_layer
        self.dropout = dropout

        self.simplemlp1 = SimpleMLP(
            config,
            input_dim=77,
            output_dim=9,
            hidden_dim=[512] * 4,
            dropout=0.05,
            zeroinit=True
        )

        self.simplemlp2 = SimpleMLP(
            config,
            input_dim=77 + 512,
            output_dim=1,
            hidden_dim=[512] * 5,
            dropout=0.05,
            zeroinit=True
        )

    def forward(self, x):
        pred_all, hidden = self.simplemlp1(x)
        x_with_hidden = torch.cat([x, hidden], dim=-1)
        pred, _ = self.simplemlp2(x_with_hidden)
        return pred, pred_all

