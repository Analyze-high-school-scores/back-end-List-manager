#!/bin/bash

# Tên của môi trường ảo
VENV_DIR="venv"

# Kiểm tra và cài đặt pip nếu chưa có
if ! command -v pip &> /dev/null
then
    echo "pip chưa được cài đặt. Vui lòng cài đặt pip trước khi chạy script này."
    exit
fi

# Tạo môi trường ảo nếu chưa có
if [ ! -d "$VENV_DIR" ]; then
    echo "Tạo môi trường ảo..."
    python -m venv $VENV_DIR
fi

# Kích hoạt môi trường ảo
echo "Kích hoạt môi trường ảo..."
source $VENV_DIR/bin/activate

# Danh sách các thư viện cần thiết
libraries=("flask" "pandas" "requests" "numpy" "scikit-learn" "seaborn" "matplotlib" "flask-cors")

# Kiểm tra và cài đặt các thư viện nếu cần
echo "Kiểm tra và cài đặt các thư viện cần thiết..."
for lib in "${libraries[@]}"
do
    if ! python -c "import $lib" &> /dev/null; then
        echo "Cài đặt $lib..."
        pip install $lib
    else
        echo "$lib đã được cài đặt."
    fi
done

# Chạy ứng dụng
echo "Đang chạy ứng dụng..."
python app.py

# Hủy kích hoạt môi trường ảo sau khi chạy xong
deactivate