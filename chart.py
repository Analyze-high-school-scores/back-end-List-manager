import pandas as pd
import matplotlib.pyplot as plt
import requests
from io import StringIO
from datetime import datetime, timedelta
import os
import seaborn as sns

# Tải dữ liệu từ API
cleaned_data_api = 'https://andyanh.id.vn/index.php/s/AQrkaif3HWgs9ke/download'

def fetch_csv_from_api(api_url):
    cache_file = 'cleaned_data_cache.csv'
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

# Tải dữ liệu từ API
df = fetch_csv_from_api(cleaned_data_api)

# Lọc dữ liệu theo năm
df_years = {2018: df[df["Year"] == 2018], 2019: df[df["Year"] == 2019]}

# Định nghĩa các cột điểm
score_columns = [
    "Toan", "Van", "Ly", "Sinh", "Ngoai ngu", "Hoa", "Lich su", "Dia ly", "GDCD"
]

# Tính điểm trung bình cho từng môn theo năm
mean_scores_2018 = df_years[2018][score_columns].replace(-1, float("nan")).mean()
mean_scores_2019 = df_years[2019][score_columns].replace(-1, float("nan")).mean()
mean_scores = pd.DataFrame({"2018": mean_scores_2018, "2019": mean_scores_2019})

# Biểu đồ thanh so sánh điểm trung bình giữa 2 năm
def plot_bar_chart():
    fig, ax = plt.subplots(figsize=(10, 6))
    mean_scores.plot(kind="bar", ax=ax)
    ax.set_title("So sánh điểm trung bình các môn giữa năm 2018 và 2019")
    ax.set_xlabel("Môn học")
    ax.set_ylabel("Điểm trung bình")
    ax.legend(title="Năm")
    plt.show()

# Biểu đồ đường thay đổi điểm trung bình
def plot_line_chart():
    fig, ax = plt.subplots(figsize=(15, 6))
    mean_scores_by_year = df.groupby("Year")[score_columns].mean()
    mean_scores_by_year.plot(kind="line", marker="o", ax=ax)
    ax.set_title("Biểu đồ thay đổi điểm trung bình")
    ax.set_ylabel("Điểm trung bình")
    ax.legend(title="Môn học")
    plt.xticks(rotation=90)
    plt.show()

# Biểu đồ phân phối điểm cho môn học năm 2018
def plot_distribution_chart(subject="Toan"):
    fig, ax = plt.subplots(figsize=(8, 5))
    df_years[2018][subject].replace(-1, float("nan")).dropna().hist(
        bins=20, color="skyblue", edgecolor="black", ax=ax
    )
    ax.set_title(f"Phân phối điểm cho môn {subject} (2018)")
    ax.set_xlabel("Điểm")
    ax.set_ylabel("Số lượng thí sinh")
    plt.show()

# Biểu đồ tròn so sánh tỉ lệ đậu rớt của năm 2018 2019
def plot_pie_chart():
    Summary_Result_By_Year = "Summary_Result_By_Year.csv"
    df_2 = pd.read_csv(Summary_Result_By_Year)
    labels = ["Đậu", "Rớt"]

    passed_2018 = df_2["Số thí sinh đậu 2018"].sum()
    failed_2018 = df_2["Số thí sinh rớt 2018"].sum()
    values_2018 = [passed_2018, failed_2018]

    passed_2019 = df_2["Số thí sinh đậu 2019"].sum()
    failed_2019 = df_2["Số thí sinh rớt 2019"].sum()
    values_2019 = [passed_2019, failed_2019]

    fig, ax = plt.subplots(1, 2, figsize=(12, 6))
    ax[0].pie(values_2018, labels=labels, autopct="%1.1f%%", startangle=140, colors=["#4CAF50", "#F44336"])
    ax[0].set_title("2018 Đậu Rớt")
    ax[1].pie(values_2019, labels=labels, autopct="%1.1f%%", startangle=140, colors=["#4CAF50", "#F44336"])
    ax[1].set_title("2019 Đậu Rớt")
    plt.show()

# Biểu đồ khu vực học sinh các khối A, B, C, D đạt các mức điểm năm 2018 - 2019
def plot_area_chart():
    khối_học = {
        'A': ['Toan', 'Ly', 'Hoa'],
        'B': ['Toan', 'Hoa', 'Sinh'], 
        'C': ['Van', 'Lich su', 'Dia ly'],
        'D': ['Toan', 'Van', 'Ngoai ngu']
    }

    def calculate_average_score(data, subjects):
        data['Average_Score'] = data[subjects].mean(axis=1)
        valid_scores = data['Average_Score'][(data['Average_Score'] >= 0) & (data['Average_Score'] <= 10)]
        distribution = pd.cut(valid_scores, bins=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                               right=False, labels=["0-1", "1-2", "2-3", "3-4", "4-5",
                                                    "5-6", "6-7", "7-8", "8-9", "9-10"]).value_counts()
        return distribution

    distribution_by_khoi = {}
    for khoi, subjects in khối_học.items():
        distribution_by_khoi[khoi] = calculate_average_score(df, subjects)

    result_df = pd.DataFrame(distribution_by_khoi).fillna(0).astype(int).sort_index()

    plt.figure(figsize=(10, 6))
    result_df.plot(kind='area', stacked=False, alpha=0.5)
    plt.title("Phân phối điểm theo khối (Area Chart)", fontsize=14)
    plt.xlabel("Mức điểm", fontsize=12)
    plt.ylabel("Số lượng học sinh", fontsize=12)
    plt.legend(title="Khối học", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
    plt.tight_layout()
    plt.show()

# Hàm vẽ heatmap cho các môn học
def heatmapSubject(data, year):
    data = data.fillna(0)
    score_columns = data.columns[1:]
    data = data[score_columns]
    data_cleaned = data.drop(columns=["MaTinh"])
    corr_matrix = data.corr()

    plt.figure(figsize=(10, 8))
    sns.heatmap(
        corr_matrix,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        cbar=True,
        square=True,
        linewidths=0.5,
    )
    plt.title(f"Ma Trận Tương Quan Giữa Các Môn Học Năm {year} TPHCM", fontsize=16)
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.show()

# Biểu đồ phân tán giữa điểm trung bình môn Toán và môn Văn
def plot_scatter_chart():
    df_filtered = df[['Toan', 'Van']]
    df_mean = df_filtered.groupby('Van')['Toan'].mean().reset_index()

    plt.figure(figsize=(10, 6))
    sns.scatterplot(x='Van', y='Toan', data=df_mean)
    plt.title('Biểu đồ phân tán giữa điểm trung bình môn Toán và môn Văn', fontsize=12, pad=15)
    plt.xlabel('Điểm môn Văn', fontsize=10)
    plt.ylabel('Điểm môn Toán', fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.show()

# Gọi các hàm để vẽ biểu đồ
plot_bar_chart()
plot_line_chart()
plot_distribution_chart()
plot_pie_chart()
plot_area_chart()
heatmapSubject(df_years[2018], 2018)
heatmapSubject(df_years[2019], 2019)
plot_scatter_chart()