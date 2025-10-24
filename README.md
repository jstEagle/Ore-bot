# ORE Mining Optimization Bot

A Python bot that finds the optimal allocation of SOL across a 5x5 grid of blocks to maximize expected value (EV) in the ORE mining game, accounting for protocol fees and opponent strategies.

## Overview

This bot uses a greedy discrete marginal-EV allocation algorithm to determine the most profitable way to distribute your SOL budget across 25 blocks in the ORE mining game. It considers:

- **Protocol fees** (default 10% on mining rewards)
- **Opponent strategies** (other miners' allocations)
- **Discrete optimization** (budget divided into small units for precise allocation)
- **Expected value maximization** (focuses on SOL returns, treating ORE as bonus)

## Features

- 🎯 **Greedy Optimization**: Allocates budget in discrete units to maximize marginal EV
- 📊 **Grid Analysis**: Works with 5x5 block grids (25 total blocks)
- 💰 **Fee-Aware**: Accounts for protocol fees on mining rewards
- 📈 **EV Calculation**: Provides detailed expected value analysis
- 🔧 **Flexible Input**: Supports CSV files or command-line grid input
- 📋 **Detailed Output**: Shows allocation recommendations and marginal EV per block

## Installation

### Prerequisites

- Python 3.6 or higher
- NumPy library

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd ore_bot
```

2. Install dependencies:
```bash
pip install numpy
```

## Usage

### Basic Usage

```bash
python main.py --budget 0.5
```

This will use the default sample grid and allocate 0.5 SOL optimally.

### Advanced Usage

#### Using Custom Opponent Grid (Command Line)
```bash
python main.py --budget 1.0 --unit 0.001 --other "0.25,0.27,0.30,0.28,0.26,0.24,0.29,0.31,0.27,0.25,0.28,0.30,0.26,0.29,0.27,0.25,0.28,0.30,0.26,0.29,0.27,0.25,0.28,0.30,0.26"
```

#### Using CSV File for Opponent Grid
```bash
python main.py --budget 0.5 --unit 0.01 --grid-file opponents.csv
```

#### Custom Protocol Fee
```bash
python main.py --budget 1.0 --protocol-fee 0.15
```

### Command Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--budget` | float | **Required** | Total SOL budget to deploy (gross) |
| `--unit` | float | 0.001 | Discretization unit for allocation (SOL) |
| `--other` | string | None | 25 comma-separated numbers for opponent grid |
| `--grid-file` | string | None | CSV file containing 25 numbers for opponent grid |
| `--protocol-fee` | float | 0.10 | Protocol fee fraction on mining rewards |
| `--max-iters` | int | None | Maximum allocation iterations (default: budget/unit) |

## Expected Value (EV) Calculation

The bot uses a sophisticated EV calculation that accounts for the probabilistic nature of block selection and protocol fees:

### Core EV Formula

```
EV = Expected_Return_After_Protocol_Fee - Total_Cost
```

### Detailed Components

1. **Expected Return Calculation**:
   ```
   Expected_Return = Σ(Probability_Block_i_Wins × Payout_if_Block_i_Wins) / 25
   ```

2. **Payout per Block**:
   ```
   Payout_i = Your_Stake_i + Reward_i
   Reward_i = (Your_Stake_i / Total_Stake_i) × Sum_Of_Other_Stakes
   ```

3. **Protocol Fee Application**:
   ```
   Expected_Rewards_After_Fee = Expected_Rewards_Before_Fee × (1 - Protocol_Fee)
   Expected_Return_After_Fee = Expected_Kept_Stakes + Expected_Rewards_After_Fee
   ```

4. **Final EV**:
   ```
   EV_SOL_After_Fees = Expected_Return_After_Protocol_Fee - Total_Deployed_SOL
   ```

### Key Assumptions

- Each block has equal probability (1/25) of being selected
- Protocol fee is applied only to the reward portion, not the kept stakes
- ORE tokens are treated as bonus (not included in EV calculation)
- No admin fees (amounts sit in pool as deployed)

## Algorithm

The bot uses a **greedy discrete marginal-EV allocation** algorithm:

1. **Discretize** the budget into small units (default 0.001 SOL)
2. **Calculate** marginal EV for adding one unit to each block
3. **Select** the block with the highest positive marginal EV
4. **Allocate** one unit to that block
5. **Repeat** until budget exhausted or no positive marginal EVs remain

## Input Format

### CSV File Format
Create a CSV file with 25 numbers representing opponent allocations (row-major order):
```csv
0.3356,0.3281,0.346,0.3346,0.3148
0.3745,0.341,0.3288,0.3097,0.3339
0.3669,0.3444,0.3456,0.3495,0.3425
0.3402,0.3399,0.3118,0.3346,0.3227
0.3172,0.3455,0.3681,0.3423,0.3198
```

### Command Line Format
```bash
--other "0.3356,0.3281,0.346,0.3346,0.3148,0.3745,0.341,0.3288,0.3097,0.3339,0.3669,0.3444,0.3456,0.3495,0.3425,0.3402,0.3399,0.3118,0.3346,0.3227,0.3172,0.3455,0.3681,0.3423,0.3198"
```

## Output

The bot provides:

- **Recommended allocation** per block (5x5 grid)
- **Expected SOL EV** after fees
- **Total deployed** vs **expected return**
- **Top allocations** (blocks with highest stakes)
- **Marginal EV** for adding one more unit to each block

## Example Output

```
--- Results ---
Total deployed (gross): 0.500000 SOL
Total deployed (net in pool): 0.500000 SOL
Expected final SOL returned after round (post protocol-fee): 0.523456 SOL
Expected SOL EV after fees: 0.023456 SOL

Top allocations (index 0..24, row-major):
  block #12: allocate 0.045000 SOL (net in pool 0.045000 SOL)
  block #07: allocate 0.042000 SOL (net in pool 0.042000 SOL)
  ...

Marginal EV for adding one unit to each block:
  block 00: marginal = +0.0001234567 SOL
  block 01: marginal = +0.0000987654 SOL
  ...
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Disclaimer

This bot is for educational and research purposes. Always verify calculations and consider all risks before using in live trading scenarios.
