import logging
import time
import traceback
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns

from colour import (
    CCS_ILLUMINANTS,
    SpectralDistribution,
    colorimetric_purity,
    colour_fidelity_index,
    colour_quality_scale,
    colour_rendering_index,
    dominant_wavelength,
    sd_to_XYZ,
)
from colour.colorimetry import (
    SDS_LEFS_PHOTOPIC,
    reshape_sd,
    sd_to_XYZ,
)
from colour.constants import CONSTANT_K_M
from colour.models import (
    DATA_MACADAM_1942_ELLIPSES,
    Luv_to_uv,
    XYZ_to_Luv,
    XYZ_to_xy,
)
from colour.plotting import (
    colour_style,
    plot_chromaticity_diagram_CIE1976UCS,
    plot_planckian_locus_in_chromaticity_diagram_CIE1976UCS,
    plot_single_sd_colour_rendition_report,
)
from colour.plotting.tm3018.components import (
    plot_colour_fidelity_indexes,
    plot_colour_vector_graphic,
    plot_local_chroma_shifts,
    plot_local_colour_fidelities,
    plot_local_hue_shifts,
    plot_spectra_ANSIIESTM3018,
)
from colour.quality import (
    colour_fidelity_index_ANSIIESTM3018,
    colour_rendering_index,
)
from colour.temperature import XYZ_to_CCT_Ohno2013
from colour.utilities import (
    as_float_scalar,
    message_box,
    optional,
)

def get_reference_illuminant_for_cct(sd_test):
    specification = colour_fidelity_index_ANSIIESTM3018(sd_test, True)
    sd_reference = specification.sd_reference
    reference_XYZ = sd_to_XYZ(sd_reference)
    reference_Luv = XYZ_to_Luv(reference_XYZ, CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D65'])
    reference_uv = Luv_to_uv(reference_Luv)
    
    return reference_uv
matplotlib.use('Agg')
matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.serif'] = ['Times New Roman']
matplotlib.rcParams['mathtext.fontset'] = 'custom'
matplotlib.rcParams['mathtext.rm'] = 'Times New Roman'
matplotlib.rcParams['mathtext.it'] = 'Times New Roman:italic'
matplotlib.rcParams['mathtext.bf'] = 'Times New Roman:bold'

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("led_analysis.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", module="colour")

CONSTANT_REPORT_SIZE_FULL = (11.69, 8.27) 
CONSTANT_REPORT_ROW_HEIGHT_RATIOS_FULL = (1, 1, 1, 1, 1) 


def wavelength_to_rgb(wavelength, gamma=0.8):
    """
    Convert a wavelength in nanometers (400-700 nm) to an approximate RGB value.
    Input: wavelength (nm) between 400 and 700.
    Output: (R, G, B) tuple with values between 0 and 1.
    """
    if wavelength < 400:
        wavelength = 400
    if wavelength > 700:
        wavelength = 700

    if 400 <= wavelength < 440:
        attenuation = 0.3 + 0.7 * (wavelength - 400) / (440 - 400)
        R = ((440 - wavelength) / (440 - 400)) * attenuation
        G = 0.0
        B = 1.0 * attenuation
    elif 440 <= wavelength < 490:
        R = 0.0
        G = (wavelength - 440) / (490 - 440)
        B = 1.0
    elif 490 <= wavelength < 510:
        R = 0.0
        G = 1.0
        B = (510 - wavelength) / (510 - 490)
    elif 510 <= wavelength < 580:
        R = (wavelength - 510) / (580 - 510)
        G = 1.0
        B = 0.0
    elif 580 <= wavelength < 645:
        R = 1.0
        G = (645 - wavelength) / (645 - 580)
        B = 0.0
    elif 645 <= wavelength <= 700:
        attenuation = 0.3 + 0.7 * (700 - wavelength) / (700 - 645)
        R = 1.0 * attenuation
        G = 0.0
        B = 0.0
    else:
        R, G, B = 0.0, 0.0, 0.0

    R = pow(R, gamma)
    G = pow(G, gamma)
    B = pow(B, gamma)
    return (R, G, B)


def make_pastel(color, pastel_factor=0.7):
    """
    Convert a given RGB color to a pastel tone by mixing it with white.
    pastel_factor controls the degree of pastel effect (0 means original color, closer to 1 makes it lighter).
    """
    return tuple((1 - pastel_factor) * c + pastel_factor for c in color)


def macadam_ellipse(center_uv, n_steps, a=0.0015, b=0.0007, angle=0):
    center_uv = np.array(center_uv).flatten()
    theta = np.linspace(0, 2 * np.pi, 100)
    ellipse_x = n_steps * a * np.cos(theta)
    ellipse_y = n_steps * b * np.sin(theta)

    R = np.array([[np.cos(angle), -np.sin(angle)],
                  [np.sin(angle),  np.cos(angle)]])
    ellipse = np.dot(R, np.vstack([ellipse_x, ellipse_y]))
    return center_uv[0] + ellipse[0], center_uv[1] + ellipse[1]

@dataclass
class LEDParameters:
    sample_name: str
    manufacturer: str
    model: str
    date: str
    cct: float
    cri: float
    rf: float
    rg: float
    luminous_efficacy: float
    dominant_wavelength: float
    color_purity: float
    peak_wavelength: float
    fwhm: float
    xy_coordinates: Tuple[float, float]
    uv_coordinates: Tuple[float, float]  
    duv_measured: float  
    tm30_status: str = "Not Generated"
    luminance: float = 0.0
    reference_uv: Optional[Tuple[float, float]] = None  

class LEDAnalyzer:
    def __init__(self, input_file: str, output_folder: str):
        """Initialize LED Analyzer with improved configuration"""
        self.input_file = Path(input_file)
        if not self.input_file.exists():
            logger.error(f"Input file not found: {input_file}")
            raise FileNotFoundError(f"Input file not found: {input_file}")

        self.output_folder = Path(output_folder)
        self.setup_folders()

        self.results: List[LEDParameters] = []
        self.wavelengths: Optional[np.ndarray] = None
        self.samples: Optional[List[str]] = None
        self.data: Optional[pd.DataFrame] = None
        self.sample_metadata: Optional[dict] = None  
        self.samples_1_to_7 = [f'Sample{i}' for i in range(1, 8)]
        self.samples_8_to_14 = [f'Sample{i}' for i in range(8, 15)]
        
        self.config = {
            'plot_dpi': 300,
            'interactive': False,
            'figure_width': 20,
            'figure_height': 15,
            'layout_pad': 3.0,
            'save_format': 'jpg',
            'run_tm30_report': False,
        }

        self.white_point = (0.3127, 0.3290)

        self.setup_plotting_style()

        self.reference_spd = None
        logger.info("Proceeding without custom reference SPD. Using TM30-18 default references.")

    def setup_folders(self):
        """Set up output folders with proper structure"""
        folders = ['plots', 'reports', 'data']
        self.output_folder.mkdir(parents=True, exist_ok=True)

        for folder in folders:
            (self.output_folder / folder).mkdir(exist_ok=True)

    def setup_plotting_style(self):
        """Configure plotting style for better visualizations"""
        try:
            plt.style.use('default')
            plt.rcParams['figure.figsize'] = [10, 6]
            plt.rcParams['figure.dpi'] = 100
            plt.rcParams['axes.grid'] = True
            plt.rcParams['grid.alpha'] = 0.3
            plt.rcParams['font.size'] = 10
            plt.rcParams['axes.titlesize'] = 12
            plt.rcParams['axes.labelsize'] = 11
            plt.rcParams['font.family'] = 'serif'
            plt.rcParams['font.serif'] = ['Times New Roman']
            plt.rcParams['mathtext.fontset'] = 'custom'
            plt.rcParams['mathtext.rm'] = 'Times New Roman'
            plt.rcParams['mathtext.it'] = 'Times New Roman:italic'
            plt.rcParams['mathtext.bf'] = 'Times New Roman:bold'
            plt.rcParams['xtick.labelsize'] = 10
            plt.rcParams['ytick.labelsize'] = 10
        except Exception as e:
            logger.warning(f"Failed to set plot style. Using minimal defaults. Error: {e}")

    def apply_font_settings(self):
        """Apply Times New Roman font settings to current plot"""
        plt.rcParams['font.family'] = 'serif'
        plt.rcParams['font.serif'] = ['Times New Roman']
        current_fig = plt.gcf()
        for ax in current_fig.get_axes():
            for text in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
                        ax.get_xticklabels() + 
                        ax.get_yticklabels()):
                text.set_fontname('Times New Roman')

    def load_data(self):
        """Load data and extract metadata."""
        try:
            self.data = pd.read_excel(self.input_file)
            self.wavelengths = self.data['Wavelength'].values
    
            sample_columns = [col for col in self.data.columns if col.startswith('Sample')]
            self.samples = []
            self.sample_metadata = {} 
    
            for sample in sample_columns:
                index = ''.join(filter(str.isdigit, sample))
                manufacturer_col = f"Manufacturer{index}"
                model_col = f"Model{index}"
                date_col = f"Date{index}"
    
                missing_columns = [
                    col for col in [manufacturer_col, model_col, date_col]
                    if col not in self.data.columns
                ]
                if missing_columns:
                    logger.warning(f"Missing metadata columns for {sample}: {missing_columns}. Defaulting to 'N/A'.")
                    self.sample_metadata[sample] = {
                        'manufacturer': 'N/A',
                        'model': 'N/A',
                        'date': 'N/A'
                    }
                else:
                    date_value = self.data[date_col].iloc[0]
                    if pd.notna(date_value) and isinstance(date_value, pd.Timestamp):
                        date_formatted = date_value.strftime('%Y/%m/%d')
                    elif pd.notna(date_value):
                        date_formatted = str(date_value)
                    else:
                        date_formatted = 'N/A'
    
                    self.sample_metadata[sample] = {
                        'manufacturer': self.data[manufacturer_col].iloc[0] if pd.notna(self.data[manufacturer_col].iloc[0]) else 'N/A',
                        'model': self.data[model_col].iloc[0] if pd.notna(self.data[model_col].iloc[0]) else 'N/A',
                        'date': date_formatted
                    }
                self.samples.append(sample)
    
            logger.info(f"Successfully loaded data with {len(self.samples)} samples")
            logger.info(f"Available columns: {self.data.columns.tolist()}")
    
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            raise
    def analyze_samples(self):
        try:
            start_time = time.time()
            self.load_data()
    
            total_samples = len(self.samples)
            for i, sample in enumerate(self.samples, 1):
                counts = self.data[sample].values
                result = self.process_sample(sample, counts)
                if result:
                    self.results.append(result)
                logger.info(f"Processed {i}/{total_samples} samples")
    
            self.create_advanced_visualizations()
    
            group_1 = ['Sample2', 'Sample5', 'Sample8', 'Sample10', 'Sample12', 'Sample13', 'Sample14']
            group_2 = [sample for sample in self.samples if sample not in group_1 and sample != 'Sample15']  # Exclude Sample15
    
            self.plot_chromaticity_coordinates(
                group_1, 
                "Chromaticity Diagram - Group 1 (Samples 2, 5, 8, 10, 12, 13, 14)", 
                "chromaticity_group_1.jpg",
                xlim=(0.14, 0.26),
                ylim=(0.44, 0.56)
            )
            self.plot_chromaticity_coordinates(
                group_2, 
                "Chromaticity Diagram - Group 2 (Other Samples, excluding Sample15)", 
                "chromaticity_group_2.jpg",
                xlim=(0.14, 0.26),
                ylim=(0.40, 0.52)
            )

            self.plot_overlain_spds()
    
            self.save_correlation_matrix()
    
            self.save_results()
    
            elapsed_time = time.time() - start_time
            logger.info(f"Analysis completed in {elapsed_time:.2f} seconds")
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
    def verify_reference_data(self):
            """Verify reference sun data exists and is valid"""
            try:
                return False
            except Exception as e:
                logger.error(f"Error verifying reference data: {e}")
                return False
    def create_interactive_plots(self, sample_name: str, spd: SpectralDistribution):
        try:
            logger.info(f"Skipping interactive SPD plot for {sample_name}")

            fig_tm30, _ = plot_single_sd_colour_rendition_report(
                spd,
                source=self.sample_metadata[sample_name]['manufacturer'],
                date=self.sample_metadata[sample_name]['date'],
                manufacturer=self.sample_metadata[sample_name]['manufacturer'],
                model=self.sample_metadata[sample_name]['model'],
                notes="",
                figure_size=(24, 18),
                mode="Full"
            )
            tm30_report_path = self.output_folder / "reports" / f"tm30_18_{sample_name}.jpg"
            fig_tm30.savefig(tm30_report_path, dpi=self.config['plot_dpi'], bbox_inches="tight")
            plt.close(fig_tm30)
            logger.info(f"TM-30-18 report saved as JPEG at {tm30_report_path}")

            self.plot_additional_tm30_components(sample_name, spd)

        except AttributeError as ae:
            logger.error(f"AttributeError: {ae}")
            message_box(f"AttributeError while creating interactive plots for {sample_name}.\nError: {ae}")
        except Exception as e:
            logger.error(f"Error creating interactive plots for {sample_name}: {e}")
            message_box(f"Error creating interactive plots for {sample_name}.\nError: {e}")
    
    def plot_additional_tm30_components(self, sample_name: str, spd: SpectralDistribution):
        """
        Plot additional TM-30-18 components for a given sample.
        This includes colour fidelity indexes, colour vector graphic, local chroma and hue shifts, and ANSI/IES TM-30-18 spectra.
        """
        try:
            tm30_report = colour_fidelity_index_ANSIIESTM3018(spd, additional_data=True)
    
            plt.figure(figsize=(12, 8))
            plot_colour_fidelity_indexes(tm30_report)
            fidelity_indexes_path = self.output_folder / "plots" / f"{sample_name}_Colour_Fidelity_Indexes.jpg"
            
            plt.savefig(fidelity_indexes_path, dpi=self.config['plot_dpi'], bbox_inches="tight")
            plt.close()
            logger.info(f"Colour Fidelity Indexes plot saved at {fidelity_indexes_path}")
    
            plt.figure(figsize=(12, 8))
            plot_colour_vector_graphic(tm30_report)
            colour_vector_path = self.output_folder / "plots" / f"{sample_name}_Colour_Vector_Graphic.jpg"
            plt.savefig(colour_vector_path, dpi=self.config['plot_dpi'], bbox_inches="tight")
            plt.close()
            logger.info(f"Colour Vector Graphic saved at {colour_vector_path}")
    
            plt.figure(figsize=(12, 8))
            plot_local_chroma_shifts(tm30_report)
            chroma_shifts_path = self.output_folder / "plots" / f"{sample_name}_Local_Chroma_Shifts.jpg"
            plt.savefig(chroma_shifts_path, dpi=self.config['plot_dpi'], bbox_inches="tight")
            plt.close()
            logger.info(f"Local Chroma Shifts plot saved at {chroma_shifts_path}")
    
            plt.figure(figsize=(12, 8))
            plot_local_colour_fidelities(tm30_report)
            colour_fidelities_path = self.output_folder / "plots" / f"{sample_name}_Local_Colour_Fidelities.jpg"
            plt.savefig(colour_fidelities_path, dpi=self.config['plot_dpi'], bbox_inches="tight")
            plt.close()
            logger.info(f"Local Colour Fidelities plot saved at {colour_fidelities_path}")
    
            plt.figure(figsize=(12, 8))
            plot_local_hue_shifts(tm30_report)
            hue_shifts_path = self.output_folder / "plots" / f"{sample_name}_Local_Hue_Shifts.jpg"
            plt.savefig(hue_shifts_path, dpi=self.config['plot_dpi'], bbox_inches="tight")
            plt.close()
            logger.info(f"Local Hue Shifts plot saved at {hue_shifts_path}")
    
            plt.figure(figsize=(12, 8))
            plot_spectra_ANSIIESTM3018(tm30_report)
            ansi_spectra_path = self.output_folder / "plots" / f"{sample_name}_ANSIIESTM3018_Spectra.jpg"
            plt.savefig(ansi_spectra_path, dpi=self.config['plot_dpi'], bbox_inches="tight")
            plt.close()
            logger.info(f"ANSI/IES TM-30-18 Spectra plot saved at {ansi_spectra_path}")
    
        except Exception as e:
            logger.error(f"Error plotting additional TM-30-18 components for {sample_name}: {e}")
            message_box(f"Error plotting additional TM-30-18 components for {sample_name}.\nError: {e}")
    def calculate_color_purity(self, xy_coords: Tuple[float, float]) -> float:
        try:
            return colorimetric_purity(xy_coords, self.white_point)
        except Exception as e:
            logger.error(f"Error calculating color purity: {e}")
            return 0

    
    def calculate_fwhm(self, intensities: np.ndarray) -> float:
        """
        Calculate Full Width at Half Maximum (FWHM) using scipy.
    
        Parameters
        ----------
        intensities : np.ndarray
            The intensity data.
    
        Returns
        -------
        float
            The FWHM value.
        """
        try:
            half_max = np.max(intensities) / 2.0
            indices = np.where(intensities >= half_max)[0]
            fwhm_value = self.wavelengths[indices[-1]] - self.wavelengths[indices[0]]
            return fwhm_value
        except Exception as e:
            logger.error(f"Error calculating FWHM: {e}")
            return 0.0
    def calculate_dominant_wavelength(self, xy_coords: Tuple[float, float]) -> float:
        try:
            dm_wl = dominant_wavelength(xy_coords, self.white_point)
            return dm_wl[0] if isinstance(dm_wl, tuple) and dm_wl[0] is not None else 0
        except Exception as e:
            logger.error(f"Error calculating dominant wavelength: {e}")
            return 0
    def calculate_peak_wavelength(self, intensities: np.ndarray) -> float:
        """
        Calculate the peak wavelength using the method from the Colour Science repository.
    
        Parameters
        ----------
        intensities : np.ndarray
            The intensity data.
    
        Returns
        -------
        float
            The peak wavelength.
        """
        try:
            peak_idx = np.argmax(intensities)
            peak_wavelength = self.wavelengths[peak_idx]
            return peak_wavelength
        except Exception as e:
            logger.error(f"Error calculating peak wavelength: {e}")
            return 0.0
    def calculate_luminous_efficacy(self, spd: SpectralDistribution) -> float:
        try:
            lef = optional(None, SDS_LEFS_PHOTOPIC["CIE 1924 Photopic Standard Observer"])
    
            lef = reshape_sd(
                lef,
                spd.shape,
                copy=False,
                extrapolator_kwargs={"method": "Constant", "left": 0, "right": 0},
            )
    
            efficiency = np.trapz(lef.values * spd.values, spd.wavelengths) / np.trapz(
                spd.values, spd.wavelengths
            )
    
            return as_float_scalar(CONSTANT_K_M * efficiency)
        except Exception as e:
            logger.error(f"Error calculating luminous efficacy: {e}")
            return 0
    def process_sample(self, sample_name: str, counts: np.ndarray) -> Optional[LEDParameters]:
        try:
            spd_data = dict(zip(self.wavelengths, counts))
            spd = SpectralDistribution(spd_data)
            spd.normalise()
    
            if len(spd) == 0 or not np.any(spd.values):
                raise ValueError(f"Spectral distribution data for {sample_name} is empty or invalid.")
    
            XYZ = sd_to_XYZ(spd)
            xy = XYZ_to_xy(XYZ)
            cct_measured = XYZ_to_CCT_Ohno2013(XYZ)[0]
    
            metadata = self.sample_metadata.get(sample_name, {'manufacturer': 'N/A', 'model': 'N/A', 'date': 'N/A'})
            manufacturer = metadata['manufacturer']
            model = metadata['model']
            date = metadata['date']
    
            tm30_status = "Not Generated"
            if self.config.get('run_tm30_report', True):
                tm30_status = self.generate_tm30_18_report(spd, sample_name, manufacturer, model, date)
    
            cri_tm30 = colour_fidelity_index_ANSIIESTM3018(spd)
            logger.info(f"CRI(TM30-18) for {sample_name}: {cri_tm30}")
    
            if self.config.get('interactive', False):
                self.create_interactive_plots(sample_name, spd)
    
            peak_wavelength = self.calculate_peak_wavelength(counts)
            color_purity = self.calculate_color_purity(xy)
            dominant_wavelength_val = self.calculate_dominant_wavelength(xy)
            fwhm = self.calculate_fwhm(counts)
            cri = colour_rendering_index(spd)
            rf = colour_fidelity_index(spd)
            rg = colour_quality_scale(spd)
            luminous_efficacy = self.calculate_luminous_efficacy(spd)
    
            X, Y, Z = XYZ
            denom = X + 15 * Y + 3 * Z
            if denom == 0:
                uv_measured = (0.0, 0.0)
            else:
                u = 4 * X / denom
                v = 9 * Y / denom
                uv_measured = (u, v)
    
            duv_measured = self.calculate_duv(uv_measured, spd)
            luminance = Y
    
            reference_uv = get_reference_illuminant_for_cct(spd)
    
            return LEDParameters(
                sample_name=sample_name,
                manufacturer=manufacturer,
                model=model,
                date=date,
                cct=cct_measured,
                cri=cri,
                rf=rf,
                rg=rg,
                luminous_efficacy=luminous_efficacy,
                dominant_wavelength=dominant_wavelength_val,
                color_purity=color_purity,
                peak_wavelength=peak_wavelength,
                fwhm=fwhm,
                xy_coordinates=xy,
                uv_coordinates=uv_measured,
                duv_measured=duv_measured,
                tm30_status=tm30_status,
                luminance=luminance,
                reference_uv=reference_uv
            )
    
        except Exception as e:
            logger.error(f"Error processing sample {sample_name}: {e}")
            message_box(f"Error processing sample {sample_name}.\nError: {e}")
            return None
    def create_advanced_visualizations(self):
        """Create advanced visualizations for deeper analysis"""
        if not self.results:
            logger.warning("No results to visualize.")
            return

        df = pd.DataFrame([vars(result) for result in self.results])
        try:
            stats_summary = df.describe()
            stats_summary_path = self.output_folder / "reports" / "statistical_summary.xlsx"
            stats_summary.to_excel(stats_summary_path)  
        except Exception as e:
            logger.error(f"Error saving statistical summary: {e}")
    def calculate_duv(self, uv_measured: Tuple[float, float], spd: SpectralDistribution) -> float:
        """
        Calculate D_uv based on the TM-30-18 method.
        
        Parameters
        ----------
        uv_measured : Tuple[float, float]
            The measured (u', v') coordinates.
        spd : SpectralDistribution
            The spectral power distribution of the sample.
    
        Returns
        -------
        float
            The calculated D_uv value.
        """
        try:
    
            reference_uv = get_reference_illuminant_for_cct(spd)
    
            if reference_uv is None:
                logger.error("Reference illuminant (u', v') coordinates could not be determined.")
                return 0.0

            duv = np.sqrt((uv_measured[0] - reference_uv[0])**2 + (uv_measured[1] - reference_uv[1])**2)
    
            return duv
        except Exception as e:
            logger.error(f"Error calculating D_uv: {e}")
            return 0.0
    def save_correlation_matrix(self):
        if not self.results:
            logger.warning("No results to save correlation matrix")
            return
    
        df = pd.DataFrame([vars(result) for result in self.results])
    
        df = df[df['sample_name'] != 'Sample15']
    
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        correlation_matrix = df[numeric_cols].corr()

        updated_labels = {
            'cct': 'CCT',
            'cri': 'CRI',
            'rf': 'Rf',
            'rg': 'Rg',
            'luminous_efficacy': 'Luminous Efficacy',
            'dominant_wavelength': 'Dominant Wavelength',
            'color_purity': 'Color Purity',
            'peak_wavelength': 'Peak Wavelength',
            'fwhm': 'FWHM',
            'duv_measured': 'Duv',
            'luminance': 'Luminance',
        }
    
        correlation_matrix.rename(columns=updated_labels, index=updated_labels, inplace=True)
    
        excel_path = self.output_folder / "data" / "correlation_matrix.xlsx"
        with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
            correlation_matrix.to_excel(writer, sheet_name='Correlation Matrix')
            workbook = writer.book
            worksheet = writer.sheets['Correlation Matrix']
            header_format = workbook.add_format({
                'bold': True, 'text_wrap': True, 'valign': 'top',
                'bg_color': '#D7E4BC', 'border': 1
            })
            for col_num, value in enumerate(correlation_matrix.columns):
                worksheet.write(0, col_num + 1, value, header_format)
            for row_num, value in enumerate(correlation_matrix.index):
                worksheet.write(row_num + 1, 0, value, header_format)
            worksheet.set_column(0, 0, 20)
            worksheet.set_column(1, len(correlation_matrix.columns), 15)
    
        logger.info(f"Correlation matrix saved to {excel_path}")
    
        plt.figure(figsize=(16, 12))
        sns.heatmap(
            correlation_matrix, cmap='coolwarm', annot=True, fmt=".2f",
            annot_kws={"size": 10}, linewidths=0.5, cbar_kws={"shrink": 0.8}
        )
        plt.title("Correlation Matrix", fontsize=20, fontname='Times New Roman', pad=20)
        plt.xticks(fontsize=12, fontname='Times New Roman', rotation=45, ha='right')
        plt.yticks(fontsize=12, fontname='Times New Roman', rotation=0)
        heatmap_path = self.output_folder / "plots" / "correlation_matrix_high_res.png"
        plt.savefig(heatmap_path, dpi=300, bbox_inches="tight") 
        plt.close()
        logger.info(f"High-resolution correlation matrix saved at {heatmap_path}")
    def plot_chromaticity_coordinates(self, samples, title, filename, xlim, ylim):
        """Plot chromaticity with scientifically accurate MacAdam ellipses, properly transformed from xy to u'v'."""

        def uv_to_xy(uv):
            """Convert CIE 1976 u', v' to xy coordinates using standard formula."""
            u, v = uv
            denominator = 6*u - 16*v + 12
            if abs(denominator) < 1e-10:
                logger.error(f"Division by near-zero in u'v' to xy transformation: u'={u:.6f}, v'={v:.6f}")
                return None
                    
            x = (9*u) / denominator
            y = (4*v) / denominator
            return (x, y)

        def xy_to_uv(xy):
            """Convert xy coordinates to CIE 1976 u', v' using standard formula."""
            x, y = xy
            denominator = -2*x + 12*y + 3
            if abs(denominator) < 1e-10:
                return None
                
            u_prime = 4*x / denominator
            v_prime = 9*y / denominator
            return (u_prime, v_prime)

        def draw_transformed_macadam_ellipse(ref_uv, step_size, color, label=None):
            try:
            
                ref_xy = uv_to_xy(ref_uv)
                if ref_xy is None:
                    logger.warning(f"Cannot transform reference point u'v'=({ref_uv[0]:.4f},{ref_uv[1]:.4f}) to xy")
                    return False
                
                min_distance = float('inf')
                closest_idx = 0
                
                for i, ellipse_data in enumerate(DATA_MACADAM_1942_ELLIPSES):
                    center_x, center_y = ellipse_data[0], ellipse_data[1]
                    distance = np.sqrt((center_x - ref_xy[0])**2 + (center_y - ref_xy[1])**2)
                    if distance < min_distance:
                        min_distance = distance
                        closest_idx = i
                
                ellipse_data = DATA_MACADAM_1942_ELLIPSES[closest_idx]
                center_x, center_y = ellipse_data[0], ellipse_data[1]
                
                xy_a = ellipse_data[5] / 1000 * step_size 
                xy_b = ellipse_data[6] / 1000 * step_size
                xy_theta = np.radians(ellipse_data[7])
                
               
                t = np.linspace(0, 2*np.pi, 200)
                ellipse_x = xy_a * np.cos(t)
                ellipse_y = xy_b * np.sin(t)
                
                R = np.array([
                    [np.cos(xy_theta), -np.sin(xy_theta)],
                    [np.sin(xy_theta), np.cos(xy_theta)]
                ])
                rotated = np.dot(R, np.vstack([ellipse_x, ellipse_y]))
                
                x_ellipse = ref_xy[0] + rotated[0]
                y_ellipse = ref_xy[1] + rotated[1]
                
                uv_points = []
                for x, y in zip(x_ellipse, y_ellipse):
                    if 0 <= x <= 1 and 0 <= y <= 1 and x + y <= 1:
                        uv_point = xy_to_uv((x, y))
                        if uv_point and 0 <= uv_point[0] <= 0.7 and 0 <= uv_point[1] <= 0.7:
                            uv_points.append(uv_point)
                
                if len(uv_points) > 20:  
                    u_points = [p[0] for p in uv_points]
                    v_points = [p[1] for p in uv_points]
                    
                    plt.plot(
                        u_points, v_points,
                        "-", color=color, alpha=0.8, linewidth=2,
                        label=label, zorder=8
                    )
                    return True
                else:
                    logger.warning(f"Too few valid points ({len(uv_points)}) for a proper ellipse")
                    return False
                    
            except Exception as e:
                logger.error(f"Error drawing MacAdam ellipse: {str(e)}")
                logger.error(traceback.format_exc())
                return False
        
        def draw_direct_macadam_ellipse(ref_uv, step_size, color, label=None):
            u_prime = ref_uv[0]
            

            if u_prime < 0.18: 
                a_scale = 0.0020 * step_size
                b_scale = 0.0010 * step_size
                theta = -30  
            elif u_prime < 0.22: 
                a_scale = 0.0025 * step_size
                b_scale = 0.0012 * step_size
                theta = -15 
            elif u_prime < 0.28:  
                a_scale = 0.0022 * step_size
                b_scale = 0.0011 * step_size
                theta = -5  
            else:  
                a_scale = 0.0018 * step_size
                b_scale = 0.0010 * step_size
                theta = 0 
                
            t = np.linspace(0, 2*np.pi, 100)
            ellipse_x = a_scale * np.cos(t)
            ellipse_y = b_scale * np.sin(t)
            
            theta_rad = np.radians(theta)
            R = np.array([
                [np.cos(theta_rad), -np.sin(theta_rad)],
                [np.sin(theta_rad), np.cos(theta_rad)]
            ])
            rotated = np.dot(R, np.vstack([ellipse_x, ellipse_y]))
            
            u_points = ref_uv[0] + rotated[0]
            v_points = ref_uv[1] + rotated[1]
            
            plt.plot(
                u_points, v_points,
                "-", color=color, alpha=0.8, linewidth=2,
                label=label, zorder=8
            )
            
            logger.info(f"Drew direct {step_size}-step ellipse at u'v'=({ref_uv[0]:.4f},{ref_uv[1]:.4f}), " + 
                    f"a={a_scale:.6f}, b={b_scale:.6f}, θ={theta}°")
            return True
        
        try:
            fig = plt.figure(figsize=(24, 12), dpi=150)
            logger.info(f"Generating chromaticity diagram for {title}")

            plt.rcParams['font.family'] = 'serif'
            plt.rcParams['font.serif'] = ['Times New Roman']
            plt.rcParams['font.size'] = 16
            plt.rcParams['axes.titlesize'] = 24
            plt.rcParams['axes.labelsize'] = 18

            plot_chromaticity_diagram_CIE1976UCS(
                standalone=False,
                title="",
                bounding_box=(-0.1, 0.7, 0.0, 0.7)
            )

            ax = plt.gca()
            ax.set_title("")
            plt.suptitle("")

            for text_obj in ax.texts[:]:
                if any(phrase in text_obj.get_text() for phrase in ["Planckian", "CIE", "Chromaticity", "Diagram", "Observer"]):
                    text_obj.remove()

            plot_planckian_locus_in_chromaticity_diagram_CIE1976UCS(
                standalone=False,
                show=False,
                title="",
                planckian_locus_colours="black",
                planckian_locus_opacity=1,
                planckian_locus_labels=[2700, 3000, 4000, 5000, 6500, 12000],
                planckian_locus_iso_temperature_lines_D_uv=0.035,
                planckian_locus_iso_temperature_lines_opacity=0.6
            )


            for text_obj in ax.texts[:]:
                text = text_obj.get_text()
                if text != title and any(phrase in text for phrase in ["Planckian", "CIE", "Chromaticity", "Diagram", "Observer"]):
                    text_obj.remove()

            ax.set_title(title, fontsize=22, fontname='Times New Roman', fontweight='bold', pad=20)

            for text_obj in ax.texts[:]:
                text_content = text_obj.get_text()
                if any(str(temp) in text_content for temp in [2700, 3000, 4000, 5000, 6500, 12000]):
                    text_obj.set_fontsize(20)
                    text_obj.set_weight('bold')
                    text_obj.set_fontname('Times New Roman')

            filtered_results = [result for result in self.results if result.sample_name in samples]

            steps = [1, 3, 7, 9]
            step_colors = {1: "#FFB300", 3: "#0072B2", 7: "#009E73", 9: "#D55E00"}
            cmap = plt.get_cmap("viridis")
            sample_colors = [cmap(i / len(filtered_results)) for i in range(len(filtered_results))]

            grouped_references = {}
            for i, result in enumerate(filtered_results):
                measured_u, measured_v = result.uv_coordinates
                plt.plot(
                    measured_u, measured_v,
                    marker="*", markersize=12, markeredgewidth=1, markeredgecolor='black',
                    color=sample_colors[i], linestyle="", label=result.sample_name,
                    zorder=10
                )
                if result.reference_uv is not None:
                    ref_u, ref_v = result.reference_uv
                    key = (round(ref_u, 2), round(ref_v, 2))
                    if key not in grouped_references:
                        grouped_references[key] = {
                            'uv_sum': np.array(result.reference_uv),
                            'count': 1,
                            'samples': [result.sample_name],
                            'color': sample_colors[i],
                            'original_uvs': [result.reference_uv]
                        }
                    else:
                        grouped_references[key]['uv_sum'] += np.array(result.reference_uv)
                        grouped_references[key]['count'] += 1
                        grouped_references[key]['samples'].append(result.sample_name)
                        grouped_references[key]['original_uvs'].append(result.reference_uv)
            
            
            for key, group_data in grouped_references.items():
                group_data['avg_uv'] = group_data['uv_sum'] / group_data['count']
                ref_u, ref_v = group_data['avg_uv']
                
                plt.plot(
                    ref_u, ref_v,
                    marker="o", markersize=2, markeredgewidth=1,
                    markeredgecolor='black', color='white',
                    linestyle="", alpha=1.0, zorder=9
                )
                
                transformation_success = False
                for step in steps:
                    label = f"{step}-step MacAdam" if key == list(grouped_references.keys())[0] else None
                    success = draw_transformed_macadam_ellipse(
                        (ref_u, ref_v),
                        step,
                        step_colors[step],
                        label
                    )
                    if success:
                        transformation_success = True
                
                if not transformation_success:
                    logger.warning(f"No MacAdam ellipses were successfully drawn. Using approximate ellipses.")
                    for step in steps:
                        label = f"{step}-step MacAdam" if key == list(grouped_references.keys())[0] else None
                        draw_direct_macadam_ellipse(
                            (ref_u, ref_v),
                            step,
                            step_colors[step],
                            label
                        )

            for i, result in enumerate(filtered_results):
                if result.reference_uv is not None:
                    measured_u, measured_v = result.uv_coordinates
                    ref_u, ref_v = result.reference_uv
                    group_key = (round(ref_u, 2), round(ref_v, 2))
                    if group_key in grouped_references:
                        group_avg_u, group_avg_v = grouped_references[group_key]['avg_uv']
                        
                        plt.plot(
                            [measured_u, group_avg_u], [measured_v, group_avg_v],
                            color=sample_colors[i], linestyle="--", alpha=0.6, linewidth=1.5,
                            zorder=7
                        )


            plt.grid(True, alpha=0.3, linestyle='--')
            plt.subplots_adjust(right=0.8)


            handles, labels = plt.gca().get_legend_handles_labels()
            step_handles = [h for h, l in zip(handles, labels) if "step" in l]
            step_labels = [l for l in labels if "step" in l]
            sample_handles = [h for h, l in zip(handles, labels) if "step" not in l]
            sample_labels = [l for l in labels if "step" not in l]

            legend1 = plt.legend(
                step_handles, step_labels,
                loc="upper left", bbox_to_anchor=(1.02, 1),
                title="MacAdam Ellipses", title_fontsize=16,
                frameon=True, framealpha=0.95,
                fontsize=14,
                prop={'family': 'Times New Roman'}
            )
            legend1.get_title().set_fontfamily('Times New Roman')
            plt.gca().add_artist(legend1)

            if len(sample_handles) <= 15:
                legend2 = plt.legend(
                    sample_handles, sample_labels,
                    loc="upper left", bbox_to_anchor=(1.02, 0.7),
                    title="LED Samples", title_fontsize=16,
                    frameon=True, framealpha=0.95,
                    fontsize=14,
                    ncol=1,
                    prop={'family': 'Times New Roman'}
                )
                legend2.get_title().set_fontfamily('Times New Roman')
                plt.gca().add_artist(legend2)

            plt.xlim(xlim)
            plt.ylim(ylim)
            plt.xlabel("u'", fontsize=18, fontname='Times New Roman', fontweight='bold')
            plt.ylabel("v'", fontsize=18, fontname='Times New Roman', fontweight='bold')
            plt.xticks(fontsize=16, fontname='Times New Roman')
            plt.yticks(fontsize=16, fontname='Times New Roman')

            save_path = self.output_folder / "plots" / filename
            plt.savefig(
                save_path,
                format="jpg",
                dpi=400,
                bbox_inches="tight",
                pad_inches=0.3,
                bbox_extra_artists=[legend1, legend2] if 'legend2' in locals() else [legend1]
            )
            plt.close()
            logger.info(f"Chromaticity diagram with MacAdam ellipses saved to {save_path}")
        
        except Exception as e:
            logger.error(f"Error plotting chromaticity coordinates: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    def plot_overlain_spds(self):
        if self.wavelengths is None or self.data is None:
            logger.error("No spectral data loaded.")
            return
    
        filtered_samples = [sample for sample in self.samples if sample != 'Sample15']
    
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.set_xlabel("Wavelength [nm]", fontsize=12)
        ax.set_ylabel("SPD [-]", fontsize=12)
        ax.set_xlim(380, 750)
        ax.set_ylim(0, 0.01)
        ax.grid(True, linestyle='--', alpha=0.6)
    
        plt.rcParams['font.family'] = 'serif'
        plt.rcParams['font.serif'] = ['Times New Roman']
    
        new_wave = np.arange(380, 780 + 0.25, 0.25)
        cmap = plt.get_cmap('tab10')
        sample_line_colors = [cmap(i % cmap.N) for i in range(len(filtered_samples))]
    
        for i, sample in enumerate(filtered_samples):
            spd = self.data[sample].values
            spd_interp = np.interp(new_wave, self.wavelengths, spd)
            ax.plot(new_wave, spd_interp, color=sample_line_colors[i], linewidth=2, label=sample)
            for j in range(len(new_wave) - 1):
                wl_mid = (new_wave[j] + new_wave[j + 1]) / 2.0
                base_color = wavelength_to_rgb(wl_mid)
                pastel_color = make_pastel(base_color, pastel_factor=0.7)
                ax.fill_between(new_wave[j:j + 2], spd_interp[j:j + 2],
                                color=pastel_color, alpha=0.4)
    
        for ann_wl in [595, 560, 450]:
            idx = np.argmin(np.abs(new_wave - ann_wl))
            peak_intensity = np.max([
                np.interp(new_wave, self.wavelengths, self.data[sample].values)[idx]
                for sample in filtered_samples
            ])
            ax.annotate(f"{ann_wl} nm",
                        xy=(new_wave[idx], peak_intensity),
                        xytext=(new_wave[idx] - 20, peak_intensity + 0.1 * peak_intensity),
                        arrowprops=dict(arrowstyle="->", color="black"),
                        fontsize=10, color="black")
    
        ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize=10)
        output_path = self.output_folder / "plots" / "overlain_spds_all.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Overlain SPDs plot saved at {output_path}")
    def save_results(self):
        """Save results with improved formatting and multiple formats."""
        if not self.results:
            logger.warning("No results to save.")
            message_box("No results to save.")
            return
    
        results_df = pd.DataFrame([{
            'Sample_name': result.sample_name,
            'Manufacturer': result.manufacturer,
            'Model': result.model,
            'Date': result.date,
            'CCT': result.cct,
            'CRI': result.cri,
            'Rf': result.rf,
            'Rg': result.rg,
            'Luminous_efficacy': result.luminous_efficacy,
            'Dominant_wavelength': result.dominant_wavelength,
            'Color_purity': result.color_purity,
            'Peak_wavelength': result.peak_wavelength,
            'FWHM': result.fwhm,
            'xy_coordinates': result.xy_coordinates,
            'uv_coordinates': result.uv_coordinates,
            'Duv': result.duv_measured,
            'Luminance': result.luminance,
        } for result in self.results])
    
        try:
            excel_path = self.output_folder / "data" / "LED_Analysis_Results.xlsx"
            logger.info("Saving results to Excel...")
            with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
                results_df.to_excel(writer, sheet_name='Results', index=False)
                workbook = writer.book
                worksheet = writer.sheets['Results']
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'bg_color': '#D7E4BC',
                    'border': 1
                })
                for col_num, value in enumerate(results_df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                    worksheet.set_column(col_num, col_num, 20)
            logger.info(f"Results saved to Excel at {excel_path}")
        except PermissionError as e:
            logger.error(f"Permission denied while saving Excel file: {e}")
            message_box(f"Permission denied while saving Excel file.\nError: {e}")
        except Exception as e:
            logger.error(f"Error saving results to Excel: {e}")
            message_box(f"Error saving results to Excel.\nError: {e}")
    
        try:
            csv_path = self.output_folder / "data" / "LED_Analysis_Results.csv"
            logger.info("Saving results to CSV...")
            results_df.to_csv(csv_path, index=False)
            logger.info(f"Results saved to CSV at {csv_path}")
        except PermissionError as e:
            logger.error(f"Permission denied while saving CSV file: {e}")
            message_box(f"Permission denied while saving CSV file.\nError: {e}")
        except Exception as e:
            logger.error(f"Error saving results to CSV: {e}")
            message_box(f"Error saving results to CSV.\nError: {e}")

def generate_tm30_18_report(self, spd: SpectralDistribution, sample_name: str, manufacturer: str, model: str, date: str):
    """Generate TM-30-18 Colour Rendition Report with metadata."""
    try:
        save_path = self.output_folder / "reports" / f"tm30_18_{sample_name}.jpg"

        message_box(f'Generating "ANSI/IES TM-30-18 Colour Rendition Report" for {sample_name}.')

        plt.ioff() 
        plt.close('all')

        colour_style()

        report_mode = "Full" 
        message_box(f'Plotting TM-30-18 report in "{report_mode}" mode for {sample_name}.')

        plt.rcParams['font.family'] = 'serif'
        plt.rcParams['font.serif'] = ['Times New Roman']

        fig_tm30, _ = plot_single_sd_colour_rendition_report(
            spd,
            source=sample_name, 
            date=date,
            manufacturer=manufacturer, 
            model=model,
            notes="", 
            figure_size=(24, 18),
            mode=report_mode
        )

        self.apply_font_settings()

        fig_tm30.savefig(save_path, dpi=self.config['plot_dpi'], bbox_inches="tight")
        plt.close(fig_tm30)

        logger.info(f"TM-30-18 report successfully generated for {sample_name} at {save_path}")
        message_box(f'TM-30-18 report successfully generated for {sample_name}.\nSaved at: {save_path}')
        return "Success"

    except NameError as ne:
        logger.error(f"NameError in generate_tm30_18_report for {sample_name}: {ne}")
        message_box(f"NameError in generating TM-30-18 report for {sample_name}.\nError: {ne}")
        return "Failed"
    except Exception as e:
        logger.error(f"Error generating TM-30-18 report for {sample_name}: {e}")
        message_box(f"Failed to generate TM-30-18 report for {sample_name}.\nError: {e}")
        return "Failed"
def main():
    """Main function with improved error handling and path management"""
    try:
        input_file = Path(r"d:\Desktop\Broad-Scope Analysis\Final Data (using as input).xlsx")
        output_folder = Path(r"d:\Desktop\Broad-Scope Analysis")
        if not input_file.exists():
            logger.error(f"Input file not found: {input_file}")
            raise FileNotFoundError(f"Input file not found: {input_file}")
        analyzer = LEDAnalyzer(input_file, output_folder)
        analyzer.analyze_samples()
    except Exception as e:
        logger.error(f"Program execution failed: {e}")
        message_box(f"Program execution failed.\nError: {e}")
        raise

if __name__ == "__main__":
    main()
