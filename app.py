from flask import Flask, request, jsonify, send_file
import pandas as pd
from datetime import datetime, timedelta
import os
from flask_cors import CORS
import requests
from io import StringIO

app = Flask(__name__)
CORS(app, resources={
    r"/students/*": {"origins": "*", "methods": ["GET", "POST", "DELETE", "PUT", "OPTIONS"]},
    r"/save": {"origins": "*", "methods": ["POST", "OPTIONS"]},
    r"/history*": {"origins": "*", "methods": ["GET", "POST", "DELETE", "PUT", "OPTIONS"]}
})


RAW_DATA_API = 'https://andyanh.id.vn/index.php/s/p7XMy828G8NKiZp/download'
UPDATED_FILE_PATH = 'Updated_Data.csv'

df = None
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

def fetch_csv_from_api(api_url):
    """
    Tải dữ liệu từ API và lưu cache
    """
    cache_file = 'raw_data_cache.csv'
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

@app.before_request
def load_data():
    global df, data_loaded
    if not data_loaded:
        try:
            df = fetch_csv_from_api(RAW_DATA_API)
            init_history()
            data_loaded = True
            print("Đã tải dữ liệu thành công")
        except Exception as e:
            print(f"Lỗi khi tải dữ liệu: {str(e)}")
            df = pd.DataFrame()
            data_loaded = True

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
    
    # Thêm vào lịch sử
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
    
    # Lưu file CSV
    df.to_csv(UPDATED_FILE_PATH, index=False)
    
    # Thêm vào lịch sử
    operation_history.append({
        'operation': 'FINISH',
        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'data': {'file': UPDATED_FILE_PATH}
    })
    
    # Lưu lịch sử thao tác với hàm mới
    save_history()
    
    return jsonify({
        'message': 'Đã lưu dữ liệu thành công',
        'download_url': f'/download/{os.path.basename(UPDATED_FILE_PATH)}'
    })

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
        
    # Xử lý dữ liệu trước khi gửi về frontend
    formatted_history = []
    for record in operation_history:
        formatted_record = {
            'operation': record['operation'],
            'time': record['time']
        }
        
        # Xử lý data để tránh lỗi NaN
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

if __name__ == '__main__':
    app.run(debug=True)