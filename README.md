# LED Spectral Data Analysis

This repository provides a set of Python scripts to process and analyze LED spectral power distribution (SPD) data. The workflow involves preparing raw LED data by adding a reference sun spectrum and normalizing power, normalizing the SPD values, and performing detailed analyses such as color rendering, luminous efficacy, and blue light hazard assessments. The scripts are designed to work sequentially, producing cleaned data and insightful visualizations.

## Repository Structure

- **`data/`**: Directory for storing input and output data files (e.g., `.xlsx` files).
- **`scripts/`**: Contains the Python scripts for data processing and analysis.
- **`README.md`**: This file, providing an overview and usage instructions.

**Note**: You’ll need to create the `data/` and `scripts/` folders in your repository and place the scripts and data files accordingly.

## Scripts

### 1. `prepare_spd_data.py`

**Purpose**: Prepares raw LED spectral data by adding a reference sun spectrum and normalizing the power of each source to 1 watt. It also cleans and restructures the data for subsequent processing.

**Usage**:
```bash
python scripts/prepare_spd_data.py --led_file path/to/led_data.xlsx --reference_file path/to/reference.xlsx --output_file path/to/output.xlsx
