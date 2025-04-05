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
Command-Line Arguments:

--led_file: Path to the Excel file with raw LED SPD data (required).
--reference_file: Path to the Excel file with the reference sun spectrum (required).
--output_file: Path to save the prepared data (required).
Input:

An Excel file (e.g., All LED_SPD (powers added).xlsx) with:
First column: Wavelength (in nm).
Subsequent columns: SPD values for each LED sample.
Last row: Power values for each sample (in watts).
A reference Excel file (e.g., Refernce.xlsx) with:
First column: Wavelength (in nm).
Second column: Reference sun spectrum (e.g., Sun_Reference or similar).
Output:

An Excel file (e.g., Combined_SPD_Data for 1 w.xlsx) with wavelengths and normalized SPD values, including a Sun_Reference column.
Features:

Handles data cleaning (e.g., removes NaN values).
Rounds wavelengths to integers.
Normalizes each sample’s power to 1 watt.
2. normalize_spd.py
Purpose: Normalizes the SPD values of the samples so that the total power (integral over wavelength) equals 1, preparing the data for analysis.

Usage:

bash

Collapse

Wrap

Copy
python scripts/normalize_spd.py --input_file path/to/prepared_data.xlsx --output_file path/to/normalized_data.xlsx
Command-Line Arguments:

--input_file: Path to the Excel file with prepared SPD data (required).
--output_file: Path to save the normalized data (required).
Input:

An Excel file from prepare_spd_data.py (e.g., Combined_SPD_Data for 1 w.xlsx) with:
First column: Wavelength (in nm).
Subsequent columns: SPD values for each sample and the reference.
Output:

An Excel file (e.g., Normalaized value and for 1 W.xlsx) with normalized SPD values.
Features:

Removes NaN or infinite values.
Computes total power using trapezoidal integration and normalizes SPD accordingly.
3. analyze_led_spd.py
Purpose: Performs a comprehensive analysis of normalized LED SPD data, calculating metrics like color rendering index (CRI), luminous efficacy, blue light hazard (BLH), and more. It also generates visualizations such as chromaticity diagrams and SPD plots.

Usage:

bash

Collapse

Wrap

Copy
python scripts/analyze_led_spd.py --input_file path/to/normalized_data.xlsx --output_folder path/to/output/folder
Command-Line Arguments:

--input_file: Path to the Excel file with normalized SPD data (required).
--output_folder: Directory to save analysis results and plots (required).
Input:

An Excel file from normalize_spd.py (e.g., Normalaized value and for 1 W.xlsx) with:
First column: Wavelength (in nm).
Subsequent columns: Normalized SPD values for each sample (e.g., Sample1, Sample2, etc.).
Optional metadata columns (e.g., Manufacturer1, Model1, Date1 for Sample1).
Output:

Data Files (in output_folder/data/):
LED_Analysis_Results.xlsx: Detailed results for each sample (CCT, CRI, Rf, Rg, etc.).
LED_Analysis_Results.csv: Same results in CSV format.
correlation_matrix.xlsx: Correlation matrix of calculated parameters.
Plots (in output_folder/plots/):
Chromaticity diagrams (e.g., chromaticity_group_1.jpg).
Overlain SPD plots (e.g., overlain_spds_all.png).
Correlation matrix heatmap (e.g., correlation_matrix_high_res.png).
Interactive HTML plots (e.g., parameter_relationships_matrix.html).
Reports (in output_folder/reports/):
TM-30-18 reports (e.g., tm30_18_Sample1.jpg) if enabled.
Features:

Calculates CCT, CRI, Rf, Rg, luminous efficacy, dominant wavelength, color purity, peak wavelength, FWHM, BLH, and more.
Generates advanced visualizations (e.g., 3D scatter plots, chromaticity diagrams with MacAdam ellipses).
Supports metadata for each sample (manufacturer, model, date).
Dependencies
The scripts rely on the following Python packages. Install them using:

bash

Collapse

Wrap

Copy
pip install pandas numpy scipy colour-science matplotlib seaborn plotly xlsxwriter
pandas: Data manipulation and Excel I/O.
numpy: Numerical computations.
scipy: Signal processing (e.g., FWHM calculation).
colour-science: Colorimetry and lighting analysis.
matplotlib: Static plotting.
seaborn: Enhanced visualizations (e.g., correlation heatmaps).
plotly: Interactive plots.
xlsxwriter: Formatted Excel output.
Data Format
Input Data
Raw LED Data (for prepare_spd_data.py):
Excel file with wavelengths (nm) in the first column, SPD values in subsequent columns, and power values in the last row.
Example:
text

Collapse

Wrap

Copy
Wavelength | Sample1 | Sample2 | ...
380        | 0.001   | 0.002   | ...
385        | 0.002   | 0.003   | ...
...        | ...     | ...     | ...
Power      | 2.5     | 3.0     | ...
Reference Data (for prepare_spd_data.py):
Excel file with wavelengths (nm) in the first column and sun reference SPD in the second column.
Example:
text

Collapse

Wrap

Copy
Wavelength | Sun_Reference
380        | 0.005
385        | 0.006
...        | ...
Intermediate and Final Data
Prepared Data (output of prepare_spd_data.py, input to normalize_spd.py):
Excel file with normalized power (1 watt) and added reference column.
Normalized Data (output of normalize_spd.py, input to analyze_led_spd.py):
Excel file with SPD values normalized by total power.
Usage Instructions
Prepare Your Data:
Place your raw LED SPD data and reference sun spectrum files in the data/ folder.
Ensure the files follow the expected format (see "Data Format").
Run the Scripts:
Execute the scripts in sequence:
bash

Collapse

Wrap

Copy
python scripts/prepare_spd_data.py --led_file data/led_data.xlsx --reference_file data/reference.xlsx --output_file data/prepared_data.xlsx
python scripts/normalize_spd.py --input_file data/prepared_data.xlsx --output_file data/normalized_data.xlsx
python scripts/analyze_led_spd.py --input_file data/normalized_data.xlsx --output_folder data/output/
Review Outputs:
Check the data/output/ folder for results, plots, and reports.
Notes
File Paths: Update the hardcoded file paths in the scripts to use command-line arguments as shown above for flexibility.
Column Names: The scripts assume specific column names (e.g., Wavelength, Sun_Reference). Adjust your data or the scripts if names differ.
TM-30-18 Reports: Enable TM-30-18 report generation in analyze_led_spd.py by setting run_tm30_report=True in the LEDAnalyzer config if desired.
Error Handling: The scripts include logging and error messages; check led_analysis.log for debugging.
For detailed implementation details, refer to the comments within each script.
