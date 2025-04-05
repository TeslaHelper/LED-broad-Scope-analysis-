LED Spectral Data Analysis

This repository provides a set of Python scripts to process and analyze LED spectral power distribution (SPD) data. The workflow involves preparing raw LED data by adding a reference sun spectrum and normalizing power, normalizing the SPD values, and performing detailed analyses such as color rendering, luminous efficacy, and blue light hazard assessments. The scripts are designed to work sequentially, producing cleaned data and insightful visualizations.

Repository Structure
- data/ : Directory for storing input and output data files (e.g., .xlsx files).
- scripts/ : Contains the Python scripts for data processing and analysis.
- README.md : This file, providing an overview and usage instructions.

Note: You’ll need to create the data/ and scripts/ folders in your repository and place the scripts and data files accordingly.

Scripts

1. prepare_spd_data.py
Purpose: Prepares raw LED spectral data by adding a reference sun spectrum and normalizing the power of each source to 1 watt. It also cleans and restructures the data for subsequent processing.

Usage:
python scripts/prepare_spd_data.py --led_file path/to/led_data.xlsx --reference_file path/to/reference.xlsx --output_file path/to/output.xlsx

Command-Line Arguments:
--led_file: Path to the Excel file with raw LED SPD data (required).
--reference_file: Path to the Excel file with the reference sun spectrum (required).
--output_file: Path to save the prepared data (required).

Input:
- An Excel file (e.g., led_data.xlsx) with:
  - First column: Wavelength (in nm).
  - Subsequent columns: SPD values for each LED sample.
  - Last row: Power values for each sample (in watts).
- A reference Excel file (e.g., reference.xlsx) with:
  - First column: Wavelength (in nm).
  - Second column: Reference sun spectrum (e.g., Sun_Reference).

Output:
- An Excel file (e.g., output.xlsx) with wavelengths and normalized SPD values, including a Sun_Reference column.

Features:
- Cleans data by removing NaN values.
- Rounds wavelengths to integers.
- Normalizes each sample’s power to 1 watt.

---

2. normalize_spd.py
Purpose: Normalizes the SPD values ofyekthe samples so that the total power (integral over wavelength) equals 1, preparing the data for analysis.

Usage:
python scripts/normalize_spd.py --input_file path/to/prepared_data.xlsx --output_file path/to/normalized_data.xlsx

Command-Line Arguments:
--input_file: Path to the Excel file with prepared SPD data (required).
--output_file: Path to save the normalized data (required).

Input:
- An Excel file from prepare_spd_data.py (e.g., prepared_data.xlsx) with:
  - First column: Wavelength (in nm).
  - Subsequent columns: SPD values for each sample and the reference.

Output:
- An Excel file (e.g., normalized_data.xlsx) with normalized SPD values.

Features:
- Removes NaN or infinite values.
- Normalizes SPD using trapezoidal integration of total power.

---

3. analyze_led_spd.py
Purpose: Performs comprehensive analysis of normalized LED SPD data, calculating metrics like color rendering index (CRI), luminous efficacy, and blue light hazard (BLH), while generating visualizations such as chromaticity diagrams and SPD plots.

Usage:
python scripts/analyze_led_spd.py --input_file path/to/normalized_data.xlsx --output_folder path/to/output/folder

Command-Line Arguments:
--input_file: Path to the Excel file with normalized SPD data (required).
--output_folder: Directory to save analysis results and plots (required).

Input:
- An Excel file from normalize_spd.py (e.g., normalized_data.xlsx) with:
  - First column: Wavelength (in nm).
  - Subsequent columns: Normalized SPD values for each sample.

Output:
- Data Files (in output_folder/data/):
  - LED_Analysis_Results.xlsx: Results including CCT, CRI, luminous efficacy, etc.
  - correlation_matrix.xlsx: Correlation matrix of parameters.
- Plots (in output_folder/plots/):
  - Chromaticity diagrams.
  - Overlain SPD plots.
  - Correlation matrix heatmap.

Features:
- Calculates advanced metrics (e.g., CRI, Rf, Rg, BLH).
- Produces detailed visualizations.

---

Dependencies
Install the required Python packages with:
pip install pandas numpy scipy colour-science matplotlib seaborn plotly xlsxwriter

- pandas: Data manipulation.
- numpy: Numerical operations.
- scipy: Signal processing.
- colour-science: Colorimetry.
- matplotlib: Static plots.
- seaborn: Enhanced visualizations.
- plotly: Interactive plots.
- xlsxwriter: Excel output.

---

Usage Instructions
1. Prepare Your Data:
   - Place your raw LED SPD data and reference files in the data/ folder.

2. Run the Scripts:
   python scripts/prepare_spd_data.py --led_file data/led_data.xlsx --reference_file data/reference.xlsx --output_file data/prepared_data.xlsx
   python scripts/normalize_spd.py --input_file data/prepared_data.xlsx --output_file data/normalized_data.xlsx
   python scripts/analyze_led_spd.py --input_file data/normalized_data.xlsx --output_folder data/output/

3. Review Outputs:
   - Check the data/output/ folder for results and plots.

---

This README provides a complete guide to using the repository. Adjust file paths or details as needed for your setup!
