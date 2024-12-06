from flask import Flask, request, jsonify, send_file
import pandas as pd
from datetime import datetime, timedelta
import os
from flask_cors import CORS
import requests
from io import StringIO
import numpy as np
from sklearn.preprocessing import StandardScaler
import seaborn as sns
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from cleaning import cleaner
import tempfile
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://list-manager-omega.vercel.app"
]

CORS(app, resources={
    r"/students/*": {"origins": ALLOWED_ORIGINS, "methods": ["GET", "POST", "DELETE", "PUT", "OPTIONS"]},
    r"/save": {"origins": ALLOWED_ORIGINS, "methods": ["POST", "OPTIONS"]},
    r"/history*": {"origins": ALLOWED_ORIGINS, "methods": ["GET", "POST", "DELETE", "PUT", "OPTIONS"]},
    r"/chart/*": {"origins": ALLOWED_ORIGINS, "methods": ["GET", "OPTIONS"]},
    r"/clean/*": {"origins": ALLOWED_ORIGINS, "methods": ["POST", "OPTIONS"]},
    r"/tinh-data": {"origins": ALLOWED_ORIGINS, "methods": ["GET"]},
    r"/*": {
        "origins": ALLOWED_ORIGINS,
        "allow_credentials": True,
        "expose_headers": ["Content-Type", "X-CSRFToken"],
        "supports_credentials": True
    }
})

RAW_DATA_API = 'https://andyanh.id.vn/index.php/s/p7XMy828G8NKiZp/download'
CLEANED_DATA_API = 'https://andyanh.id.vn/index.php/s/psPTAMbDrzzMnWk/download'
UPDATED_FILE_PATH = 'https://andyanh.id.vn/index.php/s/AQrkaif3HWgs9ke/download'
TINH_FILE_PATH = 'https://andyanh.id.vn/index.php/s/zbHTAjksBekNB4M/download'

df = None
cleaned_df = None
data_loaded = False

operation_history = []

def init_history():
    global operation_history
    history_file = 'operation_history.csv'
    if os.path.exists(history_file):
        try:
            history_df = pd.read_csv(history_file)
            # Chuyển đổi dữ liệu từ CSV thành list of dictionaries
            operation_history = []
            for _, row in history_df.iterrows():
                record = {
                    'operation': row['operation'],
                    'time': row['time']
                }
                
                # Xử lý trường sbd nếu có
                if not pd.isna(row['sbd']):
                    record['sbd'] = int(row['sbd'])
                    
                # Xử lý trường data nếu có
                if not pd.isna(row['data']):
                    try:
                        # Nếu data là string representation của dict
                        if row['data'].startswith('{'):
                            record['data'] = eval(row['data'])
                        else:
                            record['data'] = row['data']
                    except:
                        record['data'] = row['data']
                        
                operation_history.append(record)
                
            print("Đã tải lịch sử từ file:", operation_history)
        except Exception as e:
            print(f"Lỗi khi đọc file lịch sử: {str(e)}")
            operation_history = []
    else:
        print("Chưa có file lịch sử, tạo mới operation_history")
        operation_history = []

def fetch_csv_from_api(api_url, cache_prefix='raw'):
    """
    Tải dữ liệu từ API và lưu cache
    """
    cache_file = f'{cache_prefix}_data_cache.csv'
    cache_timeout = timedelta(hours=24)
    
    if os.path.exists(cache_file):
        modified_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
        if datetime.now() - modified_time < cache_timeout:
            print(f"Đang tải dữ liệu từ cache {cache_file}...")
            return pd.read_csv(cache_file)
    
    print(f"Đang tải dữ liệu từ API {api_url}...")
    response = requests.get(api_url)
    if response.status_code == 200:
        df = pd.read_csv(StringIO(response.text))
        df.to_csv(cache_file, index=False)
        return df
    else:
        raise Exception(f"Không thể tải dữ liệu: {response.status_code}")

def fetch_tinh_data():
    """
    Tải và cache dữ liệu tỉnh
    """
    cache_file = 'tinh_cache.csv'
    cache_timeout = timedelta(hours=24)
    
    try:
        # Kiểm tra cache
        if os.path.exists(cache_file):
            modified_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if datetime.now() - modified_time < cache_timeout:
                print(f"Đang tải dữ liệu tỉnh từ cache...")
                df = pd.read_csv(cache_file)
                print(f"Dữ liệu tỉnh từ cache: {df.shape[0]} dòng")
                if df.shape[0] > 100:  # Nếu số dòng quá lớn, có thể là file sai
                    print("Số lượng dòng bất thường, xóa cache và tải lại")
                    os.remove(cache_file)
                else:
                    return df
        
        # Nếu không có cache hoặc cache hết hạn, tải mới
        print(f"Đang tải dữ liệu tỉnh từ API: {TINH_FILE_PATH}")
        response = requests.get(TINH_FILE_PATH)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            # In ra vài dòng đầu để kiểm tra format
            print("Mẫu dữ liệu:")
            print(content.split('\n')[:5])
            
            df = pd.read_csv(StringIO(content))
            
            # Kiểm tra số lượng dòng
            if df.shape[0] > 100:  # Nếu số dòng quá lớn, có thể là file sai
                raise Exception("Dữ liệu tỉnh không đúng định dạng")
            
            print(f"Đã đọc được DataFrame với {df.shape[0]} dòng")
            print("Các cột:", df.columns.tolist())
            
            # Lưu cache
            df.to_csv(cache_file, index=False)
            print(f"Đã lưu cache vào {cache_file}")
            
            return df
        else:
            raise Exception(f"Không thể tải dữ liệu tỉnh: {response.status_code}")
            
    except Exception as e:
        print(f"Lỗi trong fetch_tinh_data: {str(e)}")
        raise e

# Sửa lại hàm init_app để load cả 2 dataset
def init_app():
    global df, cleaned_df, data_loaded
    if not data_loaded:
        try:
            df = fetch_csv_from_api(RAW_DATA_API, 'raw')
            cleaned_df = fetch_csv_from_api(CLEANED_DATA_API, 'cleaned')
            init_history()
            data_loaded = True
            print("Đã tải dữ liệu thành công")
        except Exception as e:
            print(f"Lỗi khi tải dữ liệu: {str(e)}")
            df = pd.DataFrame()
            cleaned_df = pd.DataFrame()
            data_loaded = True

# Gọi init_app() khi khởi động ứng dụng
init_app()

@app.before_request
def load_data():
    global df, data_loaded
    if not data_loaded:
        init_app()

@app.route('/students', methods=['POST', 'GET', 'OPTIONS'])
def create_student():
    if request.method == 'OPTIONS':
        return '', 204
    global df, operation_history
    data = request.get_json()
    
    sbd = data.get('SBD')
    year = data.get('Year')
    
    # Chuyển đổi tên trường để phù hợp với frontend
    field_mapping = {
        'Toán': 'Toan',
        'Văn': 'Van',
        'Lý': 'Ly',
        'Hóa': 'Hoa',
        'Sinh': 'Sinh',
        'Ngoại ngữ': 'Ngoai ngu',
        'Lịch sử': 'Lich su',
        'Địa lý': 'Dia ly',
        'GDCD': 'GDCD',
        'MaTinh': 'MaTinh'
    }
    
    # Chuyển đổi dữ liệu từ frontend sang format ca DataFrame
    new_student_data = {
        'SBD': sbd,
        'Year': year
    }
    
    for frontend_field, df_field in field_mapping.items():
        value = data.get(frontend_field)
        if value:
            try:
                new_student_data[df_field] = float(value)
            except ValueError:
                new_student_data[df_field] = None
    
    # Kiểm tra dữ liệu đã tồn tại
    if not df[(df['SBD'] == sbd) & (df['Year'] == year)].empty:
        return jsonify({'error': f'SBD {sbd} đã tồn tại trong năm {year}'}), 400
    
    new_student_df = pd.DataFrame([new_student_data])
    df = pd.concat([df, new_student_df], ignore_index=True)
    
    # Thm vào lịch sử
    operation_history.append({
        'operation': 'CREATE',
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'data': new_student_data
    })
    
    return jsonify({'message': 'Thêm thí sinh thành công'}), 201

@app.route('/students/<sbd>', methods=['GET', 'OPTIONS'])
def read_student(sbd):
    if request.method == 'OPTIONS':
        return '', 204
    global operation_history
    try:
        sbd = int(sbd)
        students = df[df['SBD'] == sbd].to_dict('records')
        if not students:
            return jsonify({'error': 'Không tìm thấy thí sinh'}), 404
            
        # Chuyển đổi tên trường về format frontend
        field_mapping = {
            'Toan': 'Toán',
            'Van': 'Văn',
            'Ly': 'Lý', 
            'Hoa': 'Hóa',
            'Sinh': 'Sinh',
            'Ngoai ngu': 'Ngoại ngữ',
            'Lich su': 'Lịch sử',
            'Dia ly': 'Địa lý',
            'GDCD': 'GDCD',
            'MaTinh': 'MaTinh',
            'Year': 'Năm',
            'SBD': 'Số Báo Danh'
        }
        
        # Format tất cả các bản ghi tìm được
        formatted_students = []
        for student in students:
            formatted_record = {}
            for df_field, frontend_field in field_mapping.items():
                if df_field in student:
                    value = student[df_field]
                    if pd.isna(value):  # Kiểm tra nếu là NaN
                        formatted_record[frontend_field] = "Không có"
                    else:
                        formatted_record[frontend_field] = value
            formatted_students.append(formatted_record)
            
        # Thêm vào lịch sử
        operation_history.append({
            'operation': 'READ',
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'sbd': sbd
        })
            
        return jsonify(formatted_students)
    except ValueError:
        return jsonify({'error': 'SBD không hợp lệ'}), 400

@app.route('/students/<sbd>/<year>', methods=['DELETE', 'OPTIONS'])
def delete_student(sbd, year):
    if request.method == 'OPTIONS':
        return '', 204
    global df, operation_history
    try:
        sbd = int(sbd)
        year = int(year)
        
        student_data = df[(df['SBD'] == sbd) & (df['Year'] == year)].to_dict('records')
        if not student_data:
            return jsonify({'error': 'Không tìm thấy thí sinh'}), 404
            
        df = df[~((df['SBD'] == sbd) & (df['Year'] == year))]
        
        # Thêm vào lịch sử
        operation_history.append({
            'operation': 'DELETE',
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'data': student_data[0]
        })
        
        return jsonify({'message': f'Đã xóa thí sinh SBD {sbd} năm {year}'})
    except ValueError:
        return jsonify({'error': 'SBD hoặc năm không hợp lệ'}), 400

@app.route('/students/<sbd>/<year>', methods=['PUT', 'OPTIONS'])
def update_student(sbd, year):
    if request.method == 'OPTIONS':
        return '', 204
    try:
        # Kiểm tra dữ liệu đầu vào
        if not request.is_json:
            return jsonify({'error': 'Dữ liệu phải ở định dạng JSON'}), 400
            
        changes = request.get_json()
        if not changes:
            return jsonify({'error': 'Không có dữ liệu cập nhật'}), 400

        sbd = int(sbd)
        year = int(year)
        
        # Tìm thí sinh cần cập nhật
        mask = (df['SBD'] == sbd) & (df['Year'] == year)
        if df[mask].empty:
            return jsonify({'error': 'Không tìm thấy thí sinh'}), 404
            
        # Mapping tên trường từ frontend sang backend
        field_mapping = {
            'Số Báo Danh': 'SBD',
            'Năm': 'Year',
            'Toán': 'Toan',
            'Văn': 'Van',
            'Lý': 'Ly',
            'Hóa': 'Hoa',
            'Sinh': 'Sinh',
            'Ngoại ngữ': 'Ngoai ngu',
            'Lịch sử': 'Lich su',
            'Địa lý': 'Dia ly',
            'GDCD': 'GDCD',
            'MaTinh': 'MaTinh'
        }

        # Lưu dữ liệu cũ trước khi cập nhật
        old_data = df[mask].to_dict('records')[0]
        
        # Cập nhật từng trường
        for frontend_field, value in changes.items():
            if frontend_field in field_mapping:
                backend_field = field_mapping[frontend_field]
                # Xử lý các trường điểm số
                if backend_field not in ['SBD', 'Year', 'MaTinh']:
                    if value is None or value == '' or value == 'Không có':
                        df.loc[mask, backend_field] = None
                    else:
                        try:
                            df.loc[mask, backend_field] = float(value)
                        except ValueError:
                            return jsonify({'error': f'Giá trị không hợp lệ cho trường {frontend_field}'}), 400
                else:
                    # Xử lý các trường không phải điểm số
                    if value is None or value == '':
                        df.loc[mask, backend_field] = None
                    else:
                        df.loc[mask, backend_field] = value

        # Thêm vào lịch sử
        operation_history.append({
            'operation': 'UPDATE',
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'data': {
                'old': old_data,
                'new': changes,
                'SBD': sbd,
                'Year': year
            }
        })
        
        return jsonify({'message': f'Đã cập nhật thí sinh SBD {sbd} năm {year}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save', methods=['POST', 'OPTIONS'])
def save_data():
    if request.method == 'OPTIONS':
        return '', 204
    global df, operation_history
    
    try:
        # Thay vì lưu vào URL, lưu vào file local trước
        local_file_path = 'Updated_Data.csv'
        df.to_csv(local_file_path, index=False)
        
        # Thêm vào lịch sử
        operation_history.append({
            'operation': 'FINISH',
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'data': {'file': local_file_path}
        })
        
        # Lưu lịch sử thao tác
        save_history()
        
        # Trả về nội dung file để frontend có thể tải xuống
        with open(local_file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()
            
        return jsonify({
            'message': 'Đã lưu dữ liệu thành công',
            'data': file_content
        })
        
    except Exception as e:
        print(f"Error saving data: {str(e)}")
        return jsonify({'error': f'Lỗi khi lưu dữ liệu: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(
            filename,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/history', methods=['GET', 'OPTIONS'])
def get_history():
    if request.method == 'OPTIONS':
        return '', 204
    
    print("Current operation_history:", operation_history)  # Debug log
        
    # X lý dữ liu trước khi gửi về frontend
    formatted_history = []
    for record in operation_history:
        formatted_record = {
            'operation': record['operation'],
            'time': record['time']
        }
        
        # Xử lý data để tránh li NaN
        if 'data' in record:
            if isinstance(record['data'], dict):
                formatted_data = {}
                for key, value in record['data'].items():
                    if pd.isna(value):  # Kiểm tra nếu là NaN
                        formatted_data[key] = None
                    else:
                        formatted_data[key] = value
                formatted_record['data'] = formatted_data
            else:
                formatted_record['data'] = None
                
        if 'sbd' in record:
            formatted_record['sbd'] = record['sbd']
            
        formatted_history.append(formatted_record)  # Thêm dòng này
            
    print("Formatted history:", formatted_history)  # Debug log
    return jsonify(formatted_history)

@app.route('/history/<int:index>', methods=['DELETE', 'OPTIONS'])
def delete_history_item(index):
    if request.method == 'OPTIONS':
        return '', 204
    
    global operation_history
    try:
        if 0 <= index < len(operation_history):
            # Xóa mục lịch sử tại vị trí index
            operation_history.pop(index)
            
            # Lưu lại file CSV
            history_df = pd.DataFrame(operation_history)
            history_df.to_csv('operation_history.csv', index=False)
            
            return jsonify({'message': 'Đã xóa mục lịch sử thành công'})
        else:
            return jsonify({'error': 'Không tìm thấy mục lịch sử'}), 404
    except Exception as e:
        return jsonify({'error': f'Lỗi khi xóa mục lịch sử: {str(e)}'}), 500

@app.route('/history', methods=['DELETE', 'OPTIONS'])
def clear_history():
    if request.method == 'OPTIONS':
        return '', 204
    
    global operation_history
    try:
        # Xóa lịch sử từ biến global
        operation_history = []
        
        # Tạo file CSV mới với các cột cần thiết
        history_df = pd.DataFrame(columns=['operation', 'time', 'sbd', 'data'])
        history_df.to_csv('operation_history.csv', index=False)
            
        return jsonify({'message': 'Đã xóa toàn bộ lịch sử'})
    except Exception as e:
        return jsonify({'error': f'Lỗi khi xóa lịch sử: {str(e)}'}), 500

# Cập nhật hàm lưu lịch sử
def save_history():
    global operation_history
    history_file = 'operation_history.csv'
    
    try:
        # Tạo DataFrame từ operation_history
        history_records = []
        for record in operation_history:
            history_record = {
                'operation': record['operation'],
                'time': record['time'],
                'sbd': record.get('sbd', None),
                'data': str(record.get('data', '')) if record.get('data') else None
            }
            history_records.append(history_record)
            
        # Tạo DataFrame mới và lưu
        if history_records:
            history_df = pd.DataFrame(history_records)
        else:
            # Tạo DataFrame trống với các cột cần thiết
            history_df = pd.DataFrame(columns=['operation', 'time', 'sbd', 'data'])
            
        history_df.to_csv(history_file, index=False)
        print(f"Đã lưu lịch sử thành công")
    except Exception as e:
        print(f"Lỗi khi lưu lịch sử: {str(e)}")

@app.route('/chart/bar', methods=['GET'])
def get_bar_chart_data():
    global df
    try:
        # Đảm bảo dữ liệu được tải
        if df is None or df.empty:
            load_data()
            
        print("Processing bar chart data...")
        # Tính điểm trung bình cho từng môn theo năm và làm tròn 2 chữ số thập phân
        df_2018 = df[df['Year'] == 2018]
        df_2019 = df[df['Year'] == 2019]
        
        if df_2018.empty or df_2019.empty:
            return jsonify({'error': 'Không có dữ liệu cho năm 2018 hoặc 2019'}), 400
            
        subjects = ['Toan', 'Van', 'Ly', 'Hoa', 'Sinh', 'Ngoai ngu', 'Lich su', 'Dia ly', 'GDCD']
        # Làm tròn 2 chữ số thập phân
        mean_2018 = [round(float(df_2018[subject].mean()), 2) for subject in subjects]
        mean_2019 = [round(float(df_2019[subject].mean()), 2) for subject in subjects]
        
        print("Mean 2018:", mean_2018)
        print("Mean 2019:", mean_2019)
        
        data = {
            'labels': ['Toán', 'Văn', 'Lý', 'Hóa', 'Sinh', 'Ngoại ngữ', 'Lịch sử', 'Địa lý', 'GDCD'],
            'datasets': [
                {
                    'label': '2018',
                    'data': mean_2018,
                    'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                },
                {
                    'label': '2019',
                    'data': mean_2019,
                    'backgroundColor': 'rgba(255, 99, 132, 0.5)',
                }
            ]
        }
        print("Bar chart data:", data)
        return jsonify(data)
    except Exception as e:
        print("Error in get_bar_chart_data:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/chart/line', methods=['GET'])
def get_line_chart_data():
    global cleaned_df
    subjects = ['Toan', 'Van', 'Ly', 'Hoa', 'Sinh', 'Ngoai ngu', 'Lich su', 'Dia ly', 'GDCD']
    years = sorted(cleaned_df['Year'].unique())
    
    datasets = []
    for subject in subjects:
        # Xử lý NaN và làm tròn 2 chữ số thập phân
        means = []
        for year in years:
            # Lọc ra các điểm hợp lệ (loại bỏ -1)
            valid_scores = cleaned_df[
                (cleaned_df['Year'] == year) & 
                (cleaned_df[subject] != -1) &  # Loại bỏ điểm -1
                (cleaned_df[subject].notna())  # Loi bỏ NaN
            ][subject]
            
            if len(valid_scores) > 0:
                mean_value = valid_scores.mean()
                means.append(round(float(mean_value), 2))
            else:
                means.append(0)  # hoặc giá trị mặc định khác nếu không có điểm hợp lệ
                
        datasets.append({
            'label': subject,
            'data': means,
            'fill': False,
            'borderColor': f'rgb({np.random.randint(0, 255)}, {np.random.randint(0, 255)}, {np.random.randint(0, 255)})',
            'tension': 0.1  # làm mượt đường
        })
    
    data = {
        'labels': [str(year) for year in years],
        'datasets': datasets
    }
    return jsonify(data)

@app.route('/chart/histogram/<subject>/<int:year>', methods=['GET'])
def get_histogram_data(subject, year):
    global cleaned_df
    try:
        # Map tên môn từ tiếng Việt sang tiếng Anh
        subject_mapping = {
            'Toan': 'Toán',
            'Van': 'Văn',
            'Ly': 'Lý',
            'Hoa': 'Hóa',
            'Sinh': 'Sinh',
            'Ngoai ngu': 'Ngoại ngữ',
            'Lich su': 'Lịch sử',
            'Dia ly': 'Địa lý',
            'GDCD': 'GDCD'
        }
        
        # Lọc d liệu hợp lệ theo năm và môn học
        valid_scores = cleaned_df[
            (cleaned_df['Year'] == year) &
            (cleaned_df[subject] != -1) & 
            (cleaned_df[subject].notna())
        ][subject].values
        
        counts, bins = np.histogram(valid_scores, bins=20, range=(0, 10))
        
        data = {
            'labels': [f'{bins[i]:.1f}-{bins[i+1]:.1f}' for i in range(len(bins)-1)],
            'datasets': [{
                'label': f'Phân phối điểm môn {subject_mapping.get(subject, subject)} năm {year}',
                'data': counts.tolist(),
                'backgroundColor': 'rgba(54, 162, 235, 0.5)',
            }]
        }
        return jsonify(data)
    except Exception as e:
        print("Error in get_histogram_data:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/chart/pie', methods=['GET'])
def get_pie_chart_data():
    global df
    
    def calculate_pass_fail(year_df):
        pass_count = len(year_df[year_df['Toan'] >= 5])
        fail_count = len(year_df[year_df['Toan'] < 5])
        return pass_count, fail_count
    
    df_2018 = df[df['Year'] == 2018]
    df_2019 = df[df['Year'] == 2019]
    
    pass_2018, fail_2018 = calculate_pass_fail(df_2018)
    pass_2019, fail_2019 = calculate_pass_fail(df_2019)
    
    data = {
        'labels': ['Đậu', 'Rớt'],
        'datasets': [
            {
                'label': '2018',
                'data': [pass_2018, fail_2018],
                'backgroundColor': ['rgba(75, 192, 192, 0.5)', 'rgba(255, 99, 132, 0.5)'],
            },
            {
                'label': '2019',
                'data': [pass_2019, fail_2019],
                'backgroundColor': ['rgba(54, 162, 235, 0.5)', 'rgba(255, 206, 86, 0.5)'],
            }
        ]
    }
    return jsonify(data)

@app.route('/chart/area', methods=['GET'])
def get_area_chart_data():
    global df
    khoi_hoc = {
        'A': ['Toan', 'Ly', 'Hoa'],
        'B': ['Toan', 'Hoa', 'Sinh'],
        'C': ['Van', 'Lich su', 'Dia ly'],
        'D': ['Toan', 'Van', 'Ngoai ngu']
    }
    
    data = {
        'labels': ['0-1', '1-2', '2-3', '3-4', '4-5', '5-6', '6-7', '7-8', '8-9', '9-10'],
        'datasets': []
    }
    
    for khoi, subjects in khoi_hoc.items():
        avg_scores = df[subjects].mean(axis=1)
        hist, _ = np.histogram(avg_scores, bins=10, range=(0, 10))
        data['datasets'].append({
            'label': f'Khối {khoi}',
            'data': hist.tolist(),
            'fill': True,
            'backgroundColor': f'rgba({np.random.randint(0, 255)}, {np.random.randint(0, 255)}, {np.random.randint(0, 255)}, 0.5)'
        })
    
    return jsonify(data)

@app.route('/chart/heatmap/<int:year>', methods=['GET'])
def get_heatmap_data(year):
    global df
    year_df = df[df['Year'] == year]
    
    # Chọn các cột điểm số và sắp xếp theo thứ tự mong muốn
    subjects = ['Toan', 'Van', 'Ly', 'Sinh', 'Ngoai ngu', 'Year', 'Hoa', 'Lich su', 'Dia ly', 'GDCD', 'MaTinh']
    subject_labels = ['Toán', 'Văn', 'Lý', 'Sinh', 'Ngoi ngữ', 'Year', 'Hóa', 'Lịch sử', 'Địa lý', 'GDCD', 'MaTinh']
    
    # Tính ma trận tương quan và xử lý NaN
    corr_matrix = year_df[subjects].corr().round(2)
    
    # Chuyển ma trận tương quan thành format phù hợp cho heatmap
    data = []
    for i, row_subject in enumerate(subjects):
        for j, col_subject in enumerate(subjects):
            value = corr_matrix.loc[row_subject, col_subject]
            # Xử lý NaN
            if pd.isna(value):
                value = 0
            data.append({
                'x': j,
                'y': i,
                'value': float(value)
            })
    
    # Chuyển ma trận thành list và xử lý NaN
    values = []
    for row in corr_matrix.values.tolist():
        values.append([0 if pd.isna(x) else float(x) for x in row])
    
    return jsonify({
        'data': data,
        'min': -1,
        'max': 1,
        'labels': subject_labels,
        'values': values
    })

@app.route('/clean/<choice>', methods=['POST', 'OPTIONS'])
def clean_data_route(choice):
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        print(f"Starting clean data process with choice: {choice}")
        print("Request headers:", request.headers)  # Log headers
        print("Request method:", request.method)    # Log method
        
        use_raw_data = choice == '2'
        
        try:
            # Load data
            print("Loading data...")
            data_df, tinh_df = cleaner.load_data(use_raw_data)
            print("Data loaded successfully")
            
            # Clean data
            print("Cleaning data...")
            cleaned_df = cleaner.clean_data(data_df, tinh_df)
            print("Data cleaned successfully")
            
            # Tạo temporary file để lưu kết quả
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as tmp:
                cleaned_df.to_csv(tmp.name, index=False, encoding='utf-8')
                tmp_path = tmp.name
            
            # Đọc nội dung file để trả về
            with open(tmp_path, 'r', encoding='utf-8') as f:
                csv_content = f.read()
            
            # Xóa file tạm
            os.unlink(tmp_path)
            
            # Thêm vào lịch sử
            operation_history.append({
                'operation': 'CLEAN',
                'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'data': {'choice': 'Raw Data' if use_raw_data else 'Update Data'}
            })
            
            return jsonify({
                'message': 'Dữ liệu đã được làm sạch thành công',
                'data': csv_content
            })
            
        except Exception as e:
            print(f"Error during data processing: {str(e)}")
            return jsonify({'error': f'Lỗi khi xử lý dữ liệu: {str(e)}'}), 500
            
    except Exception as e:
        print(f"Error in clean_data_route: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/tinh-data', methods=['GET'])
def get_tinh_data():
    try:
        df = fetch_tinh_data()
        data = df.to_dict('records')
        print(f"Trả về {len(data)} bản ghi tỉnh")
        print("Mẫu dữ liệu:", data[:2])  # In 2 bản ghi đầu tiên để kiểm tra
        return jsonify({
            'data': data
        })
    except Exception as e:
        print(f"Lỗi trong get_tinh_data: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)