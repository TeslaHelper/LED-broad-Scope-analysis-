import pandas as pd
import numpy as np

# Load the Excel file
file_path = r'd:\Desktop\Broad-Scope Analysis\Combined_SPD_Data for 1 w.xlsx'
df = pd.read_excel(file_path)

# Drop rows with NaN or infinite values in 'Wavelength'
df = df.dropna(subset=['Wavelength'])
df = df[np.isfinite(df['Wavelength'])]

# Round and convert 'Wavelength' to integers
df['Wavelength'] = df['Wavelength'].round().astype(int)

# Filter wavelengths to retain only those between 380 and 780 nm
df = df[(df['Wavelength'] >= 380) & (df['Wavelength'] <= 780)]

# Group by unique wavelengths and average the counts for duplicate wavelengths
df_grouped = df.groupby('Wavelength').mean().reset_index()

# Normalize each sample's SPD (excluding the 'Wavelength' column)
wavelength_diff = np.diff(df_grouped['Wavelength'], prepend=df_grouped['Wavelength'][0])
for col in df_grouped.columns[1:]:
    spd = df_grouped[col]
    total_power = np.sum(spd * wavelength_diff)  # Calculate the total power (integral)
    df_grouped[col] = spd / total_power          # Normalize the SPD

# Save the normalized data to a new Excel file
output_path = r'd:\Desktop\Broad-Scope Analysis\Normalaized value and for 1 W.xlsx'
df_grouped.to_excel(output_path, index=False)

print("Normalization complete. The results are saved in:", output_path)