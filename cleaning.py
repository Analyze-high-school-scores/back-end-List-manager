import pandas as pd
import requests
from io import StringIO
from datetime import datetime, timedelta
import os

class DataCleaner:
    def __init__(self):
        self.DATA_FILE_PATH = 'https://andyanh.id.vn/index.php/s/AQrkaif3HWgs9ke/download'
        self.TINH_FILE_PATH = 'https://andyanh.id.vn/index.php/s/zbHTAjksBekNB4M/download'
        self.RAW_DATA_API = 'https://andyanh.id.vn/index.php/s/p7XMy828G8NKiZp/download'

    def fetch_csv_from_api(self, api_url):
        """
        Tải dữ liệu từ API
        """
        try:
            print(f"Đang tải dữ liệu từ API {api_url}...")
            response = requests.get(api_url, timeout=30)
            response.raise_for_status()
            return pd.read_csv(StringIO(response.text))
        except requests.exceptions.RequestException as e:
            raise Exception(f"Lỗi khi tải dữ liệu từ {api_url}: {str(e)}")
        except pd.errors.EmptyDataError:
            raise Exception(f"Dữ liệu từ {api_url} trống")
        except Exception as e:
            raise Exception(f"Lỗi không xác định khi tải dữ liệu: {str(e)}")

    def load_data(self, use_raw_data=False):
        """
        Load dữ liệu từ nguồn được chọn
        Args:
            use_raw_data (bool): True để dùng Raw Data, False để dùng Update Data
        """
        try:
            data_file_path = self.RAW_DATA_API if use_raw_data else self.DATA_FILE_PATH
            print(f"Loading data from: {data_file_path}")
            data_df = self.fetch_csv_from_api(data_file_path)
            print("Loading tinh data...")
            tinh_df = self.fetch_csv_from_api(self.TINH_FILE_PATH)
            return data_df, tinh_df
        except Exception as e:
            raise Exception(f"Lỗi khi tải dữ liệu: {str(e)}")

    def clean_data(self, data_df, tinh_df):
        """
        Làm sạch dữ liệu
        """
        try:
            # Merge the two datasets on 'MaTinh'
            merged_df = pd.merge(data_df, tinh_df, on="MaTinh", how="left")

            # Fill missing values in score columns with -1
            score_columns = [
                "Toan", "Van", "Ly", "Sinh", "Ngoai ngu",
                "Hoa", "Lich su", "Dia ly", "GDCD",
            ]
            merged_df[score_columns] = merged_df[score_columns].fillna(-1)

            # Filter for rows where 'Year' is either 2018 or 2019
            merged_df = merged_df[merged_df["Year"].isin([2018, 2019])]

            # Drop rows where essential columns are missing
            cleaned_df = merged_df.dropna(subset=["SBD", "Year", "MaTinh"])

            return cleaned_df
        except Exception as e:
            raise Exception(f"Lỗi khi làm sạch dữ liệu: {str(e)}")

# Tạo instance để sử dụng
cleaner = DataCleaner()

if __name__ == "__main__":
    try:
        # Load the data
        data_df, tinh_df = cleaner.load_data(use_raw_data=False)
        # Clean the data
        cleaned_df = cleaner.clean_data(data_df, tinh_df)
        print("Đã làm sạch dữ liệu thành công!")
    except Exception as e:
        print(f"Lỗi: {str(e)}")