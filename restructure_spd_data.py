import pandas as pd
import numpy as np

def restructure_spd_data(led_file, reference_file, output_file):
    """
    Restructures LED SPD data and reference data into a unified format.
    Normalizes LED data to 1 watt for each source.
    For each integer wavelength, keeps the record with the greatest measurement value.
    """
    try:
        # Load the data
        print(f"Loading LED data from: {led_file}")
        df_led = pd.read_excel(led_file, sheet_name=0)
        
        # Check if reference file is different from LED file
        if reference_file != led_file:
            print(f"Loading reference data from: {reference_file}")
            df_ref = pd.read_excel(reference_file)
        else:
            print("Reference file is the same as LED file. Looking for reference data in the same file.")
            # Assume reference data is in a column named 'Sun_Reference' or similar in the LED file
            if 'Sun_Reference' in df_led.columns:
                print("Found 'Sun_Reference' column in the LED file.")
                df_ref = df_led[['Wavelength', 'Sun_Reference']].copy()
            else:
                print("No 'Sun_Reference' column found. Creating a dummy reference column.")
                # Create a dummy reference DataFrame with the same wavelength range
                df_ref = pd.DataFrame({
                    'Wavelength': df_led['Wavelength'].unique(),
                    'Count': 0  # Default value
                })
        
        print("Original data shapes:")
        print(f"LED SPD: {df_led.shape}")
        print(f"Reference: {df_ref.shape}")
        
        # Display the last few rows to verify power values are there
        print("\nLast 3 rows of LED data to check power values:")
        print(df_led.tail(3))
        
        # Extract power values from the last row
        power_values = df_led.iloc[-1, 1:].to_dict()  # Skip the first column (Wavelength)
        print("\nExtracted power values:")
        for col, power in power_values.items():
            # Validate each power value
            if pd.isna(power) or not isinstance(power, (int, float)) or power <= 0:
                print(f"WARNING: Invalid power value for {col}: {power}")
            else:
                print(f"{col}: {power}")
        
        # Remove the last row (Powers row) from the LED data
        df_led = df_led.iloc[:-1].copy()  # Use .copy() to avoid SettingWithCopyWarning
        
        # Check for NaN values in the wavelength column
        if df_led['Wavelength'].isnull().any():
            print("NaN values found in LED SPD data. Cleaning data...")
            df_led = df_led[~df_led['Wavelength'].isnull()]
            print(f"Cleaned LED SPD data shape: {df_led.shape}")
        
        # Check data type of Wavelength column
        print(f"\nWavelength column data type: {df_led['Wavelength'].dtype}")
        
        # Convert Wavelength to numeric, coercing errors to NaN
        df_led['Wavelength'] = pd.to_numeric(df_led['Wavelength'], errors='coerce')
        
        # Drop rows with NaN in Wavelength after conversion
        if df_led['Wavelength'].isnull().any():
            print(f"Found {df_led['Wavelength'].isnull().sum()} non-numeric values in Wavelength column. Dropping these rows.")
            df_led = df_led.dropna(subset=['Wavelength'])
        
        # Create a new column with rounded integer wavelengths
        df_led['Wavelength_Int'] = df_led['Wavelength'].round().astype(int)
        
        # For each integer wavelength, find the row with maximum value (across all LED columns)
        print("\nFiltering wavelengths: keeping record with greatest value for each integer wavelength...")
        led_value_columns = [col for col in df_led.columns if col != 'Wavelength' and col != 'Wavelength_Int' and col != 'Sun_Reference']
        # Create a sum column to find the row with the highest overall value
        df_led['total_value'] = df_led[led_value_columns].sum(axis=1)
        df_led_filtered = df_led.loc[df_led.groupby('Wavelength_Int')['total_value'].idxmax()]
        df_led_filtered = df_led_filtered.drop('total_value', axis=1)
        
        # Now use the filtered data but restore the integer wavelength as the main column
        df_led_filtered['Wavelength'] = df_led_filtered['Wavelength_Int']
        df_led_filtered = df_led_filtered.drop('Wavelength_Int', axis=1)
        
        # Identify LED columns (exclude Wavelength and Sun_Reference)
        led_columns = [col for col in df_led_filtered.columns if col != 'Wavelength' and col != 'Sun_Reference']
        
        # Normalize LED data to 1 watt
        print("\nNormalizing LED data to 1 watt...")
        for col in led_columns:
            if col in power_values and isinstance(power_values[col], (int, float)) and power_values[col] > 0:
                print(f"Normalizing {col} with power value: {power_values[col]}")
                df_led_filtered[col] = df_led_filtered[col] / power_values[col]
            else:
                print(f"WARNING: No valid power value found for column '{col}'. Skipping normalization.")
        
        # Round reference wavelengths to integers
        df_ref['Wavelength'] = pd.to_numeric(df_ref['Wavelength'], errors='coerce')
        df_ref = df_ref.dropna(subset=['Wavelength'])
        
        # For reference data, also keep the record with the greatest value for each integer wavelength
        df_ref['Wavelength_Int'] = df_ref['Wavelength'].round().astype(int)
        
        # For reference data, find which column to use for maximum value determination
        ref_value_columns = [col for col in df_ref.columns if col != 'Wavelength' and col != 'Wavelength_Int']
        if len(ref_value_columns) > 0:
            # If there's a Sun_Reference column, use that, otherwise use the first non-wavelength column
            value_col = 'Sun_Reference' if 'Sun_Reference' in ref_value_columns else ref_value_columns[0]
            df_ref_filtered = df_ref.loc[df_ref.groupby('Wavelength_Int')[value_col].idxmax()]
        else:
            # Fallback if no value columns are found
            df_ref_filtered = df_ref.loc[df_ref.groupby('Wavelength_Int')['Wavelength'].idxmax()]
        
        df_ref_filtered['Wavelength'] = df_ref_filtered['Wavelength_Int'] 
        df_ref_filtered = df_ref_filtered.drop('Wavelength_Int', axis=1)
        
        # Create complete wavelength range
        min_wave = min(df_led_filtered['Wavelength'].min(), df_ref_filtered['Wavelength'].min())
        max_wave = max(df_led_filtered['Wavelength'].max(), df_ref_filtered['Wavelength'].max())
        all_wavelengths = list(range(int(min_wave), int(max_wave) + 1))
        
        # Create final DataFrame with all wavelengths
        df_final = pd.DataFrame({'Wavelength': all_wavelengths})
        
        # Merge LED data
        df_final = pd.merge(df_final, df_led_filtered, on='Wavelength', how='left')
        
        # Print available columns in reference data
        print(f"\nAvailable columns in reference data: {df_ref_filtered.columns.tolist()}")
        
        # Merge reference data
        if 'Count' in df_ref_filtered.columns:
            print("Using 'Count' column as reference data")
            df_final = pd.merge(
                df_final,
                df_ref_filtered[['Wavelength', 'Count']].rename(columns={'Count': 'Sun_Reference'}),
                on='Wavelength',
                how='left'
            )
        elif 'Sun_Reference' in df_ref_filtered.columns:
            print("Using existing 'Sun_Reference' column")
            df_final = pd.merge(
                df_final,
                df_ref_filtered[['Wavelength', 'Sun_Reference']],
                on='Wavelength',
                how='left'
            )
        else:
            print(f"WARNING: Neither 'Count' nor 'Sun_Reference' column found in reference data.")
            # Try to find a suitable column for reference data
            if len(df_ref_filtered.columns) >= 2:
                ref_col = df_ref_filtered.columns[1]  # Use the second column as reference
                print(f"Using '{ref_col}' as reference column")
                df_final = pd.merge(
                    df_final,
                    df_ref_filtered[['Wavelength', ref_col]].rename(columns={ref_col: 'Sun_Reference'}),
                    on='Wavelength',
                    how='left'
                )
            else:
                print("No suitable reference column found. Adding empty Sun_Reference column.")
                df_final['Sun_Reference'] = 0
        
        # Check for NaN values after merging
        nan_count = df_final.isna().sum().sum()
        if nan_count > 0:
            print(f"\nFilling {nan_count} NaN values with 0")
            print(df_final.isna().sum())
        
        # Fill NaN values with 0
        df_final = df_final.fillna(0)
        
        # Sort by wavelength
        df_final = df_final.sort_values('Wavelength')
        
        # Verify Sun_Reference column exists
        if 'Sun_Reference' not in df_final.columns:
            print("WARNING: Sun_Reference column not created. Adding empty column.")
            df_final['Sun_Reference'] = 0
        
        # Save to Excel
        df_final.to_excel(output_file, index=False)
        
        print("\nData restructuring completed:")
        print(f"Wavelength range: {int(min_wave)} - {int(max_wave)} nm")
        print(f"Number of wavelengths: {len(df_final)}")
        print(f"Number of sources: {len(df_final.columns) - 1}")  # -1 for wavelength column
        print(f"Columns in final output: {df_final.columns.tolist()}")
        print(f"\nData saved to: {output_file}")
        
        return df_final
        
    except Exception as e:
        print(f"Error processing data: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

# File paths
led_file = r"d:\Desktop\Broad-Scope Analysis\All LED_SPD (powers added).xlsx"
reference_file = r"d:\Desktop\Broad-Scope Analysis\Refernce.xlsx"  # Make sure this is the correct path to your reference file
output_file = r"d:\Desktop\Broad-Scope Analysis\Combined_SPD_Data for 1 w.xlsx"

# Execute the restructuring
df_combined = restructure_spd_data(led_file, reference_file, output_file)